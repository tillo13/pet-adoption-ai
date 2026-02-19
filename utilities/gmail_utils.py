import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google.cloud import secretmanager
from os import environ, path
from dotenv import load_dotenv
import logging

# Define the project ID and the secret IDs for username and app password
PROJECT_ID = 'your-gcp-project-id'
GMAIL_USERNAME_SECRET_ID = 'YOUR_GMAIL_USERNAME_SECRET'
GMAIL_APP_PASSWORD_SECRET_ID = 'YOUR_GMAIL_APP_PASSWORD_SECRET'

def load_env_file():
    base_dir = path.abspath(path.join(path.dirname(__file__), '..'))
    dotenv_path = path.join(base_dir, '.env')
    if path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        return True
    return False

def get_secret_version(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')

def get_gmail_credentials():
    try:
        if load_env_file():
            return {
                'user': environ.get('GMAIL_USER'),
                'password': environ.get('GMAIL_APP_PASSWORD')
            }
        else:
            raise Exception('.env file not found or not loaded')
    except Exception as env_error:
        logging.warning(f"Failed to load Gmail credentials from .env file: {env_error}")
        logging.info("Attempting to load credentials from Google Cloud Secret Manager")
        return {
            'user': get_secret_version(PROJECT_ID, GMAIL_USERNAME_SECRET_ID),
            'password': get_secret_version(PROJECT_ID, GMAIL_APP_PASSWORD_SECRET_ID),
        }

gmail_credentials = get_gmail_credentials()
GMAIL_USER = gmail_credentials['user']
GMAIL_PASSWORD = gmail_credentials['password']

def send_email(subject, body, to_emails, attachment_paths=None, is_html=False):
    message = MIMEMultipart()
    message['From'] = 'Pet Adoption AI <{}>'.format(GMAIL_USER)
    message['To'] = ', '.join(to_emails)
    message['Subject'] = subject

    if is_html:
        message.attach(MIMEText(body, 'html'))
    else:
        message.attach(MIMEText(body, 'plain'))
    
    if attachment_paths:
        for attachment_path in attachment_paths:
            part = MIMEBase('application', 'octet-stream')
            with open(attachment_path, 'rb') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                'attachment',
                filename=path.basename(attachment_path)
            )
            message.attach(part)
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.set_debuglevel(1)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(message)
        print('Email sent successfully')

# Sample usage (disabled in the main script for safety and reuse)
if __name__ == '__main__':
    # Sample usage for quick testing, but should not run real email sends in the main script
    pass