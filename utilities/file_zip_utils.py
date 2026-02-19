import os
import zipfile
import shutil
from datetime import datetime

def zip_files(directory_to_zip, output_directory='zip_uploads', output_filename=None):
    archive_directory = os.path.join(output_directory, 'archive')

    # Move existing .zip files to the archive directory
    if not os.path.exists(archive_directory):
        os.makedirs(archive_directory)

    for file_name in os.listdir(output_directory):
        full_file_path = os.path.join(output_directory, file_name)
        if os.path.isfile(full_file_path) and file_name.endswith('.zip'):
            shutil.move(full_file_path, os.path.join(archive_directory, file_name))
            print(f"[INFO] Moved {file_name} to archive folder")

    # Generate the new zip filename with timestamp if not provided
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_filename = f"{timestamp}.zip"

    output_filepath = os.path.join(output_directory, output_filename)

    # Zip the files in the provided directory
    with zipfile.ZipFile(output_filepath, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for file_name in os.listdir(directory_to_zip):
            file_path = os.path.join(directory_to_zip, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                zipf.write(file_path, file_name)

    print(f"[INFO] Zip file created at location: {output_filepath}")
    
    return output_filepath

def move_zip_file_to_pet_directory(zip_filepath, pet_directory):
    if not os.path.exists(pet_directory):
        os.makedirs(pet_directory)
        
    # Move the zip file to the specified pet directory
    shutil.move(zip_filepath, pet_directory)
    new_zip_path = os.path.join(pet_directory, os.path.basename(zip_filepath))
    print(f"[INFO] Moved zip file to {new_zip_path}")
    
    return new_zip_path