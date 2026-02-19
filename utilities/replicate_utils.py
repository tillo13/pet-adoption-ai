import os
import replicate
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from collections import defaultdict
import json
from datetime import datetime
import time

# Load environment variables from .env file
load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

HEADERS = {
    'Authorization': f'Bearer {REPLICATE_API_TOKEN}',
    'Content-Type': 'application/json',
}

BASE_URL = 'https://api.replicate.com/v1'
SAVE_DIRECTORY = './usage_data'

# Make sure the save directory exists
os.makedirs(SAVE_DIRECTORY, exist_ok=True)

def get_replicate_default_values():
    return {
        "MODEL_VERSION": "placholder model",
        "TRIGGER_WORD": "plac3h0ld3r",
        "PROMPT_BASE": "placeholder base, ",
        "NUM_OUTPUTS": 1,
        "EXTRA_LORA": "https://civitai.com/api/download/models/758632?type=Model&format=SafeTensor",
        "EXTRA_LORA_MAIN_URL": "https://civitai.com/models/677725/cute-3d-cartoon-flux",
        "EXTRA_LORA_NAME": "Cute 3d Cartoon Flux",
        "LORA_SCALE": 1,
        "ASPECT_RATIO": "21:9",
        "OUTPUT_FORMAT": "png",
        "GUIDANCE_SCALE": 3.5,
        "OUTPUT_QUALITY": 100,
        "PROMPT_STRENGTH": 0.8,
        "EXTRA_LORA_SCALE": 1,
        "NUM_INFERENCE_STEPS": 28
    }

def create_image(prompt, api_token, config):
    os.environ['REPLICATE_API_TOKEN'] = api_token

    # Extract replicate configs from the nested structure
    replicate_configs = config["replicate_configs"]

    # Incorporate trigger word into the prompt
    final_prompt = f"{replicate_configs['TRIGGER_WORD']} {prompt}"

    output = replicate.run(
        replicate_configs["MODEL_VERSION"],
        input={
            "model": "dev",
            "prompt": final_prompt,
            "extra_lora": replicate_configs["EXTRA_LORA"],
            "lora_scale": replicate_configs["LORA_SCALE"],
            "num_outputs": replicate_configs["NUM_OUTPUTS"],
            "aspect_ratio": replicate_configs["ASPECT_RATIO"],
            "output_format": replicate_configs["OUTPUT_FORMAT"],
            "guidance_scale": replicate_configs["GUIDANCE_SCALE"],
            "output_quality": replicate_configs["OUTPUT_QUALITY"],
            "prompt_strength": replicate_configs["PROMPT_STRENGTH"],
            "extra_lora_scale": replicate_configs["EXTRA_LORA_SCALE"],
            "num_inference_steps": replicate_configs["NUM_INFERENCE_STEPS"]
        }
    )
    return output

def get_data(endpoint):
    response = requests.get(f'{BASE_URL}/{endpoint}', headers=HEADERS)
    response.raise_for_status()
    return response.json()

def scrape_pricing():
    url = "https://replicate.com/pricing"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    hardware_pricing = {}
    image_model_pricing = {}

    # Scrape hardware costs
    for row in soup.select("tr"):
        cols = row.find_all("td")
        if len(cols) >= 2 and '$' in cols[1].text:
            hardware = cols[0].text.strip().lower().replace(' ', '-')
            cost_per_sec = float(cols[1].text.strip().replace('$', '').split('/')[0])
            hardware_pricing[hardware] = cost_per_sec

    # Scrape image model costs
    for row in soup.select("div.PricingTable__Row-sc-3x5vg3-0"):
        cols = row.find_all("span")
        if len(cols) == 2 and '$' in cols[1].text:
            model_name = cols[0].text.strip().lower().replace(' ', '-')
            cost_per_image = float(cols[1].text.strip().replace('$', '').split(' ')[0])
            image_model_pricing[model_name] = cost_per_image

    return hardware_pricing, image_model_pricing

