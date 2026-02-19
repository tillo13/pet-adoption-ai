import os
import json
from datetime import datetime
import sys
import time
import subprocess
import shlex
import requests

from GLOBAL_VARIABLES import SONG_TO_USE, SONG_PROMPT

def is_npm_running():
    try:
        response = requests.get('http://localhost:3000/api/get_limit')
        response.raise_for_status()
        data = response.json()
        print("[INFO] NPM server is running. API response:", data)
        return True
    except requests.ConnectionError:
        print("[INFO] NPM server is not running.")
        return False
    except requests.HTTPError as e:
        print(f"[ERROR] HTTP error: {e}")
        return False

def start_npm():
    try:
        current_directory = os.getcwd()
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        target_directory = os.path.join(parent_directory, 'suno-api')
        cmd = f'cd {shlex.quote(target_directory)} && npm run dev'

        osascript_cmd = f"""
        tell application "Terminal"
            activate
            set newTab to do script "{cmd}"
            delay 1
            set terminalWindow to id of window 1
        end tell
        return terminalWindow
        """

        print("[INFO] Starting npm process...")
        result = subprocess.run(['osascript', '-e', osascript_cmd], capture_output=True, text=True)
        terminal_window_id = result.stdout.strip()
        print(f"[INFO] npm process started in Terminal window: {terminal_window_id}. Waiting for it to be fully up...")
        time.sleep(10)
        return terminal_window_id
    except Exception as e:
        print(f"[ERROR] Failed to start npm process: {e}")
        sys.exit(1)

def check_and_start_npm():
    if is_npm_running():
        return None

    terminal_window_id = start_npm()

    while not is_npm_running():
        print("[ERROR] NPM server is not running after the first attempt. Retrying...")
        terminal_window_id = start_npm()
        print("[INFO] Waiting 5 more seconds before re-checking...")
        time.sleep(5)

    print("[INFO] NPM server is confirmed to be running.")
    return terminal_window_id

def generate_song_if_needed():
    if not SONG_TO_USE:
        terminal_window_id = check_and_start_npm()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        suno_api_dir = os.path.join(script_dir, '..', 'suno-api')
        generate_song_script = os.path.join(suno_api_dir, 'generate_song.py')
        created_songs_dir = os.path.join(suno_api_dir, 'created_songs')

        if not os.path.exists(generate_song_script):
            print(f"[ERROR] generate_song.py not found at {generate_song_script}")
            sys.exit(1)

        if not os.path.exists(created_songs_dir):
            os.makedirs(created_songs_dir)

        try:
            existing_songs = set(os.listdir(created_songs_dir))
            print("[INFO] Trying to generate a song...")
            process = subprocess.run([sys.executable, generate_song_script, '--prompt', SONG_PROMPT])
            
            if process.returncode == 2:  # 2 is the exit code for insufficient credits
                print("[INFO] Insufficient credits for generating song. Proceeding without it.")
                return
            elif process.returncode != 0:
                print(f"[ERROR] generate_song.py failed with return code: {process.returncode}")
                sys.exit(1)

            print("[INFO] Waiting for the song to be generated...")
            max_wait_time = 300
            wait_interval = 10
            elapsed_time = 0

            new_song = None

            while elapsed_time < max_wait_time:
                current_songs = set(os.listdir(created_songs_dir))
                new_files = current_songs - existing_songs
                mp3_files = [f for f in new_files if f.endswith('.mp3')]

                if mp3_files:
                    mp3_files_fullpaths = [os.path.join(created_songs_dir, f) for f in mp3_files]
                    mp3_files_fullpaths.sort(key=lambda f: os.path.getmtime(f), reverse=True)
                    new_song = mp3_files_fullpaths[0]
                    print(f"[INFO] New song generated: {new_song}")
                    break

                time.sleep(wait_interval)
                elapsed_time += wait_interval

            if new_song:
                global_vars_path = os.path.join(script_dir, 'GLOBAL_VARIABLES.py')
                with open(global_vars_path, 'r') as f:
                    lines = f.readlines()

                with open(global_vars_path, 'w') as f:
                    for line in lines:
                        if line.startswith('SONG_TO_USE'):
                            song_path_str = os.path.normpath(new_song).replace('\\', '\\\\')
                            f.write(f'SONG_TO_USE = "{song_path_str}"\n')
                        else:
                            f.write(line)
                print(f"[INFO] Updated SONG_TO_USE in GLOBAL_VARIABLES.py to {new_song}")
            else:
                print("[ERROR] Failed to generate song within the time limit.")
                sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to generate song: {e}")
            sys.exit(1)
        finally:
            if terminal_window_id:
                close_terminal_window(terminal_window_id)
    else:
        print("[INFO] SONG_TO_USE is already specified.")

def close_terminal_window(terminal_window_id):
    try:
        close_cmd = f'tell application "Terminal" to close (every window whose id is {terminal_window_id})'
        print(f"[INFO] Terminal window ID to close: {terminal_window_id}")
        subprocess.run(['osascript', '-e', close_cmd], check=True)
        print("[INFO] Terminal window closed.")
    except Exception as e:
        print(f"[ERROR] Failed to close Terminal window with ID {terminal_window_id}: {e}")

def main():
    generate_song_if_needed()
    
    initial_images_dir = 'initial_images'
    storylines_dir = 'storylines'

    if not os.path.isdir(initial_images_dir):
        print(f"[ERROR] Directory {initial_images_dir} does not exist.")
        return

    os.makedirs(storylines_dir, exist_ok=True)

    image_files = sorted([
        f for f in os.listdir(initial_images_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    if not image_files:
        print(f"[ERROR] No image files found in {initial_images_dir}")
        return

    story_chapters = []
    model_name = 'manual'

    for i, image_file in enumerate(image_files):
        image_path = os.path.abspath(os.path.join(initial_images_dir, image_file))
        chapter = {
            'chapter': f'Image {i+1}',
            f'chapter_image_location_{model_name}': image_path
        }
        story_chapters.append(chapter)

    data = {
        'story_chapters': story_chapters
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_filename = f'{timestamp}_manual_storyline.json'
    json_filepath = os.path.join(storylines_dir, json_filename)
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[INFO] JSON file created with image paths. Saved to {json_filepath}")

if __name__ == '__main__':
    main()