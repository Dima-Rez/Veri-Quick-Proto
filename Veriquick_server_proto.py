"""
Creating a web Server to make sure the EDV's function 
Process:
1. File upload condition  
2. Data storage and execution with the links 
3. Retrieve the file link in the QR format to make the application redirect 
to the created link 
"""

#import modules 

import streamlit as st
import dropbox
import json
import re
from datetime import datetime
import qrcode
from io import BytesIO
import requests

# Dropbox credentials
ACCESS_TOKEN = st.secrets["dropbox"]["access_token"]
REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
CLIENT_ID = st.secrets["dropbox"]["client_id"]
CLIENT_SECRET = st.secrets["dropbox"]["client_secret"]

#support
mail = "dimareznokov@gmail.com"
ph = '+91 9304211754'

# Initialize Dropbox client
dbx = dropbox.Dropbox(ACCESS_TOKEN)

# Aadhaar and PAN regex patterns
AADHAAR_REGEX = r"\b\d{4} \d{4} \d{4}\b"
PAN_REGEX = r"\b[A-Z]{5}\d{4}[A-Z]{1}\b"

# Function to refresh access token
def refresh_access_token():
    global ACCESS_TOKEN, dbx
    url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        ACCESS_TOKEN = response.json().get("access_token")
        dbx = dropbox.Dropbox(ACCESS_TOKEN)
        return True
    else:
        st.error("We're facing some issues connecting to our servers\
                Please contact the site owner at {mail},{ph}")  
        return False

# Function to upload a file to Dropbox and get a public link
def upload_file_to_dropbox(file, filename):
    global dbx
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    dropbox_path = f"/Veriquick/{timestamp}_{filename}"

    try:
        dbx.files_upload(file.getvalue(), dropbox_path)
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        return shared_link_metadata.url.replace("?dl=0", "?dl=1")

    except dropbox.exceptions.AuthError:
        pass
        if refresh_access_token():
            return upload_file_to_dropbox(file, filename)
        else:
            st.error("Error 101 we are unable to fetch file in our servers.")
            return None
    except dropbox.exceptions.ApiError as e:
        st.error(f" We're facing some isses connecting to Dropbox API error: {e}, Please contact the author at {mail},{ph}")
        return None

# Function to extract Aadhaar and PAN metadata from content
'Highlight: Force Decorate'
def extract_metadata(content, file_url):
    metadata = {"document_url": file_url, "document_type": "Other", "aadhaar_numbers": [], "pan_numbers": []}

    aadhaar_numbers = re.findall(AADHAAR_REGEX, content)
    pan_numbers = re.findall(PAN_REGEX, content)

    if aadhaar_numbers:
        metadata["document_type"] = "Aadhaar"
        metadata["aadhaar_numbers"] = aadhaar_numbers
    elif pan_numbers:
        metadata["document_type"] = "PAN"
        metadata["pan_numbers"] = pan_numbers

    return metadata

# Function to generate QR code from metadata
def generate_qr_code_with_metadata(files_metadata):
    qr_data = json.dumps({"files": files_metadata})
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    return img

# Main Streamlit App
st.title("Veriquick")
st.write("Let's do it quick")

uploaded_files = st.file_uploader("Upload PDF documents", type="pdf", accept_multiple_files=True)

if uploaded_files:
    files_metadata = []
    errors_list = []

    for uploaded_file in uploaded_files:
        file_content = uploaded_file.read().decode("utf-8", errors="ignore")
        file_url = upload_file_to_dropbox(uploaded_file, uploaded_file.name)
        
        if file_url:
            try:
                metadata = extract_metadata(file_content, file_url)
                files_metadata.append(metadata)
            except Exception as e:
                errors_list.append(e)
                st.error(f"Error processing file {uploaded_file.name}: {e}\
                         Please contact the developer at {mail},{ph}")
        
    # Generate and display QR code if files are uploaded
    if files_metadata:
        qr_image = generate_qr_code_with_metadata(files_metadata)
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        st.image(qr_buffer, use_column_width=True)
        st.download_button(label="Download QR ", data=qr_buffer, file_name="document_metadata_qr.png", mime="image/png")
        st.json(files_metadata)  # Display metadata as JSON for reference











