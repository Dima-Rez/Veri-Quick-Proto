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
                            QHBoxLayout, QPushButton, QStatusBar, QMessageBox, QScrollArea, QFrame)
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
ERROR_SCANNING = os.path.join(SOUND_DIR,"Scan_error.mp3")


# Fallback to absolute paths if relative paths don't exist
if not os.path.exists(SOUND_DIR):
    SUCCESS_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\document_loaded.mp3"
    AADHAAR_DETECTED_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\Aadhar_detected.mp3"
    PAN_VERIFICATION_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\PAN_DETECTED.mp3"
    MANUAL_VERIFICATION_SOUND = "D:\Python\Main Python Directory\Mega projects\Prototype assets\verfication unsuccessful manual checking neede.mp3"
    ERROR_SCANNING = "D:\Python\Main Python Directory\Mega projects\Prototype assets\Scan_error.mp3"

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
        self.scan_cooldown = 10  # seconds between scans
        self.sound_queue = []  # Queue for sounds to play
        self.is_playing_sound = False
        self.last_result = None  # Store last scan result
        
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
        self.setWindowIcon(QIcon("Yellow and Black Modern Media Logo.ico"))
        self.setMinimumSize(1000, 600)

        # Main horizontal layout
        main_layout = QHBoxLayout()

        # Camera view (left)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(600, 500)
        self.image_label.setStyleSheet("background: #f5f7fa; border-radius: 18px; margin: 20px;")
        main_layout.addWidget(self.image_label, 2)

        # Result area (right, scrollable)
        self.result_area = QScrollArea()
        self.result_area.setWidgetResizable(True)
        self.result_area.setMinimumWidth(400)
        self.result_area.setStyleSheet('''
            QScrollArea { background: #fff; border-radius: 18px; margin: 40px 20px 40px 0; }
        ''')
        self.result_widget = QWidget()
        self.result_layout = QVBoxLayout()
        self.result_layout.setAlignment(Qt.AlignTop)
        self.result_widget.setLayout(self.result_layout)
        self.result_area.setWidget(self.result_widget)
        self.result_area.hide()  # Hide until scan
        main_layout.addWidget(self.result_area, 1)

        # Main vertical layout (for status bar)
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(main_layout)

        # Status bar at the bottom
        self.status_label = QLabel("Ready to scan QR codes")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.status_label.setStyleSheet("background: #e3f2fd; color: #1976d2; padding: 8px; border-radius: 8px; margin: 8px 32px 8px 32px;")
        outer_layout.addWidget(self.status_label)

        # Reset button below status bar
        self.reset_button = QPushButton("Reset for Next Scan")
        self.reset_button.setStyleSheet('''
            QPushButton { background: #43a047; color: #fff; border-radius: 8px; padding: 10px 24px; font-size: 15px; margin-bottom: 16px; }
            QPushButton:hover { background: #388e3c; }
        ''')
        self.reset_button.clicked.connect(self.reset_for_next_scan)
        outer_layout.addWidget(self.reset_button, alignment=Qt.AlignCenter)

        self.setLayout(outer_layout)
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

        current_time = time.time()

        # --- Preprocessing for complex QR codes ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Adaptive thresholding for better binarization
        processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
        # Contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        processed = clahe.apply(processed)
        # Use processed image for decoding
        decoded_objs = pyzbar.decode(processed)
        if decoded_objs:
            # Only process the first detected QR code per frame
            obj = decoded_objs[0]
            data = obj.data.decode('utf-8')
            x, y, w, h = obj.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, "QR Code Detected", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            if (not self.browser_opened and 
                (self.qr_data is None or self.qr_data != data) and
                current_time - self.last_scan_time >= self.scan_cooldown):  # Use the scan_cooldown variable
                self.qr_data = data
                self.last_scan_time = current_time
                self.status_label.setText("Processing QR code...")
                QTimer.singleShot(0, lambda: self.process_qr_code(data))
        else:
            self.qr_data = None

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def process_qr_code(self, qr_data):
        try:
            document_metadata = self.process_qr_data(qr_data)
            if document_metadata:
                self.browser_opened = True
                self.sound_queue = []
                files = document_metadata.get("files", [])
                self.clear_layout(self.result_layout)
                # Show all documents in a scrollable card/list
                aadhaar_found = False
                pan_found = False
                for doc in files:
                    doc_type = doc.get("document_type", "Unknown")
                    doc_url = doc.get("document_url", "")
                    file_name = doc.get("file_name", "Document")
                    
                    # Open the document URL in the web browser immediately
                    if doc_url:
                        try:
                            webbrowser.open(doc_url, new=2)  # new=2 opens in a new tab
                            print(f"Opening URL: {doc_url}")
                        except Exception as e:
                            print(f"Error opening browser: {e}")
                    
                    card = QFrame()
                    card.setStyleSheet('''
                        QFrame { background: #f7f9fa; border-radius: 14px; border: 1px solid #e0e0e0; margin-bottom: 18px; }
                    ''')
                    card_layout = QVBoxLayout()
                    title = QLabel(f"<b>{file_name}</b>")
                    title.setFont(QFont("Arial", 13, QFont.Bold))
                    card_layout.addWidget(title)
                    type_label = QLabel(f"Type: <b>{doc_type}</b>")
                    type_label.setFont(QFont("Arial", 11))
                    card_layout.addWidget(type_label)
                    link_label = QLabel(f'<a href="{doc_url}">{doc_url}</a>')
                    link_label.setFont(QFont("Arial", 10))
                    link_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
                    link_label.setOpenExternalLinks(True)
                    card_layout.addWidget(link_label)
                    open_btn = QPushButton("Open Link")
                    open_btn.setStyleSheet('''
                        QPushButton { background: #1976d2; color: #fff; border-radius: 8px; padding: 6px 16px; font-size: 12px; }
                        QPushButton:hover { background: #1565c0; }
                    ''')
                    open_btn.clicked.connect(lambda checked, url=doc_url: webbrowser.open(url))
                    card_layout.addWidget(open_btn)
                    card.setLayout(card_layout)
                    self.result_layout.addWidget(card)
                    # Sound logic
                    if not aadhaar_found and doc_type == "Aadhaar" and doc.get("aadhaar_numbers", []):
                        aadhaar_found = True
                    if not pan_found and doc_type == "PAN" and doc.get("pan_numbers", []):
                        pan_found = True
                self.result_area.show()
                self.status_label.setText("Scan successful! Ready for next user.")
                # Play only one sound per scan
                if aadhaar_found:
                    self.sound_queue.append(AADHAAR_DETECTED_SOUND)
                elif pan_found:
                    self.sound_queue.append(PAN_VERIFICATION_SOUND)
                else:
                    self.sound_queue.append(MANUAL_VERIFICATION_SOUND)
                self.process_sound_queue()
                QTimer.singleShot(1200, self.reset_for_next_scan)  # Fast reset
            else:
                # Show a user-friendly error card with the raw QR data
                self.clear_layout(self.result_layout)
                error_card = QFrame()
                error_card.setStyleSheet('''
                    QFrame { background: #fff3e0; border-radius: 14px; border: 1px solid #ffb300; margin-bottom: 18px; }
                ''')
                error_layout = QVBoxLayout()
                error_title = QLabel("<b>Unsupported QR Code Format</b>")
                error_title.setFont(QFont("Arial", 13, QFont.Bold))
                error_title.setStyleSheet("color: #e65100;")
                error_layout.addWidget(error_title)
                error_msg = QLabel("This QR code is not supported by Veriquick. Raw data:")
                error_msg.setFont(QFont("Arial", 10))
                error_layout.addWidget(error_msg)
                raw_data_box = QLabel(f"<pre style='font-size:10px; color:#333;'>{qr_data}</pre>")
                raw_data_box.setTextInteractionFlags(Qt.TextSelectableByMouse)
                raw_data_box.setStyleSheet("background: #fff8e1; border-radius: 8px; padding: 8px; margin-top: 6px;")
                error_layout.addWidget(raw_data_box)
                error_card.setLayout(error_layout)
                self.result_layout.addWidget(error_card)
                self.result_area.show()
                self.status_label.setText("Unsupported QR code scanned.")
                self.sound_queue = [ERROR_SCANNING]
                self.process_sound_queue()
                QTimer.singleShot(2000, self.reset_for_next_scan)
        except Exception as e:
            self.status_label.setText(f"Error processing QR code: {str(e)}")
            print(f"Error processing QR code: {e}")
            self.sound_queue = [ERROR_SCANNING]
            self.process_sound_queue()
            QTimer.singleShot(1500, lambda: self.status_label.setText("Ready to scan QR codes"))

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

    def copy_link_to_clipboard(self):
        if self.last_result:
            QApplication.clipboard().setText(self.last_result)
            self.status_label.setText("Link copied to clipboard!")
            QTimer.singleShot(2000, lambda: self.status_label.setText("Ready to scan QR codes"))

    def reset_for_next_scan(self):
        self.qr_data = None
        self.browser_opened = False
        self.result_area.hide()
        self.last_result = None
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
