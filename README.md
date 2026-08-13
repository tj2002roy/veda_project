Veda AI Photobooth 📸🤖
An interactive, edge-to-edge AI photobooth and conversational interface built using Python, OpenCV, and Vapi. Veda blends an automated voice assistant loop with a live-action photo capture countdown, allowing users to review their composite photo, print it directly via CUPS/Epson printers, or restart the loop seamlessly.

Features
Voice-Powered State Machine: Synchronizes visual avatar states (LISTENING, THINKING, SPEAKING) with real-time audio streams via the Vapi SDK.

Edge-to-Edge Compositing: Dynamically crops and aligns webcam frames to fit precise overlay boxes on custom poster templates without visual distortion.

Interactive Live Countdown: Features an on-screen 3-second visual countdown timer right before capturing the snapshot.

Review & Print Pipeline: Automatically presents the final composite image on a touchscreen-friendly review canvas complete with interactive PRINT and CANCEL touch zones.

Automated PDF Conversion & Printing: Instantly converts saved JPEGs into printable formats via img2pdf and routes them straight to local or network printers (lp).

Project Structure
Plaintext
veda_project/
│
├── veda_master.py       # Main application script
├── .gitignore           # Ignores local caches, logs, and temporary images/PDFs
└── README.md            # Project documentation

Prerequisites & Dependencies

1. System Packages (Linux / Raspberry Pi OS)
Ensure you have CUPS, Ghostscript, and image utilities installed for hardware printing support:

Bash
sudo apt install img2pdf ghostscript cups -y


2. Python Libraries
Install the required Python packages using pip:

Bash
pip install opencv-python numpy vapi-python

Setup & Configuration
Clone the Repository:

Bash
git clone https://github.com/tj2002roy/veda_project.git
cd veda_project


Add Your Custom Assets:

This repository provides the core control logic (veda_master.py), but does not include visual assets or templates.

You must create and place your own portrait-oriented layout overlay named template.png (recommended resolution: 480x800 pixels) in the root directory.

Add your assistant video files (listening.mp4 and speaking.mp4) to the same folder.

Configure Your Printer:

Ensure your printer (e.g., Epson EcoTank series) is properly added to your local CUPS print server (http://localhost:631) with a compatible driver (such as Epson Generic ESC/P-R).

Run the Application:

Bash
python3 veda_master.py

Usage Guide
AI Mode: Veda runs its idle listening and responding loop on the main display.

Trigger Countdown: Press the p key on your keyboard (or hook up a physical button GPIO trigger) to start the 3-second photo countdown.

Review & Action: Once the photo is captured, the UI shifts to REVIEW mode showing the composite image with on-screen touch buttons:

Click PRINT (Green Zone) to save the file to the Desktop, convert it to a PDF, and send it to the printer.

Click CANCEL (Red Zone) or press ESC to discard the image and return straight to AI mode.