@echo off
cd /d D:\printer-manuals
python generate_manuals_graph.py >> push_log.txt 2>&1
git add manuals.json
git commit -m "Auto update manuals.json" >> push_log.txt 2>&1 || echo No changes to commit >> push_log.txt
git push >> push_log.txt 2>&1
