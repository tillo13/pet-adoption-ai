import os
import json
import logging
import subprocess
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_from_directory
from flask_socketio import SocketIO
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid
from utilities.fileio_utils import upload_file_to_fileio
from utilities.file_zip_utils import zip_files

FLASK_PORT = 5001

def kill_process_using_port(port):
    try:
        if os.name == 'posix':
            command = f"lsof -t -i:{port}"
            try:
                pids = subprocess.check_output(command, shell=True).decode().strip().split()
                for pid in pids:
                    os.kill(int(pid), 9)
                    print(f"Killed process {pid} using port {port}")
            except subprocess.CalledProcessError:
                print(f"No process running on port {port}")
        elif os.name == 'nt':
            command = f"netstat -ano | findstr :{port}"
            try:
                output = subprocess.check_output(command, shell=True).decode()
                if output:
                    for line in output.splitlines():
                        if f":{port}" in line:
                            pid = int(line.split()[-1])
                            subprocess.run(f"taskkill /PID {pid} /F", shell=True)
                            print(f"Killed process {pid} using port {port}")
            except subprocess.CalledProcessError:
                print(f"No process running on port {port}")
        else:
            print("Unsupported OS")
    except Exception as e:
        print(f"An error occurred: {e}")

kill_process_using_port(FLASK_PORT)

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app)

base_output_dir = 'pet_directory'
uploads_dir = 'uploads'

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def run_scripts(json_file):
    try:
        env = os.environ.copy()
        env['APP_CONTEXT'] = 'true'
        
        cmd = ["python3", "0_run_all.py", json_file]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env)

        socketio.emit('progress_update', {'message': 'Script execution started...'})

        for line in iter(process.stdout.readline, ''):
            if line:
                cleaned_line = line.strip()
                socketio.emit('progress_update', {'message': cleaned_line})
                print(cleaned_line)

        process.stdout.close()
        process.wait()

        for line in iter(process.stderr.readline, ''):
            if line:
                cleaned_line = line.strip()
                socketio.emit('progress_update', {'message': cleaned_line})
                print(cleaned_line)

        process.stderr.close()

        socketio.emit('progress_update', {'message': '#### GENERATION COMPLETED! ####'})
        print("#### GENERATION COMPLETED! ####")
    except Exception as e:
        socketio.emit('progress_update', {'message': f"An error occurred: {str(e)}"})
        print(f"An error occurred: {str(e)}")

@app.route('/')
def index():
    return redirect(url_for('view_pets'))

@app.route('/create_lora', methods=['GET', 'POST'])
def create_lora():
    if request.method == 'POST':
        try:
            pet_description = request.form.get('pet_description')
            logging.debug('Pet Description: %s', pet_description)

            if not pet_description:
                logging.error('Pet description is missing.')
                return jsonify({'message': 'Pet description is required!'}), 400

            zip_uploads_dir = 'zip_uploads'
            os.makedirs(zip_uploads_dir, exist_ok=True)
            logging.debug('Ensured zip_uploads directory exists: %s', zip_uploads_dir)

            uploaded_files = request.files.getlist('file_input')
            logging.debug('Uploaded files: %s', uploaded_files)

            if not uploaded_files:
                logging.error('No files uploaded.')
                return jsonify({'message': 'No files uploaded!'}), 400

            for file in uploaded_files:
                if file.filename == '':
                    logging.warning('Empty filename detected, skipping file.')
                    continue
                filename = secure_filename(file.filename)
                file_path = os.path.join(zip_uploads_dir, filename)
                logging.debug('Saving file to: %s', file_path)
                file.save(file_path)

            # Prepare data for further processing, such as running scripts
            json_data = {
                "PET_DESCRIPTION": pet_description,
                "submit_time": int(datetime.now().timestamp())
            }

            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            json_filename = f"create_lora_data_{timestamp}.json"
            log_dir = os.path.join('app_submit_log')
            os.makedirs(log_dir, exist_ok=True)
            log_filepath = os.path.join(log_dir, json_filename)
            with open(log_filepath, 'w') as log_file:
                json.dump(json_data, log_file, indent=2)

            # Start the background task to run the scripts
            socketio.start_background_task(run_scripts, json_filename)

            date_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = f"Pet info and images accepted! Generation process started as of {date_time_str}!"

            return jsonify({'message': message}), 200

        except Exception as e:
            logging.error("Error in create_lora", exc_info=True)
            return jsonify({'message': 'An error occurred. Please try again.'}), 500

    return render_template('create_lora.html')

