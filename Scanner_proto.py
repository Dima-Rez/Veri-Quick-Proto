""" Veri-Quick Scanner made to access the qr content and load the content in browser
made by D.Rana 

Acesss: Limited and under copyright 

Github: Dave R 
Repository: Veri-Quick Final Scanner.final.py 

Permission required to edit and modify the code 

Date of update : 10-11-2024

Version : 2.3.0

"""

# Importing necessary modules
import cv2
import pyzbar.pyzbar as pyzbar
import webbrowser
import pygame
import sys
import json
import os
import time
from PyQt5.QtWidgets import (QApplication, QLabel, QVBoxLayout, QWidget, 
                            QHBoxLayout, QPushButton, QStatusBar, QMessageBox)
from PyQt5.QtGui import QImage, QPixmap, QIcon, QFont
from PyQt5.QtCore import QTimer, Qt

# Initialize pygame mixer and preload sounds for faster access
pygame.mixer.init()
# Use relative paths for sound files to make the application more portable
SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SUCCESS_SOUND = os.path.join(SOUND_DIR, "document_loaded.mp3")
AADHAAR_DETECTED_SOUND = os.path.join(SOUND_DIR, "aadhar_detected.mp3")
PAN_VERIFICATION_SOUND = os.path.join(SOUND_DIR, "pan_detected.mp3")
MANUAL_VERIFICATION_SOUND = os.path.join(SOUND_DIR, "verification_unsuccessful.mp3")

# Fallback to absolute paths if relative paths don't exist
if not os.path.exists(SOUND_DIR):
    SUCCESS_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\document_loaded.mp3"
    AADHAAR_DETECTED_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\Aadhar_detected.mp3"
    PAN_VERIFICATION_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\PAN_DETECTED.mp3"
    MANUAL_VERIFICATION_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\verfication unsuccessful manual checking neede.mp3"

class QRScannerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.cap = None
        self.initialize_camera()

        # Set initial flags and timers
        self.qr_data = None
        self.browser_opened = False
        self.last_scan_time = 0
        self.scan_cooldown = 5  # seconds between scans
        self.sound_queue = []  # Queue for sounds to play
        self.is_playing_sound = False
        
        # Main timer for camera updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Frame rate control
        
        # Timer for sound queue processing
        self.sound_timer = QTimer()
        self.sound_timer.timeout.connect(self.process_sound_queue)
        self.sound_timer.start(100)  # Check sound queue every 100ms

    def initUI(self):
        self.setWindowTitle("Veriquick - Document Scanner")
        self.setWindowIcon(QIcon("D:\\Python\\Main Python Directory\\Mega Project Prototype 1\\Prototype assets\\qricon.ico"))
        self.setMinimumSize(800, 600)

        # Main layout
        main_layout = QVBoxLayout()
        
        # Camera view
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.image_label)
        
        # Status display
        self.status_label = QLabel("Ready to scan QR codes")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        main_layout.addWidget(self.status_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset Scanner")
        self.reset_button.clicked.connect(self.reset_for_next_scan)
        button_layout.addWidget(self.reset_button)
        
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        self.show()

    def initialize_camera(self):
        """Initialize the camera with error handling."""
        try:
            # Try DirectShow first for better performance on Windows
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise Exception("Camera could not be initialized with DirectShow.")
                
            # Set camera properties for optimal QR scanning
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus
            
            # Verify camera is working
            ret, _ = self.cap.read()
            if not ret:
                raise Exception("Camera is not returning frames.")
                
            self.status_label.setText("Camera initialized successfully")
            
        except Exception as e:
            self.status_label.setText(f"Camera error: {str(e)}")
            print(f"Camera initialization error: {e}")
            
            # Try fallback to default camera
            try:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise Exception("Unable to access any camera.")
                self.status_label.setText("Camera initialized with fallback settings")
            except Exception as e2:
                self.status_label.setText("Camera error: Unable to access camera")
                QMessageBox.critical(self, "Camera Error", 
                                    "Unable to access the camera. Please check the camera connection or settings.")
                print(f"Fallback camera error: {e2}")

    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            self.status_label.setText("Camera is not available")
            return

        success, frame = self.cap.read()
        if not success:
            self.status_label.setText("Error reading frame from camera")
            return

        # Check if we're in cooldown period
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_cooldown:
            # Show cooldown status
            remaining = round(self.scan_cooldown - (current_time - self.last_scan_time))
            self.status_label.setText(f"Scanning paused. Ready in {remaining} seconds...")
        else:
            self.status_label.setText("Ready to scan QR codes")

        # Decode QR code from frame
        decoded_objs = pyzbar.decode(frame)
        
        # Draw QR detection indicator
        if decoded_objs:
            # Process each detected QR code
            for obj in decoded_objs:
                data = obj.data.decode('utf-8')
                x, y, w, h = obj.rect
                
                # Draw a green rectangle around the QR code
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                
                # Add text label
                cv2.putText(frame, "QR Code Detected", (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Only process if it's a new QR code and not in cooldown
                if (not self.browser_opened and 
                    (self.qr_data is None or self.qr_data != data) and
                    current_time - self.last_scan_time >= self.scan_cooldown):
                    
                    self.qr_data = data
                    self.last_scan_time = current_time
                    self.status_label.setText("Processing QR code...")
                    
                    # Process in a separate thread to keep UI responsive
                    QTimer.singleShot(0, lambda: self.process_qr_code(data))
        else:
            # No QR code detected
            self.qr_data = None

        # Update display with video frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale image to fit the label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def process_qr_code(self, qr_data):
        """Process the QR code data in a separate thread to keep UI responsive."""
        try:
            document_metadata = self.process_qr_data(qr_data)
            
            if document_metadata:
                self.browser_opened = True  # Prevent re-opening on repeat scans
                aadhaar_detected = False
                pan_detected = False
                
                # Queue sounds to play in sequence
                self.sound_queue = []  # Clear any existing sounds
                
                # Add success sound to queue
                self.sound_queue.append(SUCCESS_SOUND)
                
                # Open each document URL in the QR code metadata
                for doc in document_metadata.get("files", []):
                    doc_type = doc.get("document_type", "Unknown")
                    doc_url = doc.get("document_url", "")
                    aadhaar_numbers = doc.get("aadhaar_numbers", [])
                    pan_numbers = doc.get("pan_numbers", [])
                    
                    # Open the document URL in the browser
                    if doc_url:
                        webbrowser.open(doc_url)
                        self.status_label.setText(f"Opening document: {doc_type}")
                    
                    # Queue document-specific sounds
                    if doc_type == "Aadhaar" and aadhaar_numbers and not aadhaar_detected:
                        aadhaar_detected = True
                        self.sound_queue.append(AADHAAR_DETECTED_SOUND)
                    elif doc_type == "PAN" and pan_numbers and not pan_detected:
                        pan_detected = True
                        self.sound_queue.append(PAN_VERIFICATION_SOUND)
                
                # Queue manual verification sound if needed
                if not aadhaar_detected and not pan_detected:
                    self.sound_queue.append(MANUAL_VERIFICATION_SOUND)
                
                # Start playing sounds
                self.process_sound_queue()
                
                # Reset for next scan after cooldown
                QTimer.singleShot(self.scan_cooldown * 1000, self.reset_for_next_scan)
            else:
                self.status_label.setText("Invalid QR code data")
                QTimer.singleShot(3000, lambda: self.status_label.setText("Ready to scan QR codes"))
                
        except Exception as e:
            self.status_label.setText(f"Error processing QR code: {str(e)}")
            print(f"Error processing QR code: {e}")
            QTimer.singleShot(3000, lambda: self.status_label.setText("Ready to scan QR codes"))

    def process_qr_data(self, qr_data):
        """Parse and validate QR code data."""
        try:
            data = json.loads(qr_data)
            
            # Validate the expected structure
            if not isinstance(data, dict) or "files" not in data:
                print("Invalid QR data format: missing 'files' key")
                return None
                
            if not isinstance(data["files"], list) or len(data["files"]) == 0:
                print("Invalid QR data format: 'files' is empty or not a list")
                return None
                
            return data
            
        except json.JSONDecodeError as e:
            print(f"Error decoding QR data: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error processing QR data: {e}")
            return None

    def process_sound_queue(self):
        """Process the sound queue to play sounds sequentially."""
        if self.is_playing_sound:
            # Check if current sound is finished
            if not pygame.mixer.music.get_busy():
                self.is_playing_sound = False
            else:
                return  # Still playing current sound
        
        # Play next sound in queue if available
        if self.sound_queue and not self.is_playing_sound:
            sound_path = self.sound_queue.pop(0)
            self.play_sound(sound_path)

    def play_sound(self, sound_path):
        """Play sound at specified path with error handling."""
        try:
            pygame.mixer.music.stop()  # Stop any previous sound
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
            self.is_playing_sound = True
            print(f"Playing sound: {sound_path}")
        except pygame.error as e:
            print(f"Error playing sound {sound_path}: {e}")
            self.is_playing_sound = False

    def reset_for_next_scan(self):
        """Reset necessary flags to allow for the next scan."""
        self.qr_data = None
        self.browser_opened = False
        self.status_label.setText("Ready to scan QR codes")
        print("Scanner reset, ready for next scan")

    def closeEvent(self, event):
        """Clean up resources when the application is closed."""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        pygame.mixer.quit()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    scanner = QRScannerApp()
    sys.exit(app.exec_())
