# GLOBAL_VARIABLES.py

# Song prompt to use if SONG_TO_USE is empty
SONG_PROMPT = "Create an upbeat and cute song about a dog named Honey getting adopted. The song should have a lively rhythm and adorable lyrics that celebrate the joy of finding a forever home. Think of playful melodies and happy beats that capture the heartwarming moment when Honey is welcomed into her new family."

# Whether to randomize the order of images
randomize_images = True  # Set to True to randomize, False to sort alphabetically

# Adjust the following variables if needed
# For example, DEFAULT_VIDEO_LENGTH if you want to specify a default length
DEFAULT_VIDEO_LENGTH = 55  # Default length in seconds if needed

# Variables for the text to display in the first and last 5 seconds
FIRST_5_SECOND_TEXT = """
Meet Honey!
"""

LAST_5_SECONDS_TEXT = """
You can adopt Honey @
Homeward Pet
13132 NE 177th Pl, 
Woodinville, WA 98072
"""

# Path to an MP3 file to use as background music (leave empty to auto-generate via Suno API)
SONG_TO_USE = ""
