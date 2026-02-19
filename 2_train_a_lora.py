# train_lora.py

import os
import time
import json
import glob
from datetime import datetime
from dotenv import load_dotenv
from huggingface_hub import HfApi
from utilities.replicate_utils import (
    initialize_client,
    generate_model_name,
    generate_hf_repo_name,
    create_model,
    start_training,
    generate_direct_download_link,
    record_hf_repo_creation,
    get_training_status,
    monitor_training,
    get_model_versions
)
from utilities.fileio_utils import upload_file_to_fileio
from GLOBAL_VARIABLES import *

# Load environment variables from .env file
load_dotenv()

# Tokens from .env file
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# Ensure tokens are correctly loaded
if not REPLICATE_API_TOKEN:
    print("Error: REPLICATE_API_TOKEN is not set in the .env file")
    exit(1)

if not HUGGING_FACE_TOKEN and MODE == "PRODUCTION":
    print("Error: HUGGING_FACE_TOKEN is not set in the .env file")
    exit(1)

def get_latest_json_file(directory):
    """Get the most recent JSON file in the specified directory and its subdirectories."""
    json_files = glob.glob(os.path.join(directory, '**', '*.json'), recursive=True)
    if not json_files:
        print("Error: No JSON files found in the pet_directory.")
        return None
    latest_file = max(json_files, key=os.path.getctime)
    print(f"Latest JSON file: {latest_file}")
    return latest_file

def extract_trigger_word(json_file):
    """Extract the TRIGGER_WORD from the JSON file."""
    with open(json_file, 'r') as file:
        data = json.load(file)
        return data.get("replicate_configs", {}).get("TRIGGER_WORD")

def create_hf_repo(hf_token, repo_id, json_file):
    """Create a Hugging Face repository."""
    if MODE == "PRODUCTION":
        print_log_and_save(f"Creating a Hugging Face repository: {repo_id}", json_file=json_file)
        api = HfApi()
        try:
            response = api.create_repo(repo_id=repo_id, token=hf_token, private=(VISIBILITY == "private"), exist_ok=True)
            record_hf_repo_creation(response)
            print_log_and_save(f"Repository '{repo_id}' created or already exists.", json_file=json_file)
        except Exception as e:
            print_log_and_save(f"Error creating Hugging Face repository: {e}", json_file=json_file)
            exit(1)
    else:
        print("Skipping Hugging Face repository creation in DEVELOPMENT mode.")

def print_log_and_save(message, json_file, update_configs=False):
    """Prints the message, then appends it to the JSON file."""
    print(message)
    
    # Open the JSON file and load existing data
    if os.path.exists(json_file):
        with open(json_file, 'r') as file:
            json_data = json.load(file)
    else:
        json_data = {}

    # Append specific relevant information based on message content
    if "Model created:" in message:
        json_data["REPLICATE_MODEL_LINK"] = message.split(": ")[1]
    elif "Model URL:" in message:
        json_data["REPLICATE_MODEL_URL"] = message.split(": ")[1]
    elif "Direct download link generated:" in message:
        json_data["TRAINING_IMAGES_ZIP_FILE"] = message.split(": ")[1]
    elif "Training completed with status:" in message:
        json_data["REPLICATE_TRAINING_STATUS"] = message.split(": ")[1]
    
    # Update replicate_configs section if needed
    if update_configs:
        if "REPLICATE_MODEL_LINK" in json_data and "REPLICATE_MODEL_VERSION" in json_data:
            model_version_string = f"{REPLICATE_OWNER}/{json_data['REPLICATE_MODEL_LINK']}:{json_data['REPLICATE_MODEL_VERSION']}"
            if "replicate_configs" in json_data:
                json_data["replicate_configs"]["MODEL_VERSION"] = model_version_string

    # Save updated data back to JSON file
    with open(json_file, 'w') as file:
        json.dump(json_data, file, indent=2)

def generate_model_name(trigger_word):
    """Generate a unique model name with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{trigger_word}_{timestamp}"

def generate_hf_repo_name(trigger_word):
    """Generate a unique Hugging Face repository name with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{trigger_word}_{timestamp}"

