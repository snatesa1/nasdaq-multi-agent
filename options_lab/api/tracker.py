import os
import logging
from datetime import datetime

# Setup persistent log file path with cross-platform fallback
DEFAULT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "options_lab_tracker.log")
LOG_FILE_PATH = os.getenv("TRACKER_LOG_PATH", DEFAULT_LOG_PATH)

# Ensure directory exists safely
log_dir = os.path.dirname(LOG_FILE_PATH)
if log_dir and not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass

# Standard Python logger setup
logger = logging.getLogger("options-lab-tracker")
logger.setLevel(logging.INFO)

# File Handler with graceful fallback
try:
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception:
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)

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
