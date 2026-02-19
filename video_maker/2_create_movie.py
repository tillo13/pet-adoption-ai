import os
import subprocess
import shutil
import json
import re
import random  # Import random module
from datetime import datetime
from PIL import Image, ExifTags, ImageFilter
import math

# Import variables from GLOBAL_VARIABLES.py
try:
    from GLOBAL_VARIABLES import SONG_TO_USE, randomize_images
except ImportError:
    SONG_TO_USE = ""
    randomize_images = False  # Default to False if not specified

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def convert_images_to_jpeg(image_list, temp_directory):
    """Convert images to JPEG, correct orientation, resize and process."""
    temp_image_paths = []

    # Desired output size for the video frames
    desired_width = 1280
    desired_height = 720

    for i, image_path in enumerate(image_list):
        output_path = os.path.join(temp_directory, f'img{i:03d}.jpg')
        img = Image.open(image_path)

        # Correct image orientation
        img = correct_image_orientation(img)

        # Resize and process image
        img = resize_and_process_image(img, desired_width, desired_height)

        # Convert to RGB and save as JPEG
        img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=95)
        temp_image_paths.append(output_path)

    return temp_image_paths

def correct_image_orientation(img):
    try:
        # Rotate image based on EXIF Orientation
        exif = img._getexif()
        if exif is not None:
            orientation_key = next(
                (key for key, value in ExifTags.TAGS.items() if value == 'Orientation'), None)
            if orientation_key is not None:
                orientation = exif.get(orientation_key, None)
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
    except Exception as e:
        print(f"Error correcting image orientation: {e}")
    return img

def resize_and_process_image(img, desired_width, desired_height):
    # Determine if the image is portrait or landscape
    img_ratio = img.width / img.height
    desired_ratio = desired_width / desired_height

    if img_ratio < desired_ratio:
        # Image is taller than desired ratio (portrait)
        img = img.resize((int(img.width * desired_height / img.height), desired_height), Image.LANCZOS)

        # Create new image with black background
        new_img = Image.new('RGB', (desired_width, desired_height), (0, 0, 0))
        offset = ((desired_width - img.width) // 2, 0)
        new_img.paste(img, offset)
    else:
        # Image is wider than desired ratio (landscape)
        img = img.resize((desired_width, int(img.height * desired_width / img.width)), Image.LANCZOS)

        # Create blurred background
        background = img.copy().filter(ImageFilter.GaussianBlur(radius=20))
        background = background.resize((desired_width, desired_height), Image.LANCZOS)

        # Paste the original image on top of the background
        offset = (0, (desired_height - img.height) // 2)
        background.paste(img, offset)
        new_img = background

    return new_img



def generate_video_from_images(image_paths, audio_file, output_file, display_durations, temp_directory):
    # Ensure all directories exist
    ensure_directory_exists(temp_directory)

    temp_jpeg_images = convert_images_to_jpeg(image_paths, temp_directory)
    temp_video_paths = []

    # Create a video segment for each image
    for i, (image_file, duration) in enumerate(zip(temp_jpeg_images, display_durations)):
        image_video_path = os.path.join(temp_directory, f'image_video_{i:03d}.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-loop', '1', '-i', image_file, '-c:v', 'libx264',
            '-t', str(duration), '-pix_fmt', 'yuv420p', image_video_path
        ], check=True)
        temp_video_paths.append(image_video_path)

    # Concatenate the individual video segments
    videos_list_path = os.path.join(temp_directory, 'videos_list.txt')
    with open(videos_list_path, 'w') as f:
        for video_path in temp_video_paths:
            f.write(f"file '{video_path}'\n")

    concatenated_video_path = os.path.join(temp_directory, 'concatenated_video.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', videos_list_path,
        '-c', 'copy', concatenated_video_path
    ], check=True)

    # Adjust the audio length to match the video duration if needed
    video_duration = sum(display_durations)
    audio_file_adjusted = adjust_audio_length(audio_file, video_duration)

    # Calculate fade parameters
    fade_duration = min(5.0, video_duration)  # Fade duration is 5 seconds or video length if shorter
    fade_start_time = max(0.0, video_duration - fade_duration)  # Start fade 5 seconds before the end

    # Combine the concatenated video with the audio, applying fade out effect
    output_file_temp = output_file + "_temp.mp4"  # Temporary output file

    subprocess.run([
        'ffmpeg', '-y',
        '-i', concatenated_video_path,
        '-i', audio_file_adjusted,
        '-filter_complex',
        f"[0:v]fade=t=out:st={fade_start_time}:d={fade_duration},format=yuv420p[v];"
        f"[1:a]afade=t=out:st={fade_start_time}:d={fade_duration}[a]",
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'veryfast',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        output_file_temp
    ], check=True)

    # Replace the original output file with the faded one
    shutil.move(output_file_temp, output_file)

    # Clean up temporary files
    for temp_file in temp_jpeg_images + temp_video_paths:
        os.remove(temp_file)
    os.remove(videos_list_path)
    os.remove(concatenated_video_path)

