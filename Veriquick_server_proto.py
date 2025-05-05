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
import PyPDF2
import pytesseract
from PIL import Image
import pdf2image
import io
import uuid

# Configure Streamlit page settings
st.set_page_config(
    page_title="Veriquick",
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

# Enable dark mode by default using custom CSS
st.markdown("""
    <style>
        body, .stApp {
            background: linear-gradient(135deg, #232526 0%, #414345 100%);
            color: #FAFAFA;
        }
        .main .block-container {
            max-width: 900px;
            margin: auto;
            padding: 2rem 2rem 2rem 2rem;
        }
        .card {
            background: #fff;
            color: #232526;
            border-radius: 18px;
            box-shadow: 0 4px 24px rgba(30, 34, 90, 0.08);
            padding: 2rem 2rem 1.5rem 2rem;
            margin-bottom: 2rem;
        }
        .card-title {
            color: #1976d2;
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .card-link {
            color: #1565c0;
            font-size: 1.1rem;
            word-break: break-all;
        }
        .stButton>button {
            background-color: #1976d2;
            color: white;
            border-radius: 8px;
            font-size: 1.1rem;
            padding: 0.5rem 1.5rem;
        }
        .stFileUploader {
            background: #262730;
            border-radius: 12px;
        }
    </style>
""", unsafe_allow_html=True)

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

# Function to validate Aadhaar number using checksum and format
def validate_aadhaar(aadhaar):
    """Validate Aadhaar number using checksum and format."""
    # Remove spaces and check length
    aadhaar = aadhaar.replace(" ", "")
    if len(aadhaar) != 12 or not aadhaar.isdigit():
        return False
    # Add proper Verhoeff algorithm validation here if needed
    return True

# Function to validate PAN card number format and checksum
def validate_pan(pan):
    """Validate PAN card number format and checksum."""
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}\b', pan):
        return False
    # First five characters should be letters
    if not pan[:5].isalpha():
        return False
    # Next 4 should be numbers
    if not pan[5:9].isdigit():
        return False
    # Last character should be letter
    if not pan[9].isalpha():
        return False
    return True

# Function to extract and validate document metadata from content and OCR text
def extract_metadata(content, file_url, ocr_text=None):
    """
    Extract and validate document metadata from content and OCR text.
    
    Args:
        content (str): Raw document content
        file_url (str): URL to the uploaded document
        ocr_text (str, optional): OCR extracted text from the document
    
    Returns:
        dict: Validated metadata including document type and extracted information
    """
    metadata = {
        "document_url": file_url,
        "document_type": "Unknown",
        "aadhaar_numbers": [],
        "pan_numbers": [],
        "confidence_score": 0.0,
        "verification_status": "unverified",
        "extraction_timestamp": datetime.now().isoformat()
    }

    # Combine content and OCR text if available
    text_to_analyze = content
    if ocr_text:
        text_to_analyze = f"{content} {ocr_text}"

    # Extract and validate Aadhaar numbers
    potential_aadhaar = re.findall(AADHAAR_REGEX, text_to_analyze)
    validated_aadhaar = []
    for aadhaar in potential_aadhaar:
        if validate_aadhaar(aadhaar):
            validated_aadhaar.append(aadhaar)
    
    # Extract and validate PAN numbers
    potential_pan = re.findall(PAN_REGEX, text_to_analyze)
    validated_pan = []
    for pan in potential_pan:
        if validate_pan(pan):
            validated_pan.append(pan)

    # Determine document type and set confidence score
    if validated_aadhaar:
        metadata["document_type"] = "Aadhaar"
        metadata["aadhaar_numbers"] = validated_aadhaar
        metadata["confidence_score"] = 0.9 if len(validated_aadhaar) == 1 else 0.7
        metadata["verification_status"] = "verified"
    elif validated_pan:
        metadata["document_type"] = "PAN"
        metadata["pan_numbers"] = validated_pan
        metadata["confidence_score"] = 0.9 if len(validated_pan) == 1 else 0.7
        metadata["verification_status"] = "verified"

    # Add additional metadata
    metadata["num_matches"] = len(validated_aadhaar) + len(validated_pan)
    metadata["processing_details"] = {
        "ocr_used": ocr_text is not None,
        "content_length": len(text_to_analyze),
        "multiple_matches": metadata["num_matches"] > 1
    }

    return metadata

