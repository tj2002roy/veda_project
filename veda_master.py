import cv2
import numpy as np
import threading
import sys
import os
import time
from datetime import datetime
from vapi_python import Vapi

# Suppress ALSA logging, force hardware resampling, and use X11
os.environ["ORT_LOGGING_LEVEL"] = "3"
os.environ["PA_ALSA_PLUGHW"] = "1" 
os.environ["QT_QPA_PLATFORM"] = "xcb"

# --- GLOBAL STATE & ASSETS ---
ai_state = "LISTENING"
system_mode = "AI_MODE"  # Modes: AI_MODE, COUNTDOWN, REVIEW
VIDEO_PATHS = {
    "LISTENING": "xyz.mp4",
    "THINKING": "xyz.mp4",
    "SPEAKING": "xyz.mp4"
}
TEMPLATE_PATH = "template.png"
WINDOW_NAME = "Veda"

# Screen configurations (Landscape visual environment)
SCREEN_W, SCREEN_H = 800, 480

# Template dimensions (Portrait output)
TEMPLATE_W, TEMPLATE_H = 480, 800

# SHIFTED BOUNDING BOX (Edge-to-Edge)
CROP_X1, CROP_Y1 = 8, 190
CROP_X2, CROP_Y2 = 472, 575
BOX_W = CROP_X2 - CROP_X1
BOX_H = CROP_Y2 - CROP_Y1

# Photobooth Logic variables
countdown_start = 0
final_composite = None
action_print = False
action_cancel = False

# ==========================================
# PART 1: THE VOICE ENGINE
# ==========================================
def handle_vapi_messages(message):
    global ai_state
    try:
        if message.get("type") == "speech-update":
            role = message.get("role")
            status = message.get("status")
            
            if role == "user" and status == "stopped":
                ai_state = "THINKING"
            elif role == "assistant" and status == "started":
                ai_state = "SPEAKING"
            elif role == "assistant" and status == "stopped":
                ai_state = "LISTENING"
    except Exception as e:
        pass

def run_veda_voice():
    vapi = Vapi(api_key="REPLACE THIS WITH THE ACTUAL API KEY") 
    vapi.on_message = handle_vapi_messages
    try:
        vapi.start(assistant_id="REPLACE THIS WITH THE ACTUAL Assistant id")
    except Exception as e:
        pass

voice_thread = threading.Thread(target=run_veda_voice, daemon=True)
voice_thread.start()

# ==========================================
# PART 2: THE HANGING FRAME COMPOSITOR
# ==========================================
if os.path.exists(TEMPLATE_PATH):
    photo_template = cv2.imread(TEMPLATE_PATH)
    photo_template = cv2.resize(photo_template, (TEMPLATE_W, TEMPLATE_H))
else:
    print(f"Error: {TEMPLATE_PATH} missing. Please add it to folder.")
    sys.exit()

def generate_photobooth_frame(webcam_frame):
    """Crops the webcam feed and overlays it directly onto the template canvas."""
    cam_h, cam_w, _ = webcam_frame.shape
    target_ratio = BOX_W / BOX_H
    current_ratio = cam_w / cam_h
    
    if current_ratio > target_ratio:
        new_w = int(cam_h * target_ratio)
        start_x = (cam_w - new_w) // 2
        cropped = webcam_frame[:, start_x:start_x+new_w]
    else:
        new_h = int(cam_w / target_ratio)
        start_y = (cam_h - new_h) // 2
        cropped = webcam_frame[start_y:start_y+new_h, :]
        
    resized_photo = cv2.resize(cropped, (BOX_W, BOX_H))
    canvas = photo_template.copy()
    canvas[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2] = resized_photo
        
    return canvas

def mouse_callback(event, x, y, flags, param):
    """Maps display click zones back into real coordinate variables."""
    global action_print, action_cancel, system_mode
    if event == cv2.EVENT_LBUTTONDOWN and system_mode == "REVIEW":
        render_w = int(SCREEN_H * (TEMPLATE_W / TEMPLATE_H)) 
        offset_x = (SCREEN_W - render_w) // 2
        
        # Check if user clicked the Green Print box
        if offset_x + 10 <= x <= offset_x + 130 and 420 <= y <= 465:
            action_print = True
        # Check if user clicked the Red Cancel box
        elif offset_x + 160 <= x <= offset_x + 280 and 420 <= y <= 465:
            action_cancel = True

