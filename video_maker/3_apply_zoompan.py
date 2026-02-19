
# apply_zoompan.py

import os
import subprocess
import json
import shutil
from datetime import datetime

# Constants
CREATED_VIDEOS_DIR = "created_videos"
PROCESSED_VIDEOS_DIR = os.path.join(CREATED_VIDEOS_DIR, "processed")
STORYLINES_FOLDER = "storylines"
GLOBAL_PAN_SPEED = 50  # Speed of the pan and zoom effects (10 is fast, 200 is slow)
ZOOM_PATTERN = "1 + 0.2*sin(in/25)"  # Customize the zoom pattern here

# Ensure the processed videos directory exists
os.makedirs(PROCESSED_VIDEOS_DIR, exist_ok=True)

def get_latest_storyline_file(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('_manual_storyline.json')]
    if not json_files:
        return None
    json_files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
    latest_file = json_files[0]
    return os.path.join(directory, latest_file)

def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON file {file_path}: {e}")
        return None

def write_json(data, file_path):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"[INFO] JSON file {file_path} updated successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to write to JSON file {file_path}: {e}")

def process_video():
    json_file_path = get_latest_storyline_file(STORYLINES_FOLDER)
    if not json_file_path:
        print("[ERROR] No storyline JSON file found.")
        return

    data = read_json(json_file_path)
    if data is None:
        return

    # Get the video path from the JSON file
    created_video_key = "created_video_location_manual"
    created_video_path = data.get(created_video_key)
    if not created_video_path or not os.path.isfile(created_video_path):
        print(f"[ERROR] Video file {created_video_path} does not exist.")
        return

    video_file = os.path.basename(created_video_path)
    video_dir = os.path.dirname(created_video_path)

    # Get the video dimensions using ffprobe
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
         'stream=width,height', '-of', 'csv=p=0', created_video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    video_dimensions = result.stdout.decode().strip().split(',')
    if len(video_dimensions) < 2:
        print(f"Could not determine dimensions for {video_file}.")
        return

    video_width = int(video_dimensions[0])
    video_height = int(video_dimensions[1])

    # Adding a smooth and varied zoom and pan effect for the entire video
    # Apply GLOBAL_PAN_SPEED to pan and zoom functions
    zoompan_filter = (
        f"zoompan=z='{ZOOM_PATTERN}':"  # Use the global ZOOM_PATTERN
        f"x='iw/2-(iw/zoom/2)+(sin(on/{GLOBAL_PAN_SPEED})*iw/4)':"  # Horizontal panning
        f"y='ih/2-(ih/zoom/2)+(cos(on/{GLOBAL_PAN_SPEED})*ih/4)':"  # Vertical panning
        f"d=1:s={video_width}x{video_height}"  # Output size
    )

    # Generate the processed output filename
    video_base_name = os.path.splitext(video_file)[0]
    processed_video_filename = f"{video_base_name}_zoompan.mp4"
    processed_video_path = os.path.join(video_dir, processed_video_filename)

    # Process the video with FFmpeg
    ffmpeg_command = [
        'ffmpeg', '-y', '-i', created_video_path, '-vf', zoompan_filter,
        '-preset', 'fast', '-c:a', 'copy', processed_video_path
    ]
    try:
        subprocess.run(ffmpeg_command, check=True)
        print(f"Processed video saved as {processed_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg processing failed: {e}")
        return

    # Move the original video to the processed directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_video_archived_name = f"{video_base_name}_{timestamp}.mp4"
    original_video_archived_path = os.path.join(PROCESSED_VIDEOS_DIR, original_video_archived_name)
    shutil.move(created_video_path, original_video_archived_path)
    print(f"Original video moved to {original_video_archived_path}")

    # Update the JSON data with the new processed video location
    data["zoom_pan_video_location_manual"] = processed_video_path

    # Update 'created_video_location_manual' with the new location of the original video
    data["created_video_location_manual"] = original_video_archived_path

    # Save the updated JSON file
    write_json(data, json_file_path)

if __name__ == "__main__":
    process_video()