# 4_add_text.py

import os
import subprocess
import json
from datetime import datetime

# Import variables from GLOBAL_VARIABLES.py
from GLOBAL_VARIABLES import FIRST_5_SECOND_TEXT, LAST_5_SECONDS_TEXT

# Constants
STORYLINES_FOLDER = 'storylines'
CREATED_VIDEOS_DIR = 'created_videos'
PROCESSED_VIDEOS_DIR = os.path.join(CREATED_VIDEOS_DIR, 'processed')
FONT_FILE = '/System/Library/Fonts/Supplemental/Helvetica.ttc'  # Update with your font path
FONT_SIZE = 48  # Adjust font size as needed
MAX_CHARS_PER_LINE = 40  # Adjust the max characters per line as needed

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

def get_video_duration(input_file):
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_file
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"[ERROR] Failed to get video duration: {e}")
        return None

def sanitize_text(text):
    # Remove surrounding quotes
    sanitized_text = text.strip('"').replace("'", "`")
    # Escape special characters for ffmpeg drawtext
    sanitized_text = sanitized_text.replace('\\', r'\\\\')   # Escape backslashes
    sanitized_text = sanitized_text.replace(':', r'\:')      # Escape colons
    sanitized_text = sanitized_text.replace(',', r'\,')      # Escape commas
    # Do NOT escape newlines; leave them as is
    return sanitized_text

def split_text_into_lines(text, max_chars_per_line):
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 > max_chars_per_line:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word) + 1
        else:
            current_line.append(word)
            current_length += len(word) + 1

    if current_line:
        lines.append(' '.join(current_line))

    return '\n'.join(lines)

def sanitize_path(path):
    return path.replace('\\', r'\\\\').replace("'", r"\'").replace(":", r'\:').replace(',', r'\,')

def process_video():
    # Get the latest storyline JSON file
    json_file_path = get_latest_storyline_file(STORYLINES_FOLDER)
    if not json_file_path:
        print("[ERROR] No storyline JSON file found.")
        return

    data = read_json(json_file_path)
    if data is None:
        return

    # Get the video path from the JSON file
    zoom_pan_video_key = "zoom_pan_video_location_manual"
    zoom_pan_video_path = data.get(zoom_pan_video_key)
    if not zoom_pan_video_path or not os.path.isfile(zoom_pan_video_path):
        print(f"[ERROR] Video file {zoom_pan_video_path} does not exist.")
        return

    # Prepare input and output file paths
    input_file = zoom_pan_video_path
    video_base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{video_base_name}_text.mp4"
    output_file = os.path.join(CREATED_VIDEOS_DIR, output_filename)

    # Get video duration
    duration = get_video_duration(input_file)
    if duration is None:
        print("[ERROR] Could not determine video duration.")
        return

    # Duration settings for first and last text
    start_time1 = 0
    end_time1 = min(5, duration / 2)  # Show first text for 5 seconds or half the video
    start_time2 = max(duration - 5, end_time1)  # Start last text 5 seconds before end
    end_time2 = duration

    # Position settings
    x1 = '(w - text_w) / 2'  # Center horizontally
    y1 = 'h - text_h - 50'   # Position near the bottom
    x2 = '(w - text_w) / 2'  # Center horizontally
    y2 = '50'                # Position near the top

    # Text styling settings
    fontfile = FONT_FILE
    fontsize = FONT_SIZE
    fontcolor = 'white'
    box = 1
    boxcolor = 'black@0.5'
    boxborderw = 10
    borderw = 2
    bordercolor = 'white@0.8'
    shadowcolor = 'black@0.7'
    shadowx = 3
    shadowy = 3
    line_spacing = 10
    alpha = '1'

    # Sanitize and split texts into lines
    sanitized_text1 = sanitize_text(FIRST_5_SECOND_TEXT)
    sanitized_text2 = sanitize_text(LAST_5_SECONDS_TEXT)
    split_text1 = split_text_into_lines(sanitized_text1, MAX_CHARS_PER_LINE)
    split_text2 = split_text_into_lines(sanitized_text2, MAX_CHARS_PER_LINE)
    escaped_fontfile = sanitize_path(fontfile)

    # Construct drawtext filters
    drawtext1 = (
        f"drawtext="
        f"fontfile='{escaped_fontfile}':"
        f"text='{split_text1}':"
        f"fontcolor={fontcolor}:"
        f"fontsize={fontsize}:"
        f"line_spacing={line_spacing}:"
        f"box={box}:"
        f"boxcolor={boxcolor}:"
        f"boxborderw={boxborderw}:"
        f"borderw={borderw}:"
        f"bordercolor={bordercolor}:"
        f"shadowcolor={shadowcolor}:"
        f"shadowx={shadowx}:"
        f"shadowy={shadowy}:"
        f"x={x1}:"
        f"y={y1}:"
        f"alpha={alpha}:"
        f"enable='between(t,{start_time1},{end_time1})'"
    )

    drawtext2 = (
        f"drawtext="
        f"fontfile='{escaped_fontfile}':"
        f"text='{split_text2}':"
        f"fontcolor={fontcolor}:"
        f"fontsize={fontsize}:"
        f"line_spacing={line_spacing}:"
        f"box={box}:"
        f"boxcolor={boxcolor}:"
        f"boxborderw={boxborderw}:"
        f"borderw={borderw}:"
        f"bordercolor={bordercolor}:"
        f"shadowcolor={shadowcolor}:"
        f"shadowx={shadowx}:"
        f"shadowy={shadowy}:"
        f"x={x2}:"
        f"y={y2}:"
        f"alpha={alpha}:"
        f"enable='between(t,{start_time2},{end_time2})'"
    )

    # Combine the drawtext filters
    video_filter = f"{drawtext1},{drawtext2}"

    # Build the ffmpeg command
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',  # Overwrite without asking
        '-i', input_file,
        '-vf', video_filter,
        '-codec:a', 'copy',  # Copy audio without re-encoding
        output_file
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"[INFO] Text successfully added to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] An error occurred while running ffmpeg:\n{e}")
        print(f"ffmpeg command: {' '.join(ffmpeg_cmd)}")
        return

    # Move the original video to the processed directory
    os.makedirs(PROCESSED_VIDEOS_DIR, exist_ok=True)
    original_video_archived_name = f"{video_base_name}_{timestamp}.mp4"
    original_video_archived_path = os.path.join(PROCESSED_VIDEOS_DIR, original_video_archived_name)
    os.rename(input_file, original_video_archived_path)
    print(f"[INFO] Original video moved to {original_video_archived_path}")

    # Update the JSON data with the new processed video location
    data["final_video_with_text_manual"] = output_file

    # Update 'zoom_pan_video_location_manual' with the new location of the original video
    data["zoom_pan_video_location_manual"] = original_video_archived_path

    # Save the updated JSON file
    write_json(data, json_file_path)

def main():
    print(f"[INFO] Starting 4_add_text.py at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    process_video()
    print(f"[INFO] 4_add_text.py completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()