@app.route('/view_pets', methods=['GET'])
def view_pets():
    directories = [d for d in os.listdir(base_output_dir) if os.path.isdir(os.path.join(base_output_dir, d))]
    directories = sorted(directories, key=lambda d: os.path.getmtime(os.path.join(base_output_dir, d)), reverse=True)
    
    selected_directory = request.args.get('selected_directory')
    
    if not selected_directory and directories:
        selected_directory = directories[0]
    
    if selected_directory:
        try:
            json_data = None
            ai_image_files = []
            real_image_files = []

            for file in os.listdir(os.path.join(base_output_dir, selected_directory)):
                if file.endswith('.json'):
                    with open(os.path.join(base_output_dir, selected_directory, file)) as f:
                        json_data = json.load(f)
                    break

            ai_image_dir = os.path.join(base_output_dir, selected_directory, 'ai_images')
            if os.path.exists(ai_image_dir):
                ai_image_files = [file for file in os.listdir(ai_image_dir) if os.path.isfile(os.path.join(ai_image_dir, file))]

            real_image_dir = os.path.join(base_output_dir, selected_directory, 'real_images')
            if os.path.exists(real_image_dir):
                real_image_files = [file for file in os.listdir(real_image_dir) if os.path.isfile(os.path.join(real_image_dir, file))]

            return render_template('view_pets.html', json_data=json_data, ai_image_files=ai_image_files, real_image_files=real_image_files, directory=selected_directory, directories=directories)
        except Exception as e:
            return str(e), 500 
        
    return render_template('view_pets.html', directories=directories, selected_directory=selected_directory)

@app.route('/create_images', methods=['GET', 'POST'])
def create_images():
    if request.method == 'POST':
        pet_directory = request.form['pet_directory']
        prompt = request.form['prompt']
        num_outputs = request.form.get('num_outputs', 1, type=int)
        aspect_ratio = request.form.get('aspect_ratio', '1:1')
        output_format = request.form.get('output_format', 'webp')
        guidance_scale = request.form.get('guidance_scale', 3.5, type=float)
        output_quality = request.form.get('output_quality', 90, type=int)
        prompt_strength = request.form.get('prompt_strength', 0.8, type=float)
        extra_lora_name = request.form.get('extra_lora', '')
        extra_lora_scale = request.form.get('extra_lora_scale', 1, type=float)

        lora_urls = {
            "Handpainted miniature": "civitai.com/models/685433/handpainted-miniature",
            "Phlux": "https://civitai.com/api/download/models/753339?type=Model&format=SafeTensor",
            "Lego": "https://civitai.com/api/download/models/753339?type=Model&format=SafeTensor",
            "Pixar": "https://civitai.com/api/download/models/758632?type=Model&format=SafeTensor",
            "Ghibli": "https://huggingface.co/alvarobartt/ghibli-characters-flux-lora"
        }

        extra_lora_url = lora_urls.get(extra_lora_name, '')

        if not pet_directory or not prompt:
            return jsonify({'message': 'Pet directory and prompt are required!'}), 400

        try:
            cmd = [
                "python3", "4_create_additional_images.py",
                "--pet_directory", pet_directory,
                "--prompt", prompt,
                "--num_outputs", str(num_outputs),
                "--aspect_ratio", aspect_ratio,
                "--output_format", output_format,
                "--guidance_scale", str(guidance_scale),
                "--output_quality", str(output_quality),
                "--prompt_strength", str(prompt_strength),
                "--extra_lora", extra_lora_url,
                "--extra_lora_scale", str(extra_lora_scale)
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            image_urls = []

            for line in iter(process.stdout.readline, ''):
                if line:
                    cleaned_line = line.strip()
                    socketio.emit('progress_update', {'message': cleaned_line})
                    print(cleaned_line)
                    
                    # Extract image URLs from the script output.
                    if "Downloading image from URL" in cleaned_line:
                        url_start = cleaned_line.find("http")
                        url = cleaned_line[url_start:]
                        image_urls.append(url)

            process.stdout.close()
            process.wait()

            for line in iter(process.stderr.readline, ''):
                if line:
                    cleaned_line = line.strip()
                    socketio.emit('progress_update', {'message': cleaned_line})
                    print(cleaned_line)

            process.stderr.close()

            socketio.emit('progress_update', {'message': '#### IMAGE CREATION COMPLETED! ####'})
            print("#### IMAGE CREATION COMPLETED! ####")

        except Exception as e:
            socketio.emit('progress_update', {'message': f"An error occurred: {str(e)}"})
            print(f"An error occurred: {str(e)}")

        message = "Image creation process started! Check the console for updates."
        
        return jsonify({'message': message, 'image_urls': image_urls}), 200

    directories = [d for d in os.listdir(base_output_dir) if os.path.isdir(os.path.join(base_output_dir, d))]
    return render_template('create_images.html', directories=directories)

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    return send_from_directory('uploads', filename)

@app.route('/pet_images/<directory>/<filename>')
def serve_image(directory, filename):
    return send_from_directory(os.path.join(base_output_dir, directory, 'ai_images'), filename)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=FLASK_PORT)