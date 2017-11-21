# ===================
# module: config.py
# description: basic configuration of the project
# ===================
import os

# the absolute path to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
# the absolute path to piano reduction package
LIB_DIR = os.path.join(PROJECT_ROOT, "learning")
# the absolute path to ./log
LOG_DIR = os.path.join(PROJECT_ROOT, "log")
# the absolute path to ./tonalanalysis
TONE_DIR = os.path.join(PROJECT_ROOT, "tonalanalysis")
# the absolute path to datasets for flow model
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# temporary folder directory
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

if __name__ == "__main__":
    print("Project root directory: ", PROJECT_ROOT)
    print("Library directory: ", LIB_DIR)
    print("Log directory: ", LOG_DIR)
    print("Tonal analysis directory: ", TONE_DIR)
    print("Flow dataset directory: ", DATA_DIR)
    print("Temporary folder directory: ", TEMP_DIR)
