import os
import json
import re
import time
import shutil
from datetime import datetime
from GLOBAL_VARIABLES import *
from utilities.ollama_utils import (
    install_and_setup_ollama,
    kill_existing_ollama_service,
    clear_gpu_memory,
    stop_ollama_service,
    get_story_response_from_model
)
from utilities.replicate_utils import get_replicate_default_values
from utilities.file_zip_utils import zip_files, move_zip_file_to_pet_directory

MODEL_NAME = GLOBAL_MODEL_NAME
NUMBER_OF_FACTS = NUMBER_OF_FACTS
PET_DESCRIPTION = PET_DESCRIPTION.strip()

STORYLINE_TEMPLATE = (
    "Create a fun and heartwarming story based on the following details of a pet that needs adopting: "
    "\"{pet_description}\". Make sure the story is engaging, clean, and showcases the pet's personality and details well. "
    "The story should make the pet appealing to potential adopters."
)

base_output_dir = "pet_directory"
temp_uploads_dir = os.path.join("temp", "temp_uploads")

def move_uploaded_files(new_directory_path):
    real_image_dir = os.path.join(new_directory_path, 'real_images')
    if not os.path.exists(real_image_dir):
        os.makedirs(real_image_dir)
    
    for filename in os.listdir(temp_uploads_dir):
        file_path = os.path.join(temp_uploads_dir, filename)
        if os.path.isfile(file_path):
            new_file_path = os.path.join(real_image_dir, filename)
            try:
                shutil.move(file_path, new_file_path)
                print(f"[INFO] Moved {filename} to {real_image_dir}")
            except Exception as error:
                print(f"[ERROR] Failed to move {filename} to {real_image_dir}. Error: {error}")

def sanitize_name(name):
    return re.sub(r'[\W_]+', '_', name).lower()

def get_response_from_model(model_name, prompt):
    start_time = time.time()
    response = get_story_response_from_model(model_name, prompt)
    end_time = time.time()
    response_time = end_time - start_time
    return response.strip(), response_time

def clean_response(response):
    patterns = [
        r'^(Here.+:\n+\*\*Image:\*\*)',  # Remove patterns like "Here is a detailed visual description for an image prompt based on Jackson:\n\n**Image:**"
        r'^\s+',                         # Remove leading whitespace
        r'\s+$',                         # Remove trailing whitespace
        r'\\n+',                         # Remove backslash followed by 'n'
        r'\\',                           # Remove any remaining backslashes
        r'\"$',                          # Remove any trailing quotation marks
    ]
    for pattern in patterns:
        response = re.sub(pattern, "", response)
    return response.strip()

def extract_pet_detail(model_name, pet_description, detail_type):
    if detail_type == "species of pet":
        detail_type_specific_prompt = (
            "Based on the following pet description, respond with the general species (like dog, cat, bird) "
            "and avoid specific breeds or types. Only respond with one word from this set: dog, cat, bird, reptile, fish, rodent."
        )
    else:
        detail_type_specific_prompt = f"Respond with only the {detail_type} without any preamble or filler text."

    print(f"[INFO] Extracting {detail_type}...")
    prompt = f"{detail_type_specific_prompt}: {pet_description}"
    response, response_time = get_response_from_model(model_name, prompt)
    if not response:
        response = "unsure"
    print(f"Full JSON response: {response}")
    detail = clean_response(response)
    print(f"[INFO] Extracted {detail_type}: {detail}")
    return detail, response_time

def create_storyline(model_name, pet_description):
    print("[INFO] Creating storyline...")
    storyline_prompt = STORYLINE_TEMPLATE.format(pet_description=pet_description) + " Respond with only the storyline."
    storyline, response_time = get_response_from_model(model_name, storyline_prompt)
    if not storyline:
        storyline = "unsure"
    storyline_cleaned = clean_response(storyline)
    print("[INFO] Storyline created.")
    return storyline_cleaned, response_time

def extract_encouraging_facts(model_name, pet_description, number_of_facts):
    facts = {}
    previous_facts = ""
    for i in range(1, number_of_facts + 1):
        print(f"[INFO] Generating encouraging fact {i}...")
        prompt = (
            f"Based on the following pet description and the previous facts {previous_facts}, "
            f"provide a new, unique, and encouraging fact number {i} about the pet to promote adoption. "
            f"Respond with only the fact and no additional words: {pet_description}"
        )
        fact, response_time = get_response_from_model(model_name, prompt)
        if not fact:
            fact = "unsure"
        cleaned_fact = clean_response(fact)
        print(f"Full JSON response: {fact}")
        facts[f"fact_{i}"] = {"fact": cleaned_fact, "response_time": response_time}
        print(f"[INFO] Encouraging fact {i}: {cleaned_fact}")
        if fact == "N/A" or not cleaned_fact:
            break
        previous_facts += f" Fact {i}: {cleaned_fact}."
    return facts

