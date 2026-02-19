import subprocess
import sys
import os
import json
import shutil
import argparse

def run_script(script_name, json_file):
    try:
        result = subprocess.run([sys.executable, script_name, json_file], check=True)
        print(f"[INFO] Successfully ran {script_name} with {json_file}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] An error occurred while running {script_name}: {e}")
        sys.exit(1)

def update_global_variables(pet_description, google_drive_link):
    with open("GLOBAL_VARIABLES.py", "r") as f:
        lines = f.readlines()

    new_lines = []
    description_started = False
    for line in lines:
        if line.startswith("PET_DESCRIPTION"):
            new_lines.append(f'PET_DESCRIPTION = """\n{pet_description}\n"""\n')
            description_started = True
        elif "GOOGLE_DRIVE_PATH_TO_IMAGES_ZIP" in line:
            new_lines.append(f'GOOGLE_DRIVE_PATH_TO_IMAGES_ZIP = "{google_drive_link}"\n')
        elif description_started and line.strip().startswith('"""'):
            description_started = False
        elif not description_started:
            new_lines.append(line)

    with open("GLOBAL_VARIABLES.py", "w") as f:
        f.writelines(new_lines)

    print("[INFO] Updated GLOBAL_VARIABLES.py with the new pet description and Google Drive link.")

def main(json_file=None):
    if json_file:
        # Check if running within app.py context
        is_app_context = os.getenv('APP_CONTEXT', 'false').lower() == 'true'
        
        if is_app_context:
            json_file_path = os.path.join("app_submit_log", json_file)
        else:
            json_file_path = json_file
        
        print(f"[INFO] Reading input JSON file: {json_file_path}")
        with open(json_file_path) as f:
            data = json.load(f)

        pet_description = data.get('PET_DESCRIPTION', "")
        gdrive_link = data.get('zip_of_images_via_gdrive', "")
        update_global_variables(pet_description, gdrive_link)

        # Log the Google Drive link if present
        if 'zip_of_images_via_gdrive' in data:
            print(f"[INFO] Google Drive link for zip file: {data['zip_of_images_via_gdrive']}")

        # Run the first script
        print("[INFO] Running 1_gather_pet_data.py...\n")
        run_script("1_gather_pet_data.py", json_file)

        # Run the second script
        print("[INFO] Running 2_train_a_lora.py...\n")
        run_script("2_train_a_lora.py", json_file)

        # Run the third script
        print("[INFO] Running 3_create_images_of_pet.py...\n")
        run_script("3_create_images_of_pet.py", json_file)

        # Move the JSON file to the pet directory folder and rename it to config.json
        try:
            pet_directory = data['PET_DESCRIPTION'].split()[0].lower()  # Use the first word of the pet description as the directory name
            safe_pet_directory = ''.join(e for e in pet_directory if e.isalnum() or e == "_")
            target_directory = os.path.join("pet_directory", safe_pet_directory)
            os.makedirs(target_directory, exist_ok=True)
            shutil.move(json_file_path, os.path.join(target_directory, "config.json"))
            print(f"[INFO] Moved {json_file_path} to {target_directory}/config.json")
        except Exception as e:
            print(f"[ERROR] Moving JSON file failed: {e}")
            sys.exit(1)

        print("#### GENERATION COMPLETED! ####")
        
    else:
        # Default operation if no JSON file is provided
        print("[INFO] Running 1_gather_pet_data.py without JSON file...\n")
        run_script("1_gather_pet_data.py", "")

        print("[INFO] Running 2_train_a_lora.py without JSON file...\n")
        run_script("2_train_a_lora.py", "")

        print("[INFO] Running 3_create_images_of_pet.py without JSON file...\n")
        run_script("3_create_images_of_pet.py", "")

        print("#### GENERATION COMPLETED! ####")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all scripts to generate pet images.")
    parser.add_argument("json_file", nargs='?', default=None, help="Path to the JSON file with pet description.")

    args = parser.parse_args()
    main(args.json_file)