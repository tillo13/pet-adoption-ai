
# 5_clean_up.py

import os
import shutil
import sys
from datetime import datetime

def delete_directory(dir_path):
    """
    Deletes the directory at dir_path if it exists.

    Args:
        dir_path (str): The absolute path to the directory to delete.
    """
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Deleted directory: {dir_path}")
        except Exception as e:
            print(f"[ERROR] Failed to delete {dir_path}: {e}")
    else:
        print(f"[INFO] Directory not found, skipping deletion: {dir_path}")

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the directories to clean up
    directories_to_delete = [
        os.path.join(script_dir, "created_videos", "processed"),
        os.path.join(script_dir, "frames"),
        os.path.join(script_dir, "music_downloads"),  # If exists from previous runs
        os.path.join(script_dir, "temp_images_on_create_video"),
        os.path.join(script_dir, "temp_tts_creation"),  # If used in previous versions
        # Add any other temporary directories you may have used
    ]

    print(f"[INFO] Starting clean-up process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for dir_path in directories_to_delete:
        delete_directory(dir_path)

    print(f"[INFO] Clean-up process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()