def generate_signage_prompt(model_name, fact):
    print(f"[INFO] Generating signage prompt for the fact: {fact}...")
    prompt = f"Give a 3 or 4 word max description of this scene: {fact}. Respond with only the signage text."
    signage, response_time = get_response_from_model(model_name, prompt)
    if not signage:
        signage = "unsure"
    cleaned_signage = clean_response(signage)
    print(f"[INFO] Signage prompt: {cleaned_signage}")
    return cleaned_signage, response_time

def write_to_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[INFO] Updated JSON file: {filepath}")

def generate_unique_trigger_word(pet_name, pet_species):
    trigger_word = f"{pet_species}_{pet_name}".lower().replace('o', '0').replace('e', '3').replace('i', '1')
    print(f"[INFO] Generated unique TRIGGER_WORD: {trigger_word}")
    return trigger_word

def generate_prompt_base(model_name, pet_description, pet_breed, pet_age, pet_size):
    prompt_request = (
        f"Provide a concise visual description for an image prompt of a pet with these characteristics: "
        f"breed: {pet_breed}, age: {pet_age}, size: {pet_size}, details: {pet_description}. "
        f"Respond only with the description. No introductory text."
    )
    prompt_response, _ = get_response_from_model(model_name, prompt_request)
    cleaned_prompt = clean_response(prompt_response)
    return cleaned_prompt

