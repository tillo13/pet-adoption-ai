import os
import json
import time
import replicate
import requests
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise Exception("Replicate API token not found. Please ensure it is set in the .env file.")

# Default user-defined variables
DEFAULT_PET_DIRECTORY_TO_USE = "20240923221530_dog_jackson"
DEFAULT_PROMPT = "A happy dog playing in the park."
DEFAULT_NUM_OUTPUTS = 1
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_GUIDANCE_SCALE = 3.5
DEFAULT_OUTPUT_FORMAT = "webp"
DEFAULT_OUTPUT_QUALITY = 90
DEFAULT_PROMPT_STRENGTH = 0.8
DEFAULT_EXTRA_LORA = ""
DEFAULT_EXTRA_LORA_SCALE = 1

def log(message):
    """Helper function to print log messages with a timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def get_json_file(pet_directory):
    """Get the JSON file from the specified pet directory."""
    json_files = [f for f in os.listdir(pet_directory) if f.endswith('.json')]
    if not json_files:
        raise Exception(f"No JSON files found in the specified pet directory {pet_directory}")
    latest_json_file = os.path.join(pet_directory, json_files[0])
    return latest_json_file

def read_json(file_path):
    """Read JSON data from a file."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def write_json(file_path, data):
    """Write JSON data to a file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def generate_image(prompt, model_version, trigger_word, num_outputs, aspect_ratio, output_format, guidance_scale, output_quality, prompt_strength, extra_lora, extra_lora_scale):
    """Generate an image using Replicate's API."""
    combined_prompt = f"{trigger_word} {prompt}"

    try:
        output = replicate.run(
            model_version,
            input={
                "prompt": combined_prompt,
                "num_outputs": num_outputs,
                "aspect_ratio": aspect_ratio,
                "output_format": output_format,
                "guidance_scale": guidance_scale,
                "output_quality": output_quality,
                "prompt_strength": prompt_strength,
                "extra_lora": extra_lora,
                "extra_lora_scale": extra_lora_scale
            }
        )
        return output
    except Exception as e:
        log(f"Error generating images: {e}")
        return []

def save_images(image_urls, image_dir, output_format):
    """Download and save images from provided URLs."""
    image_paths = []
    for index, url in enumerate(image_urls):
        try:
            log(f"Downloading image from URL: {url}")
            response = requests.get(url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_name = f"{timestamp}_{index}.{output_format}"
            image_path = os.path.join(image_dir, image_name)

            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                log(f"Image saved: {image_path}")
                image_paths.append(image_path)
            else:
                log(f"Failed to download image from {url}, status code: {response.status_code}")
        except Exception as e:
            log(f"Error downloading or saving image {url}: {e}")
    return image_paths

def main(pet_directory, prompt, num_outputs, aspect_ratio, output_format, guidance_scale, output_quality, prompt_strength, extra_lora, extra_lora_scale):
    log("4_create_new_images_via_existing_lora.py script started.")
    
    base_directory = "pet_directory"
    pet_dir = os.path.join(base_directory, pet_directory)
    log(f"Using pet directory: {pet_dir}")

    if not os.path.exists(pet_dir):
        raise Exception(f"The specified pet directory does not exist: {pet_dir}")

    latest_json_file = get_json_file(pet_dir)
    log(f"Using JSON file: {latest_json_file}")

    pet_data = read_json(latest_json_file)
    log("Loaded JSON data:")
    log(json.dumps(pet_data, indent=2))

    # Get the model version and trigger word from JSON
    try:
        model_version = pet_data["replicate_configs"]["MODEL_VERSION"]
        trigger_word = pet_data["replicate_configs"]["TRIGGER_WORD"]
    except KeyError as e:
        raise Exception(f"Key {e} not found in the JSON file")

    image_dir_name = 'ai_images'
    image_dir_path = os.path.join(pet_dir, image_dir_name)
    log(f"Image directory found at: {image_dir_path}")

    # Generate the combined prompt
    combined_prompt = f"{trigger_word} {prompt}"
    log(f"Generating image for prompt: {combined_prompt}")

    # Generate the image
    image_urls = generate_image(prompt, model_version, trigger_word, num_outputs, aspect_ratio, output_format, guidance_scale, output_quality, prompt_strength, extra_lora, extra_lora_scale)
    if not image_urls:
        log("No image URLs returned. Exiting.")
        return

    # Save the images to the directory
    image_paths = save_images(image_urls, image_dir_path, output_format)
    
    # Update JSON with the new image details
    generation_time = time.time()
    pet_data["new_image_generation"] = {
        "prompt": combined_prompt,
        "images": image_paths,
        "generation_time": generation_time
    }
    
    write_json(latest_json_file, pet_data)
    log(f"Updated JSON file with new image details: {latest_json_file}")

    log("4_create_new_images_via_existing_lora.py script finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pet_directory", type=str, default=DEFAULT_PET_DIRECTORY_TO_USE, help="Pet directory to use")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT, help="Prompt for generated image")
    parser.add_argument("--num_outputs", type=int, default=DEFAULT_NUM_OUTPUTS, help="Number of images to output")
    parser.add_argument("--aspect_ratio", type=str, default=DEFAULT_ASPECT_RATIO, help="Aspect ratio for generated image")
    parser.add_argument("--output_format", type=str, default=DEFAULT_OUTPUT_FORMAT, help="Format of the output images")
    parser.add_argument("--guidance_scale", type=float, default=DEFAULT_GUIDANCE_SCALE, help="Guidance scale for the diffusion process")
    parser.add_argument("--output_quality", type=int, default=DEFAULT_OUTPUT_QUALITY, help="Quality of the output images")
    parser.add_argument("--prompt_strength", type=float, default=DEFAULT_PROMPT_STRENGTH, help="Prompt strength for img2img / inpaint")
    parser.add_argument("--extra_lora", type=str, default=DEFAULT_EXTRA_LORA, help="Combine this fine-tune with another LoRA")
    parser.add_argument("--extra_lora_scale", type=float, default=DEFAULT_EXTRA_LORA_SCALE, help="Defines how strongly the extra LoRA is applied")
    
    args = parser.parse_args()
    
    main(args.pet_directory, args.prompt, args.num_outputs, args.aspect_ratio, args.output_format, args.guidance_scale, args.output_quality, args.prompt_strength, args.extra_lora, args.extra_lora_scale)