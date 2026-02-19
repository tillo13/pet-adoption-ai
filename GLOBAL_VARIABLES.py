# global_variables.py
#####START####these will change dynamically if using app.py, or can run independently also######
GOOGLE_DRIVE_PATH_TO_IMAGES_ZIP = ""

# Local path to the images ZIP file intended for file.io upload
FILE_IO_PATH_TO_IMAGES_ZIP = "zip_uploads/images.zip"


# Pet Adoption Information (Sample description; adjust as needed)
PET_DESCRIPTION = """
Honey is pure sweetness! Honey is a precious 1-year-old Lab mix has love just oozing out of her. There's nothing Honey loves more than your company (except maybe toys). Whether it's getting belly rubs, booty scritches, or playing with toys, she's happy as can be. Honey does well with other dogs but needs a home with no cats, chickens, or other small animals. She can be protective of her toys and bed, so she will likely do best with just adults. Honey is not a fit for an apartment or condo and would appreciate living in a quiet neighborhood. If you're ready to welcome home this sweetheart, come meet her today!

Behavioral characteristics
Cuddler
This pet loves to snuggle.

Experienced with Dogs
This pet enjoys the company of dogs.

No Cats
This pet does not enjoy the company of cats.

No Small Animals
This pet cannot go to a home with small pets like rodents and birds.

Playful
This pet loves toys and playtime.

Additional details
Pet ID
54621044
Pet type
Dog
Sex
Female
Age
2 years old, Young
Breed
Labrador Retriever - American Pit Bull Terrier
Size
Medium, 59.00 pounds
Location
Shelter, Kennel #:Dog Room
"""

#####END####these will change dynamically if using app.py, or can run independently also######

# Replicate and Hugging Face Configurations
REPLICATE_OWNER = "your-replicate-username"
HUGGING_FACE_OWNER = "your-huggingface-username"
#TRIGGER_WORD = "marina".lower().replace(' ', '_')

# Training Configurations
#BASE_MODEL_NAME = f"flux1-dev-{TRIGGER_WORD}"
STEPS = 1000
LORA_RANK = 16
OPTIMIZER = "adamw8bit"
BATCH_SIZE = 1
RESOLUTION = "512, 768, 1024"
AUTOCAPTION = True
LEARNING_RATE = 0.0004

DESCRIPTION = "A fine-tuned FLUX.1 model for pet adoption"
USE_CAPTIONS = False
HARDWARE = "gpu-t4"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
MODEL_VERSION = "ostris/flux-dev-lora-trainer:7f53f82066bcdfb1c549245a624019c26ca6e3c8034235cd4826425b61e77bec"

# Mode flag: Change to "PRODUCTION" when ready for production
MODE = "DEVELOPMENT"  # or "PRODUCTION"
VISIBILITY = "private" if MODE == "DEVELOPMENT" else "public"


REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
GLOBAL_MODEL_NAME = 'llama3'
NUMBER_OF_FACTS = 5
EMAIL_ON_COMPLETION = True  # Set to True to enable email notifications
EMAIL_RECIPIENTS = ["your-email@example.com"]  # Update with the actual recipient emails