def generate_direct_download_link(source, file_path):
    """Generate a direct download link based on the source specified."""
    if source == "file_io":
        print("[INFO] Attempting to upload and generate link using file.io...")

        if os.path.exists(file_path):
            print(f"[INFO] Image zip file exists at {file_path}")
            fileio_link = upload_file_to_fileio(file_path)
            if fileio_link:
                print(f"[INFO] File.io link generated: {fileio_link}")
                return fileio_link
            else:
                print("[ERROR] Failed to generate link using file.io, falling back to Google Drive.")
        else:
            print(f"[ERROR] File path does not exist: {file_path}")

    # Google Drive logic as fallback
    print("[INFO] Using Google Drive link.")
    return GOOGLE_DRIVE_PATH_TO_IMAGES_ZIP

def main():
    # Find the most recent JSON file in the pet_directory
    base_output_dir = "pet_directory"
    latest_json_file = get_latest_json_file(base_output_dir)
    if latest_json_file is None:
        print("Error: No JSON file found in the pet_directory.")
        exit(1)

    # Load the contents of the JSON file
    with open(latest_json_file, 'r') as file:
        json_data = json.load(file)

    trigger_word = extract_trigger_word(latest_json_file)
    if not trigger_word:
        print("Error: TRIGGER_WORD not found in the latest JSON file.")
        exit(1)

    print_log_and_save("Starting main process...", json_file=latest_json_file)

    client = initialize_client()
    print_log_and_save("Replicate client initialized successfully.", json_file=latest_json_file)

    model_name = generate_model_name(trigger_word)
    print_log_and_save(f"Generated model name: {model_name}", json_file=latest_json_file)

    hf_repo_name = generate_hf_repo_name(trigger_word)
    print_log_and_save(f"Generated Hugging Face repo name: {hf_repo_name}", json_file=latest_json_file)

    model = create_model(client, REPLICATE_OWNER, model_name, VISIBILITY, HARDWARE, DESCRIPTION)
    print_log_and_save(f"Model created: {model.name}", json_file=latest_json_file)
    print_log_and_save(f"Model URL: https://replicate.com/{model.owner}/{model.name}", json_file=latest_json_file)

    create_hf_repo(HUGGING_FACE_TOKEN, hf_repo_name, json_file=latest_json_file)

    if USE_CAPTIONS:
        print_log_and_save("Captions are enabled. Configure Llava3 as USE_CAPTIONS is set to True.", json_file=latest_json_file)
        exit(0)

    print_log_and_save(f"Starting training with model: {model.name} at {datetime.now()}", json_file=latest_json_file)

    # Check if user has uploaded images and use that path if available, else use default path
    user_uploaded_images_zip = json_data.get("user_uploaded_images_zip", "").strip()
    IMAGE_SOURCE = "file_io"
    FILE_IO_PATH = user_uploaded_images_zip if user_uploaded_images_zip else FILE_IO_PATH_TO_IMAGES_ZIP

    # Generate the direct download link for the image zip file
    direct_download_link = generate_direct_download_link(IMAGE_SOURCE, FILE_IO_PATH)
    if not direct_download_link:
        print_log_and_save("Error generating direct download link for the image file.", json_file=latest_json_file)
        exit(1)

    print_log_and_save(f"Direct download link generated: {direct_download_link}", json_file=latest_json_file)

    training = start_training(
        client, model, direct_download_link, STEPS, LORA_RANK, OPTIMIZER, BATCH_SIZE,
        RESOLUTION, AUTOCAPTION, trigger_word, LEARNING_RATE, 
        HUGGING_FACE_TOKEN if MODE == "PRODUCTION" else None, hf_repo_name, MODEL_VERSION, RETRY_DELAY, MAX_RETRIES
    )

    print_log_and_save(f"Training process started at {datetime.now()}. Monitoring progress...", json_file=latest_json_file)

    # Monitor the training status
    monitor_training(training.id)

    # Fetch and save the model versions after training is complete
    versions = get_model_versions(REPLICATE_OWNER, model_name)
    if versions and versions.get('results'):
        latest_version_id = versions['results'][0]['id']
        print_log_and_save(f"Fetched model version: {latest_version_id}", json_file=latest_json_file)

        # Save the REPLICATE_MODEL_VERSION to JSON
        if os.path.exists(latest_json_file):
            with open(latest_json_file, 'r') as file:
                json_data = json.load(file)
            json_data["REPLICATE_MODEL_VERSION"] = latest_version_id
            with open(latest_json_file, 'w') as file:
                json.dump(json_data, file, indent=2)

        # Update replicate_configs section with the new MODEL_VERSION
        print_log_and_save("Updating replicate_configs with new MODEL_VERSION", json_file=latest_json_file, update_configs=True)
    else:
        print_log_and_save("Failed to fetch model versions or no versions available.", json_file=latest_json_file)

if __name__ == "__main__":
    main()