def calculate_costs(data, hardware_pricing, image_model_pricing, key):
    total_cost = 0.0
    cost_breakdown = defaultdict(list)

    for item in data['results']:
        duration = item['metrics'].get(f'{key[:-1]}_time', 0)  # get 'predict_time', 'train_time', or 'deploy_time'
        if not duration:
            duration = item['metrics'].get('total_time', 0)  # fallback if specific time not available

        hardware = item.get('configuration', {}).get('hardware', 'cpu').lower().replace(' ', '-')

        # Correct for specialized hardware notated differently
        hardware = hardware.replace('gpu-', '').replace('gpu', 'gpu-')

        model = item.get('model', '').lower().replace(' ', '-')

        if model in image_model_pricing:
            cost_per_image = image_model_pricing[model]
            item_cost = cost_per_image
        else:
            cost_per_second = hardware_pricing.get(hardware, 0.0)
            item_cost = duration * cost_per_second

        total_cost += item_cost
        cost_breakdown[f"{hardware} ({model})"].append((duration, item_cost))

        # Debugging output to understand costs
        print(f"ID: {item['id']}, Hardware: {hardware}, Model: {model}, Duration: {duration}, Item Cost: {item_cost}")

    return total_cost, cost_breakdown

def save_response_to_file(filename, data):
    filepath = os.path.join(SAVE_DIRECTORY, filename)
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=2)

def fetch_and_save_data(endpoint, filename):
    response = requests.get(endpoint, headers=HEADERS)
    if response.status_code == 200:
        save_response_to_file(filename, response.json())
    elif response.status_code == 404:
        print(f"Resource not found for {filename}: {response.status_code}")
    else:
        print(f"Failed to fetch {filename}: {response.status_code}")

def fetch_predictions():
    url = f"{BASE_URL}/predictions"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        predictions = response.json().get('results', [])
        save_response_to_file("predictions.json", predictions)
        print("Predictions data saved.")
    else:
        print(f"Failed to fetch predictions data: {response.status_code}")

def fetch_trainings():
    url = f"{BASE_URL}/trainings"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        trainings = response.json().get('results', [])
        save_response_to_file("trainings.json", trainings)
        print("Trainings data saved.")
    else:
        print(f"Failed to fetch trainings data: {response.status_code}")

def fetch_detailed_training_info(training_id):
    url = f"{BASE_URL}/trainings/{training_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch detailed training info for {training_id}: {response.status_code}")
        return None

def fetch_detailed_trainings():
    trainings_filename = os.path.join(SAVE_DIRECTORY, "trainings.json")
    if not os.path.exists(trainings_filename):
        fetch_trainings()  # Ensure we have the main trainings.json

    with open(trainings_filename, 'r') as file:
        trainings = json.load(file)

    detailed_trainings = []
    for training in trainings:
        training_id = training['id']
        detailed_info = fetch_detailed_training_info(training_id)
        if detailed_info:
            detailed_trainings.append(detailed_info)

    detailed_trainings_filename = "detailed_trainings.json"
    save_response_to_file(detailed_trainings_filename, detailed_trainings)
    print("Detailed trainings data saved.")

def fetch_models():
    url = f"{BASE_URL}/models"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        models = response.json().get('results', [])
        save_response_to_file("models.json", models)
        print("Models data saved.")
    else:
        print(f"Failed to fetch models data: {response.status_code}")

def generate_direct_download_link(gdrive_url):
    """Generate a direct download link from a Google Drive URL."""
    file_id = gdrive_url.split('/d/')[1].split('/')[0]
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def initialize_client():
    """Initialize Replicate client."""
    print("Initializing Replicate client with API token...")
    client = replicate.Client(api_token=REPLICATE_API_TOKEN)
    print("Replicate client initialized successfully.")
    return client

def generate_model_name(base_name):
    """Generate a unique model name with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base_name}-{timestamp}"

def generate_hf_repo_name(base_name):
    """Generate a unique Hugging Face repository name with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base_name}-{timestamp}"

