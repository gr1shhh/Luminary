import os
import shutil
from datetime import datetime
from config import BASE_OUTPUT_DIR, LATEST_DIR


def setup_run():
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)

    existing_runs = [d for d in os.listdir(BASE_OUTPUT_DIR) if d.startswith("run_")]
    run_number = len(existing_runs) + 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    run_folder = f"run_{run_number:02d}_{timestamp}"
    run_path = os.path.join(BASE_OUTPUT_DIR, run_folder)

    if os.path.exists(LATEST_DIR):
        shutil.move(LATEST_DIR, run_path)

    os.makedirs(LATEST_DIR, exist_ok=True)
    print(f"Starting run: {run_folder}")
    return LATEST_DIR