# Initialize graphics window context
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.resizeWindow(WINDOW_NAME, SCREEN_W, SCREEN_H)
cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

cap = cv2.VideoCapture(VIDEO_PATHS[ai_state])
current_state = ai_state

while True:
    key = cv2.waitKey(16) & 0xFF
    
    # --- 1. CORE VOICE ASSISTANT INTERFACE ---
    if system_mode == "AI_MODE":
        if ai_state != current_state:
            current_state = ai_state
            cap.release()
            cap = cv2.VideoCapture(VIDEO_PATHS[current_state])

        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret: continue

        final_output = cv2.resize(frame, (SCREEN_W, SCREEN_H))
        cv2.imshow(WINDOW_NAME, final_output)

        if key == ord('p'):
            system_mode = "COUNTDOWN"
            countdown_start = time.time()
            cap.release()
            cap = cv2.VideoCapture(0) # Open USB camera

    # --- 2. LIVE SHOT COUNTDOWN PROJECTION ---
    elif system_mode == "COUNTDOWN":
        ret, frame = cap.read()
        if ret:
            time_left = 3 - int(time.time() - countdown_start)
            composite = generate_photobooth_frame(frame)
            
            display_frame = composite.copy()
            if time_left > 0:
                cv2.putText(display_frame, str(time_left), (TEMPLATE_W//2 - 30, CROP_Y1 + 230), 
                            cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 255), 8, cv2.LINE_AA)
            
            render_w = int(SCREEN_H * (TEMPLATE_W / TEMPLATE_H))
            resized_display = cv2.resize(display_frame, (render_w, SCREEN_H))
            screen_canvas = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
            offset_x = (SCREEN_W - render_w) // 2
            screen_canvas[:, offset_x:offset_x+render_w] = resized_display
            
            cv2.imshow(WINDOW_NAME, screen_canvas)
            
            if time_left <= 0:
                final_composite = generate_photobooth_frame(frame)
                system_mode = "REVIEW"
                action_print = False
                action_cancel = False
                cap.release()

    # --- 3. REVIEW MODE & PRINTING PIPELINE ---
    elif system_mode == "REVIEW":
        render_w = int(SCREEN_H * (TEMPLATE_W / TEMPLATE_H))
        resized_display = cv2.resize(final_composite, (render_w, SCREEN_H))
        screen_canvas = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
        offset_x = (SCREEN_W - render_w) // 2
        screen_canvas[:, offset_x:offset_x+render_w] = resized_display
        
        # Draw buttons on screen[cite: 1]
        cv2.rectangle(screen_canvas, (offset_x + 10, 420), (offset_x + 130, 465), (0, 200, 0), -1)
        cv2.putText(screen_canvas, "PRINT", (offset_x + 35, 448), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.rectangle(screen_canvas, (offset_x + 160, 420), (offset_x + 280, 465), (0, 0, 200), -1)
        cv2.putText(screen_canvas, "CANCEL", (offset_x + 175, 448), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.imshow(WINDOW_NAME, screen_canvas)
        
        if action_print:
            timestamp = datetime.now().strftime("%d-%b-%Y_%H-%M-%S")
            desktop_dir = os.path.expanduser("~/Desktop")
            jpg_filename = os.path.join(desktop_dir, f"Veda_Booth_{timestamp}.jpg")
            pdf_filename = os.path.join(desktop_dir, f"Veda_Booth_{timestamp}.pdf")
            
            cv2.imwrite(jpg_filename, final_composite)
            print(f"Saved completed picture to desktop: {jpg_filename}")
            
            # Print pipeline[cite: 1]
            os.system(f"img2pdf {jpg_filename} -o {pdf_filename}")
            os.system(f"lp {pdf_filename}")
            
            system_mode = "AI_MODE"
            current_state = ai_state
            action_print = False
            action_cancel = False
            cap = cv2.VideoCapture(VIDEO_PATHS[current_state])
            
        elif action_cancel or key == 27:
            print("Print cancelled by user. Returning to AI Mode.")
            system_mode = "AI_MODE"
            current_state = ai_state
            action_print = False
            action_cancel = False
            cap = cv2.VideoCapture(VIDEO_PATHS[current_state])