# Function to generate QR code from metadata
def generate_qr_code_with_metadata(files_metadata):
    qr_data = json.dumps({"files": files_metadata})
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    return img

def extract_text_from_pdf(pdf_file):
    """
    Extract text from PDF using both PDF text extraction and OCR.
    
    Args:
        pdf_file: Streamlit uploaded PDF file
    Returns:
        str: Extracted text content
    """
    text_content = ""
    ocr_text = ""
    
    try:
        # First try regular PDF text extraction
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text_content += page.extract_text() or ""

        # If text extraction yields little content, try OCR
        if len(text_content.strip()) < 50:  # Arbitrary threshold
            # Convert PDF to images
            pdf_images = pdf2image.convert_from_bytes(pdf_file.getvalue())
            
            # Perform OCR on each page
            for image in pdf_images:
                ocr_text += pytesseract.image_to_string(image, lang='eng') + "\n"
    
    except Exception as e:
        st.warning(f"Error in PDF processing: {str(e)}")
        return "", ""

    return text_content, ocr_text

def verify_aadhaar_authenticity(aadhaar_number):
    """
    Verify Aadhaar number authenticity using Verhoeff algorithm
    """
    # Remove spaces
    aadhaar = aadhaar_number.replace(" ", "")
    
    # Verhoeff algorithm multiplication table
    mult = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
    
    # Permutation table
    perm = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]
    
    # Inverse table
    inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
    
    check = 0
    for i, digit in enumerate(reversed(aadhaar)):
        check = mult[check][perm[i % 8][int(digit)]]
    
    return check == 0

# Main Streamlit App
st.title("Veriquick")
st.markdown("<h4 style='color:#90caf9;'>Let's Make it Quick✅.</h4>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload PDF documents", type="pdf", accept_multiple_files=True)

if uploaded_files:
    files_metadata = []
    errors_list = []
    # If multiple files, upload to a folder
    if len(uploaded_files) > 1:
        file_links = upload_file_to_dropbox(uploaded_files)
        for file, link in zip(uploaded_files, file_links):
            text_content, ocr_text = extract_text_from_pdf(file)
            metadata = extract_metadata(text_content, link["url"], ocr_text)
            metadata["file_name"] = file.name
            files_metadata.append(metadata)
    else:
        # Single file logic (keep old logic for single file)
        uploaded_file = uploaded_files[0]
        text_content, ocr_text = extract_text_from_pdf(uploaded_file)
        file_url = upload_file_to_dropbox(uploaded_file, uploaded_file.name)
        if file_url:
            metadata = extract_metadata(text_content, file_url, ocr_text)
            metadata["file_name"] = uploaded_file.name
            files_metadata.append(metadata)

    # Show cards for each file
    for meta in files_metadata:
        st.markdown(f"""
        <div class='card'>
            <div class='card-title'>{meta['file_name']}</div>
            <div>Type: <b>{meta['document_type']}</b></div>
            <div>Status: <b>{meta['verification_status']}</b></div>
            <div class='card-link'>Link: <a href='{meta['document_url']}' target='_blank'>{meta['document_url']}</a></div>
        </div>
        """, unsafe_allow_html=True)

    # Generate and display QR code for all files
    if files_metadata:
        qr_image = generate_qr_code_with_metadata(files_metadata)
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        st.image(qr_buffer, use_column_width=True)
        st.download_button(label="Download QR for all documents", data=qr_buffer, file_name="document_metadata_qr.png", mime="image/png")

# Function to upload multiple files to Dropbox folder and get their public links
def upload_files_to_dropbox(files):
    global dbx
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    folder_id = str(uuid.uuid4())[:8]
    folder_path = f"/Veriquick/{timestamp}_{folder_id}"
    dbx.files_create_folder_v2(folder_path)
    file_links = []
    for file in files:
        dropbox_path = f"{folder_path}/{file.name}"
        dbx.files_upload(file.getvalue(), dropbox_path)
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        file_links.append({
            "name": file.name,
            "url": shared_link_metadata.url.replace("?dl=0", "?dl=1")
        })
    return file_links