def create_model(client, owner, name, visibility, hardware, description):
    """Create a new model on Replicate."""
    print(f"Creating a new model on Replicate to store fine-tuned weights... (Model Name: {name})")
    try:
        model = client.models.create(
            owner=owner,
            name=name,
            visibility=visibility,
            hardware=hardware,
            description=description
        )
        print(f"Model created: {model.name}")
        print(f"Model URL: https://replicate.com/{model.owner}/{model.name}")
        return model
    except replicate.exceptions.ReplicateError as e:
        print(f"Error creating model on Replicate: {str(e)}")
        if "already exists" in str(e.detail):
            print(f"Model creation failed: {e.detail}")
            exit(1)
        else:
            raise

def start_training(client, model, path_to_images, steps, lora_rank, optimizer, batch_size, resolution,
                   autocaption, trigger_word, learning_rate, hf_token, hf_repo_id, version, retry_delay, max_retries):
    """Start the training process on Replicate."""
    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1} to start the training process...")

        try:
            print("Initializing training on Replicate...")
            training = client.trainings.create(
                version=version,
                input={
                    "input_images": path_to_images,
                    "steps": steps,
                    "lora_rank": lora_rank,
                    "optimizer": optimizer,
                    "batch_size": batch_size,
                    "resolution": resolution,
                    "autocaption": autocaption,
                    "trigger_word": trigger_word,
                    "learning_rate": learning_rate,
                    "hf_token": hf_token,
                    "hf_repo_id": hf_repo_id,
                },
                destination=f"{model.owner}/{model.name}"
            )

            print(f"Training initiation payload:\n"
                  f"{{\n"
                  f"  'input_images': '{path_to_images}',\n"
                  f"  'steps': {steps},\n"
                  f"  'lora_rank': {lora_rank},\n"
                  f"  'optimizer': '{optimizer}',\n"
                  f"  'batch_size': {batch_size},\n"
                  f"  'resolution': '{resolution}',\n"
                  f"  'autocaption': {autocaption},\n"
                  f"  'trigger_word': '{trigger_word}',\n"
                  f"  'learning_rate': {learning_rate},\n"
                  f"  'hf_token': '{hf_token}',\n"
                  f"  'hf_repo_id': '{hf_repo_id}'\n"
                  f" }}")

            print("Training has started successfully.")
            print(f"Training ID: {training.id}")
            print(f"Training URL: https://replicate.com/p/{training.id}")
            print("Monitor the training progress using the URL provided above. Refresh the page periodically to check the status.")
            return training

        except (requests.exceptions.RequestException) as e:
            print(f"Attempt {attempt + 1} failed due to network issue: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                exit(1)
        except replicate.exceptions.ReplicateError as e:
            print(f"Attempt {attempt + 1} failed due to Replicate error: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during attempt {attempt + 1}: {e}")
            exit(1)

def record_hf_repo_creation(response):
    """Record Hugging Face repository creation output."""
    print(f"Response: {response}")

# Newly added functions to utilities
def get_training_status(training_id):
    """Get the current status of a training."""
    url = f"{BASE_URL}/trainings/{training_id}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get training status: {response.status_code}")
        return None

def monitor_training(training_id, interval=60):
    """Continuously monitor the training status at specified intervals."""
    print(f"Starting to monitor training: {training_id}")

    while True:
        training_info = get_training_status(training_id)
        if training_info:
            status = training_info.get("status")
            print(f"Training Status: {status} (Checked at {time.strftime('%Y-%m-%d %H:%M:%S')})")
            
            if status in ["succeeded", "failed", "canceled"]:
                print(f"Training completed with status: {status}")
                break
        else:
            print("No training info available. Exiting.")
            break
        
        time.sleep(interval)

def get_model_versions(model_owner, model_name):
    """Get the versions of a given model."""
    url = f"{BASE_URL}/models/{model_owner}/{model_name}/versions"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        versions = response.json()
        return versions
    else:
        print(f"Failed to fetch model versions. Status code: {response.status_code}")
        return response.json()