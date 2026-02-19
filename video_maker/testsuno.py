import os
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get the SUNO_COOKIE from environment variables
suno_cookie = os.getenv('SUNO_COOKIE')

# Define the URL of the Suno API endpoint
url = "https://studio-api.suno.ai/api/get_limit"

# Define the headers with the cookie
headers = {
    "Cookie": suno_cookie,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://suno.com/",
    "Accept": "*/*",
}

# Make the GET request to the Suno API endpoint
response = requests.get(url, headers=headers)

# Check the response status code
if response.status_code == 200:
    # Print the JSON response from the API
    print(response.json())
else:
    print(f"Failed to retrieve data: {response.status_code} - {response.text}")