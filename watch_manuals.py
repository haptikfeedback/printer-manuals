from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import time
import os

# === Configuration ===
WATCH_FOLDER = r"D:\SynergyITX\OneDrive - Synergy IT Solutions LLC\Documents - Support Files\_Sorted_By_Manufacturer_Model"
REPO_FOLDER = r"D:\printer-manuals"
SCRIPT_NAME = "generate_manuals_graph.py"
LOG_FILE = os.path.join(REPO_FOLDER, "watcher_log.txt")

class ManualChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if not event.is_directory:
            with open(LOG_FILE, "a") as log:
                log.write(f"[{time.ctime()}] Change detected: {event.src_path}\n")

            subprocess.call(["pythonw", os.path.join(REPO_FOLDER, SCRIPT_NAME)])
            subprocess.call(["git", "add", "manuals.json"], cwd=REPO_FOLDER)
            subprocess.call(["git", "commit", "-m", "Auto update from file watcher"], cwd=REPO_FOLDER)
            subprocess.call(["git", "push"], cwd=REPO_FOLDER)

if __name__ == "__main__":
    event_handler = ManualChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_FOLDER, recursive=True)
    observer.start()

    with open(LOG_FILE, "a") as log:
        log.write(f"[{time.ctime()}] File watcher started.\n")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
        with open(LOG_FILE, "a") as log:
            log.write(f"[{time.ctime()}] File watcher stopped.\n")

    observer.join()
