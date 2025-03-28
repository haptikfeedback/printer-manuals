import os
import json
import logging
import msal
import requests
import atexit
import sys

# Config
CLIENT_ID = 'bea13de9-52f0-4aa7-88b4-b18e332871b9'
TENANT_ID = 'a52eded3-8aec-4175-972a-4799ea939583'
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Sites.Read.All", "Files.ReadWrite.All", "User.Read"]
TOKEN_CACHE_FILE = "msal_cache.bin"
LOG_FILE = "generate_manuals_graph.log"
SKIPPED_LINKS_LOG = "skipped_links.log"
ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".zip", ".exe"]

# Site and Drive setup
SITE_HOSTNAME = "synergyitx.sharepoint.com"
SITE_PATH = "/sites/SupportFiles"
DOCUMENT_LIBRARY_NAME = "Documents"

# Local OneDrive-synced folder
MANUALS_FOLDER = r"D:\SynergyITX\OneDrive - Synergy IT Solutions LLC\Documents - Support Files\_Sorted_By_Manufacturer_Model"
OUTPUT_JSON = "manuals.json"
LOGIN_HINT = "nicholas.tonn@synergyitx.com"

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

if not sys.stdout.isatty():
    logger.propagate = False

# === AUTHENTICATION ===
def load_token_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        cache.deserialize(open(TOKEN_CACHE_FILE, "r").read())
    atexit.register(lambda: open(TOKEN_CACHE_FILE, "w").write(cache.serialize()) if cache.has_state_changed else None)
    return cache

def authenticate():
    cache = load_token_cache()
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
    if not result:
        result = app.acquire_token_interactive(
            scopes=SCOPES,
            login_hint=LOGIN_HINT,
            prompt="select_account"
        )
    return result["access_token"]

def get_graph_client(token):
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session

# === GRAPH HELPERS ===
def get_site_id(graph_client):
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_HOSTNAME}:{SITE_PATH}"
    response = graph_client.get(url)
    response.raise_for_status()
    return response.json()['id']

def get_drive_id(graph_client, site_id):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    response = graph_client.get(url)
    response.raise_for_status()
    drives = response.json()['value']
    for drive in drives:
        if drive['name'] == DOCUMENT_LIBRARY_NAME:
            return drive['id']
    raise Exception(f"Drive '{DOCUMENT_LIBRARY_NAME}' not found in site.")

def find_file_id(graph_client, drive_id, remote_path):
    encoded_path = requests.utils.quote(remote_path)
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}"
    response = graph_client.get(url)
    if response.status_code == 200:
        return response.json()['id']
    else:
        logger.warning(f"File not found in SharePoint: {remote_path}")
        return None

def create_anonymous_link(graph_client, drive_id, file_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/createLink"
    body = {
        "type": "view",
        "scope": "anonymous"
    }
    response = graph_client.post(url, json=body)
    response.raise_for_status()
    return response.json()['link']['webUrl']

def is_link_valid(url):
    try:
        res = requests.head(url, allow_redirects=True, timeout=10)
        return res.status_code in (200, 302)
    except Exception as e:
        logger.warning(f"Link validation failed: {e}")
        return False

# === MAIN SCRIPT ===
def main():
    logger.info("🔐 Authenticating with Microsoft Graph...")
    token = authenticate()
    graph_client = get_graph_client(token)

    logger.info("🌐 Resolving SharePoint site and drive IDs...")
    site_id = get_site_id(graph_client)
    drive_id = get_drive_id(graph_client, site_id)

    existing_manuals = {}
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            existing_manuals = json.load(f)

    new_manuals = {}
    seen_keys = set()
    skipped_links = []

    logger.info("📂 Scanning local OneDrive-synced folder...")
    for root, _, files in os.walk(MANUALS_FOLDER):
        for file in files:
            if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS:
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, MANUALS_FOLDER).replace("\\", "/")
                remote_path = f"_Sorted_By_Manufacturer_Model/{rel_path}"
                parts = rel_path.split("/")

                if len(parts) >= 2:
                    manufacturer = parts[0]
                    model = parts[1] if len(parts) > 2 else "_root"
                    title = os.path.splitext(file)[0]
                    seen_keys.add((manufacturer, model, title))

                    try:
                        logger.info(f"🔎 Looking up: {remote_path}")
                        file_id = find_file_id(graph_client, drive_id, remote_path)
                        if not file_id:
                            continue

                        share_url = create_anonymous_link(graph_client, drive_id, file_id)

                        if not is_link_valid(share_url):
                            logger.warning(f"⚠️ Skipping broken link: {share_url}")
                            skipped_links.append(share_url)
                            continue

                        new_manuals.setdefault(manufacturer, {}).setdefault(model, []).append({
                            "title": file,
                            "url": share_url
                        })

                    except Exception as e:
                        logger.error(f"❌ Error processing {rel_path}: {e}")
                else:
                    logger.warning(f"⚠️ Skipped unstructured file: {rel_path}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(new_manuals, f, indent=4)
    logger.info(f"✅ Done. Manual links written to: {OUTPUT_JSON}")

    if skipped_links:
        with open(SKIPPED_LINKS_LOG, "w", encoding="utf-8") as logf:
            for link in skipped_links:
                logf.write(link + "\n")
        logger.info(f"⚠️ Some broken links were skipped. See {SKIPPED_LINKS_LOG}")

if __name__ == "__main__":
    main()
