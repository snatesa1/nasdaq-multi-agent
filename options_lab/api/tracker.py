import os
import logging
from datetime import datetime

# Setup persistent log file path
LOG_FILE_PATH = "c:/Admin/Akpegis-Agent-Ecosystem/options_lab_tracker.log"

# Standard Python logger setup
logger = logging.getLogger("options-lab-tracker")
logger.setLevel(logging.INFO)

# File Handler
file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_progress(step: str, status: str, message: str = ""):
    """
    Log a distinct progress milestone for the options lab.
    Writes to the centralized options_lab_tracker.log.
    """
    log_msg = f"| Step: {step:<25} | Status: {status:<10} | {message}"
    logger.info(log_msg)
    # Also print to stdout for backend processes
    print(f"[TRACKER] {log_msg}")

# Initialize log file if not exists
if not os.path.exists(LOG_FILE_PATH):
    try:
        with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(f"=== OptionsLab Progress & Activity Log (Initialized {datetime.now()}) ===\n")
        log_progress("Initialization", "SUCCESS", "Tracker log file created at options_lab_tracker.log")
    except Exception:
        pass
else:
    log_progress("Startup", "INFO", "Tracker log agent attached to running session")