def get_length(filename):
    """Get the length of an audio file using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return float(result.stdout.strip())

def adjust_audio_length(audio_path, target_length):
    """Adjusts the audio file to match the target length by trimming or looping."""
    current_length = get_length(audio_path)

    if current_length > target_length:
        # Trim the audio
        trimmed_audio_path = f"{os.path.splitext(audio_path)[0]}_trimmed.mp3"
        subprocess.run([
            'ffmpeg', '-y', '-i', audio_path, '-t', str(target_length), '-c', 'copy', trimmed_audio_path
        ], check=True)
        return trimmed_audio_path
    elif current_length < target_length:
        # Loop the audio
        loop_count = int(target_length // current_length) + 1
        looped_audio_path = f"{os.path.splitext(audio_path)[0]}_looped.mp3"
        subprocess.run([
            'ffmpeg', '-y', '-stream_loop', str(loop_count), '-i', audio_path, '-t', str(target_length),
            '-c', 'copy', looped_audio_path
        ], check=True)
        return looped_audio_path
    else:
        # Audio length matches target length
        return audio_path

def unique_filepath(filepath):
    if not os.path.exists(filepath):
        return filepath
    base, ext = os.path.splitext(filepath)
    return f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"

def get_latest_storyline_file(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('_manual_storyline.json')]
    if not json_files:
        return None
    json_files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
    latest_file = json_files[0]
    return os.path.join(directory, latest_file)

def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON file {file_path}: {e}")
        return None

def write_json(data, file_path):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"[INFO] JSON file {file_path} updated successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to write to JSON file {file_path}: {e}")

def find_initial_images(data):
    initial_images = []
    model_name = 'manual'
    image_key_prefix = f'chapter_image_location_{model_name}'

    for chapter in data.get("story_chapters", []):
        image_path = chapter.get(image_key_prefix)
        if image_path and os.path.isfile(image_path):
            initial_images.append(image_path)
    return initial_images

def apply_fade_out(audio_path, fade_duration):
    """Applies a fade-out effect to the audio file over the specified duration."""
    total_duration = get_length(audio_path)
    start_time = total_duration - fade_duration
    if start_time < 0:
        start_time = 0  # Ensure start time is not negative
    faded_audio_path = f"{os.path.splitext(audio_path)[0]}_faded.mp3"
    subprocess.run([
        'ffmpeg', '-y', '-i', audio_path,
        '-af', f"afade=t=out:st={start_time}:d={fade_duration}",
        '-c:a', 'aac', '-b:a', '192k',
        faded_audio_path
    ], check=True)
    return faded_audio_path

def generate_video_filename(audio_file, group_time_str, final_video_length):
    audio_base = sanitize_filename_component(os.path.splitext(os.path.basename(audio_file))[0])
    return f"{group_time_str}_video_{audio_base}_{int(final_video_length)}s.mp4"

def sanitize_filename_component(component, length=20):
    """Sanitize a filename component to be safe and limit its length."""
    sanitized = re.sub(r'[^\w\-_.]', '_', component.strip().lower())
    sanitized = re.sub(r'__+', '_', sanitized)  # Remove multiple underscores
    return sanitized[:length]

def main():
    # Define directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    videos_folder = os.path.join(script_dir, 'created_videos')
    temp_image_folder = os.path.join(script_dir, 'temp_images_on_create_video')
    storylines_folder = os.path.join(script_dir, 'storylines')

    # Ensure necessary directories exist
    ensure_directory_exists(videos_folder)
    ensure_directory_exists(temp_image_folder)

    # Get the latest storyline JSON file
    json_file_path = get_latest_storyline_file(storylines_folder)
    if not json_file_path:
        print("[ERROR] No storyline JSON file found.")
        return

    data = read_json(json_file_path)
    if data is None:
        return

    # Find images
    image_files = find_initial_images(data)
    if not image_files:
        print("[INFO] No images found.")
        return

    # Randomize or sort images based on the setting
    if randomize_images:
        random.shuffle(image_files)
        print("[INFO] Images have been randomized.")
    else:
        image_files.sort()
        print("[INFO] Images have been sorted alphabetically.")

    num_images = len(image_files)
    if num_images == 0:
        print("[ERROR] No images to process.")
        return

    # Set duration per image
    display_duration = 5  # Seconds per image
    display_durations = [display_duration] * num_images

    final_video_length = sum(display_durations)

    # Determine the audio file to use
    if SONG_TO_USE:
        if os.path.isfile(SONG_TO_USE):
            audio_file = os.path.abspath(SONG_TO_USE)
            print(f"Using user-provided song: {audio_file}")

            # Optionally adjust the audio length
            audio_file = adjust_audio_length(audio_file, final_video_length)
        else:
            print(f"[ERROR] The specified SONG_TO_USE does not exist: {SONG_TO_USE}")
            return  # Exit the script
    else:
        print(f"[ERROR] SONG_TO_USE is not specified in GLOBAL_VARIABLES.py")
        return  # Exit the script

    group_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_video = os.path.join(videos_folder, generate_video_filename(audio_file, group_time_str, final_video_length))

    print(f"Creating video with {num_images} images, total video length: {final_video_length:.2f} seconds")

    generate_video_from_images(image_files, audio_file, output_video, display_durations, temp_image_folder)
    print(f"Video created successfully at '{output_video}'.")

    # Update JSON with the created video path
    data['created_video_location_manual'] = output_video
    write_json(data, json_file_path)

    # Clean up temporary directories
    if os.path.exists(temp_image_folder):
        shutil.rmtree(temp_image_folder)

if __name__ == "__main__":
    main()