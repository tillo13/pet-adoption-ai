import os
import requests

def upload_file_to_fileio(file_path):
    """Upload a file to file.io and return the download URL."""
    url = "https://file.io/"
    print(f"[INFO] Starting the upload to file.io for file: {file_path}")

    # Check if the file exists
    if not os.path.isfile(file_path):
        print(f"[ERROR] File not found at path: {file_path}")
        return None

    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(url, files=files)
            print(f"[INFO] Upload to file.io response status code: {response.status_code}")

            response_data = response.json()
            print(f"[INFO] file.io response data: {response_data}")
            
            if response_data.get('success'):
                download_link = response_data['link']
                print(f"[INFO] Successfully uploaded to file.io. Download URL: {download_link}")
                return download_link
            else:
                print(f"[ERROR] Failed to upload to file.io: {response_data}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception during file upload to file.io: {e}")
        return None