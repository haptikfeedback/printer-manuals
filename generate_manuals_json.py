import os
import json

# Public SharePoint folder link (anyone with the link can view)
SHAREPOINT_PUBLIC_BASE = "https://synergyitx.sharepoint.com/:f:/s/SupportFiles/EkAC-zIBK_dJieib8J4SIR0B7oNsGG_ly9CHsGqi3oZNGQ"

# Allowed file extensions
ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".zip", ".exe"]

def generate_manuals_json(root_folder):
    manuals_data = {}

    for make in os.listdir(root_folder):
        make_path = os.path.join(root_folder, make)
        if not os.path.isdir(make_path):
            continue

        has_manuals_at_root = False
        root_manuals = []

        for item in os.listdir(make_path):
            item_path = os.path.join(make_path, item)

            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    relative_path = f"{make}/{item}".replace(" ", "%20")
                    sharepoint_url = f"{SHAREPOINT_PUBLIC_BASE}/{relative_path}"
                    root_manuals.append({
                        "title": os.path.splitext(item)[0],
                        "url": sharepoint_url
                    })
                    has_manuals_at_root = True

        if has_manuals_at_root:
            manuals_data[make] = {
                "_root": {
                    "manuals": root_manuals
                }
            }

        for model in os.listdir(make_path):
            model_path = os.path.join(make_path, model)
            if not os.path.isdir(model_path):
                continue

            manuals = []
            for file in os.listdir(model_path):
                ext = os.path.splitext(file)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    relative_path = f"{make}/{model}/{file}".replace(" ", "%20")
                    sharepoint_url = f"{SHAREPOINT_PUBLIC_BASE}/{relative_path}"

                    manuals.append({
                        "title": os.path.splitext(file)[0],
                        "url": sharepoint_url
                    })

            if manuals:
                if make not in manuals_data:
                    manuals_data[make] = {}
                manuals_data[make][model] = {
                    "manuals": manuals
                }

    return manuals_data

# Path to your synced OneDrive folder
local_folder_path = r"D:\SynergyITX\OneDrive - Synergy IT Solutions LLC\Documents - Support Files\_Sorted_By_Manufacturer_Model"
output_file_path = "manuals.json"

manuals_json = generate_manuals_json(local_folder_path)

with open(output_file_path, "w", encoding="utf-8") as f:
    json.dump(manuals_json, f, indent=2)

print(f"✅ manuals.json created at: {output_file_path}")
