
# run_all.py

import subprocess
import sys
import os
import time
import json
import datetime  # Correctly import the entire datetime module

def run_script(script_name):
    """
    Runs a Python script using the same interpreter and captures its output.

    Args:
        script_name (str): The name of the script to run.

    Returns:
        bool: True if the script ran successfully, False otherwise.
    """
    # Construct the command to run the script
    command = [sys.executable, script_name]
    
    print(f"\nRunning script: {script_name}\n{'=' * 50}")
    
    try:
        # Run the script and capture the output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        
        # Print the script's output
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running {script_name}:\n")
        print(e.output)
        return False  # Indicate failure

def find_latest_json(storylines_dir):
    """
    Finds the latest JSON file in the specified directory with the suffix '_manual_storyline.json'.

    Args:
        storylines_dir (str): The directory to search for JSON files.

    Returns:
        str or None: The path to the latest JSON file, or None if not found.
    """
    json_files = [f for f in os.listdir(storylines_dir) if f.endswith('_manual_storyline.json')]
    if not json_files:
        return None

    # Sort the files by modification time in descending order
    json_files.sort(key=lambda f: os.path.getmtime(os.path.join(storylines_dir, f)), reverse=True)
    latest_json_filename = json_files[0]
    return os.path.join(storylines_dir, latest_json_filename)

def update_json_with_runtime(json_filepath, total_runtime_seconds):
    """
    Updates the specified JSON file by adding the 'total_script_runtime' fields.

    Args:
        json_filepath (str): The path to the JSON file to update.
        total_runtime_seconds (float): The total runtime in seconds.
    """
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON file {json_filepath}: {e}")
        return

    # Add or update the 'total_script_runtime' fields
    data['total_script_runtime_seconds'] = total_runtime_seconds
    # Convert seconds to a human-readable format (HH:MM:SS)
    data['total_script_runtime_human_readable'] = str(datetime.timedelta(seconds=round(total_runtime_seconds)))

    try:
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"[INFO] Updated JSON file with total runtime: {json_filepath}")
    except Exception as e:
        print(f"[ERROR] Failed to write to JSON file {json_filepath}: {e}")

def main():
    # List of scripts to run in order
    scripts_to_run = [
        '1_prepare_images.py',
        '2_create_movie.py',
        '3_apply_zoompan.py',
        '4_add_text.py',
        '5_clean_up.py'
    ]
    
    # Check that all scripts exist
    for script in scripts_to_run:
        if not os.path.isfile(script):
            print(f"Error: {script} not found in the current directory.")
            sys.exit(1)
    
    print(f"[INFO] Starting the entire script run at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Record the start time
    start_time = time.time()
    
    # Run each script
    for script in scripts_to_run:
        success = run_script(script)
        if not success:
            print(f"[ERROR] Execution halted due to failure in {script}.")
            sys.exit(1)  # Exit if any script fails
    
    # Record the end time
    end_time = time.time()
    
    # Calculate total runtime
    total_runtime = end_time - start_time
    print(f"\n[INFO] All scripts executed successfully.")
    print(f"[INFO] Total runtime: {total_runtime:.2f} seconds.")
    
    # Locate the latest JSON file in 'storylines' directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    storylines_dir = os.path.join(script_dir, 'storylines')
    latest_json = find_latest_json(storylines_dir)
    
    if latest_json:
        print(f"[INFO] Latest JSON file found: {latest_json}")
        update_json_with_runtime(latest_json, total_runtime)
    else:
        print(f"[WARNING] No '_manual_storyline.json' files found in {storylines_dir}. Skipping runtime update.")
    
    print(f"[INFO] run_all.py completed at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()