def main():
    # Kill any existing service before starting
    kill_existing_ollama_service()
    clear_gpu_memory()
    
    # Install and setup the Ollama model
    install_and_setup_ollama(MODEL_NAME)
    print("[INFO] Setting up the Ollama model. Please wait...")

    start_time = time.time()
    print("[INFO] Starting the pet details extraction process...")

    response_times = {}
    initial_data = {}

    # Extract pet details
    pet_name, name_response_time = extract_pet_detail(MODEL_NAME, PET_DESCRIPTION, "name of the pet")
    pet_type, type_response_time = extract_pet_detail(MODEL_NAME, PET_DESCRIPTION, "species of pet")

    response_times["name"] = name_response_time
    response_times["type"] = type_response_time

    initial_data["name"] = pet_name
    initial_data["type"] = pet_type

    sanitized_type = sanitize_name(pet_type)
    sanitized_name = sanitize_name(pet_name)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pet_dir_name = f"{timestamp}_{sanitized_type}_{sanitized_name}"
    pet_dir_path = os.path.join(base_output_dir, pet_dir_name)
    if not os.path.exists(pet_dir_path):
        print(f"[INFO] Creating directory: {pet_dir_path}")
        os.makedirs(pet_dir_path)

    json_filename = f"{pet_dir_name}.json"
    json_filepath = os.path.join(pet_dir_path, json_filename)

    replicate_values = get_replicate_default_values()
    initial_data["replicate_configs"] = replicate_values

    # Generate unique TRIGGER_WORD
    print("[INFO] Generating unique TRIGGER_WORD...")
    unique_trigger_word = generate_unique_trigger_word(sanitized_name, sanitized_type)
    initial_data["replicate_configs"]["TRIGGER_WORD"] = unique_trigger_word

    # Generate custom PROMPT_BASE
    pet_breed = initial_data.get("breed", "unknown breed")
    pet_age = initial_data.get("age", "unknown age")
    pet_size = initial_data.get("size", "unknown size")

    print("[INFO] Generating custom PROMPT_BASE...")
    custom_prompt_base = generate_prompt_base(MODEL_NAME, PET_DESCRIPTION, pet_breed, pet_age, pet_size)
    initial_data["replicate_configs"]["PROMPT_BASE"] = custom_prompt_base

    # Add TRAINING_CONFIGS to initial data
    initial_data["TRAINING_CONFIGS"] = {
        "STEPS": STEPS,
        "LORA_RANK": LORA_RANK,
        "OPTIMIZER": OPTIMIZER,
        "BATCH_SIZE": BATCH_SIZE,
        "RESOLUTION": RESOLUTION,
        "AUTOCAPTION": AUTOCAPTION,
        "LEARNING_RATE": LEARNING_RATE,
        "DESCRIPTION": DESCRIPTION,
        "USE_CAPTIONS": USE_CAPTIONS,
        "HARDWARE": HARDWARE,
        "MAX_RETRIES": MAX_RETRIES,
        "RETRY_DELAY": RETRY_DELAY,
        "MODEL_VERSION": MODEL_VERSION,
        "MODE": MODE,
        "VISIBILITY": VISIBILITY,
    }

    # Write initial data to JSON
    write_to_json(json_filepath, initial_data)

    # Additional details
    details = [
        "pet ID",
        "gender of the pet",
        "age of the pet",
        "breed of the pet",
        "size of the pet",
        "location of the pet",
        "behavioral characteristics of the pet",
        "additional details about the pet"
    ]

    # Extract each detail and update JSON
    for detail in details:
        detail_key = detail.replace(" of the pet", "").replace(" ", "_")
        detail_value, response_time = extract_pet_detail(MODEL_NAME, PET_DESCRIPTION, detail)
        if not detail_value:
            detail_value = "unsure"
        response_times[detail_key] = response_time
        initial_data[detail_key] = detail_value
        write_to_json(json_filepath, initial_data)

    print("[INFO] All pet details extracted. Now creating the storyline...")

    storyline, response_time = create_storyline(MODEL_NAME, PET_DESCRIPTION)
    response_times["storyline"] = response_time
    initial_data["storyline"] = storyline
    write_to_json(json_filepath, initial_data)

    print("[INFO] Storyline created successfully. Generating encouraging facts...")

    encouraging_facts = extract_encouraging_facts(MODEL_NAME, PET_DESCRIPTION, NUMBER_OF_FACTS)
    initial_data.update(encouraging_facts)
    write_to_json(json_filepath, initial_data)

    # Fetch updated TRIGGER_WORD and PROMPT_BASE from replicate_configs
    TRIGGER_WORD = initial_data["replicate_configs"]["TRIGGER_WORD"]
    PROMPT_BASE = initial_data["replicate_configs"]["PROMPT_BASE"]
    PET_TYPE = initial_data.get("type", "unknown pet").lower()

    # Generate image prompts and update JSON
    for i in range(1, NUMBER_OF_FACTS + 1):
        fact_key = f"fact_{i}"
        if fact_key not in initial_data:
            break
        fact = initial_data[fact_key]["fact"]

        cleaned_fact = clean_response(fact)

        prompt_request = f"Create an image prompt in 200 characters or less that accentuates the following activity: '{cleaned_fact}'. Respond with only the prompt and no additional words."
        prompt_response, prompt_response_time = get_response_from_model(MODEL_NAME, prompt_request)
        if not prompt_response:
            prompt_response = "unsure"
        cleaned_prompt = clean_response(prompt_response)

        signage_prompt, signage_response_time = generate_signage_prompt(MODEL_NAME, cleaned_prompt)

        # Adjusting how full_prompt is constructed
        full_prompt = f"a signage that says: {signage_prompt} {TRIGGER_WORD} {PET_TYPE} {cleaned_prompt}"
        
        # Sanitize full_prompt to remove any forward or backslashes
        full_prompt = full_prompt.replace("\\", "").replace("/", "")
        
        initial_data[f"IMAGE_{i}_PROMPT"] = cleaned_prompt
        initial_data[f"IMAGE_{i}_PROMPT_response_time"] = prompt_response_time
        initial_data[f"SIGNAGE_PROMPT_{i}"] = signage_prompt
        initial_data[f"replicate_full_prompt_image_{i}"] = full_prompt
        
        # Update JSON with new prompt details
        write_to_json(json_filepath, initial_data)

    # Check and zip files in the zip_uploads directory
    zip_dir = "zip_uploads"
    print("[INFO] Checking and zipping files in zip_uploads...")
    if os.path.exists(zip_dir) and os.listdir(zip_dir):
        # Zip the files
        zip_file_path = zip_files(zip_dir, "zip_uploads")

        # Move the zip file to the pet directory
        new_zip_path = move_zip_file_to_pet_directory(zip_file_path, pet_dir_path)
        initial_data["user_uploaded_images_zip"] = new_zip_path
        write_to_json(json_filepath, initial_data)
    else:
        initial_data["user_uploaded_images_zip"] = ""  # Set to empty string if no files found
        print("[INFO] No files found to zip. Setting user_uploaded_images_zip to an empty value.")

    end_time = time.time()
    total_time_taken = end_time - start_time

    initial_data["summary"] = {
        "total_time_taken": round(total_time_taken, 2),
        "average_response_time_per_question": round(sum(response_times.values()) / len(response_times), 2),
        "response_times": response_times
    }

    # Final update to JSON
    write_to_json(json_filepath, initial_data)

    print(f"[INFO] Generated initial JSON file: {json_filepath}")
    print(f"[INFO] Here is your storyline:\n{storyline}")

    print("[INFO] === SUMMARY ===")
    print(f"[INFO] Total time taken: {total_time_taken:.2f} seconds")
    print(f"[INFO] Average response time per question: {sum(response_times.values()) / len(response_times):.2f} seconds")
    print(f"[INFO] JSON file path: {json_filepath}")

    stop_ollama_service()
    clear_gpu_memory()

if __name__ == "__main__":
    main()