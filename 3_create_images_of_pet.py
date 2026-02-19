import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from utilities.replicate_utils import create_image, get_replicate_default_values
from utilities.gmail_utils import send_email
import time
from GLOBAL_VARIABLES import NUMBER_OF_FACTS, EMAIL_ON_COMPLETION, EMAIL_RECIPIENTS, PET_DESCRIPTION

# Load environment variables from .env file in the root directory
load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise Exception("Replicate API token not found. Please ensure it is set in the .env file.")

def log(message):
    """Helper function to print log messages with a timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def notify_completion(pet_dir_name, pet_data, image_paths):
    """Send an email notification upon completion."""
    subject = f"Pet Image Generation Completed for {pet_dir_name}"
    body = f"""
    <h1>Pet Image Generation Completed</h1>
    <p>The image generation for <b>{pet_dir_name}</b> has been completed successfully.</p>
    <p>Details:</p>
    <pre>{json.dumps(pet_data, indent=2)}</pre>
    """
    send_email(subject, body, EMAIL_RECIPIENTS, attachment_paths=image_paths, is_html=True)
    log(f"Email notification sent to: {', '.join(EMAIL_RECIPIENTS)}")

def main():
    log("create_images_of_pet.py script started.")
    
    pet_dir_base = "pet_directory"
    pet_subdirs = [f.path for f in os.scandir(pet_dir_base) if f.is_dir()]
    if not pet_subdirs:
        raise Exception("No pet directories found in pet_directory")

    latest_pet_dir = max(pet_subdirs, key=os.path.getmtime)
    json_files = [f for f in os.listdir(latest_pet_dir) if f.endswith('.json')]
    if not json_files:
        raise Exception(f"No JSON files found in the latest pet directory {latest_pet_dir}")

    latest_json_file = os.path.join(latest_pet_dir, json_files[0])
    log(f"Using JSON file: {latest_json_file}")

    with open(latest_json_file, 'r') as file:
        pet_data = json.load(file)

    replicate_defaults = get_replicate_default_values()
    log("Replicate default values loaded successfully.")
    
    image_dir_name = 'ai_images'
    image_dir_path = os.path.join(latest_pet_dir, image_dir_name)
    if not os.path.exists(image_dir_path):
        os.makedirs(image_dir_path)
    log(f"Image directory created at: {image_dir_path}")

    image_details = {}
    image_paths = []

    for i in range(1, NUMBER_OF_FACTS + 1):
        replicate_full_prompt_key = f"replicate_full_prompt_image_{i}"
        if replicate_full_prompt_key in pet_data:
            full_prompt = pet_data[replicate_full_prompt_key]
            log(f"Generating image for: {full_prompt}")
            
            start_time = time.time()
            try:
                image_urls = create_image(full_prompt, REPLICATE_API_TOKEN, pet_data)
                log(f"Image URLs returned: {image_urls}")
            except Exception as e:
                log(f"Error generating images: {e}, skipping to next.")
                continue
            
            end_time = time.time()
            generation_time = end_time - start_time
            log(f"Time taken for image generation: {generation_time:.2f} seconds")

            for index, url in enumerate(image_urls):
                try:
                    log(f"Downloading image from URL: {url}")
                    response = requests.get(url)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_name = f"{timestamp}_{index}.{replicate_defaults['OUTPUT_FORMAT']}"
                    image_path = os.path.join(image_dir_path, image_name)
                    
                    if response.status_code == 200:
                        with open(image_path, 'wb') as f:
                            f.write(response.content)
                        log(f"Image saved: {image_path}")

                        image_paths.append(image_path)
                        
                        if replicate_full_prompt_key not in image_details:
                            image_details[replicate_full_prompt_key] = {"images": [], "generation_time": generation_time}
                        image_details[replicate_full_prompt_key]["images"].append(image_path)
                    else:
                        log(f"Failed to download image from {url}, status code: {response.status_code}")
                except Exception as e:
                    log(f"Error downloading or saving image {url}: {e}")

    pet_data.update({"image_generation": image_details})
    pet_data.update({
        "EXTRA_LORA_MAIN_URL": replicate_defaults["EXTRA_LORA_MAIN_URL"],
        "EXTRA_LORA_NAME": replicate_defaults["EXTRA_LORA_NAME"]
    })
    
    try:
        with open(latest_json_file, 'w') as file:
            json.dump(pet_data, file, indent=2)
        log(f"Updated JSON file with image details and LORA info: {latest_json_file}")
    except Exception as e:
        log(f"Error updating JSON file {latest_json_file}: {e}")
    
    if EMAIL_ON_COMPLETION:
        notify_completion(latest_pet_dir, pet_data, image_paths)

    log("create_images_of_pet.py script finished.")

if __name__ == "__main__":
    main()