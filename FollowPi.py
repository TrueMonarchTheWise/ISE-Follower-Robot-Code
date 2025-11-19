import cv2
import time
import numpy as np
import serial
import os
import pygame.mixer
import random

# --- Configuration ---

# Camera Settings
CAMERA_INDEX = 0 
# Requested 1080x720 resolution (720p)
FRAME_WIDTH = 1080
FRAME_HEIGHT = 720
FRAME_CENTER_X = FRAME_WIDTH // 2

# Motor Control Settings (MUST match your Arduino sketch commands: F, L, R, S)
SERIAL_PORT = '/dev/ttyUSB0' 
BAUD_RATE = 9600
COMMAND_FORWARD = 'F' 
COMMAND_LEFT = 'L' 
COMMAND_RIGHT = 'R' 
COMMAND_STOP = 'S' 
COMMAND_SEARCH_TURN = 'R' 

# --- AUDIO CONFIGURATION ---
SOUND_FOLDER = "./sounds"  # Make sure this folder exists with your sound files
READY_SOUND_FILE = "tada.mp3"        
TRACKING_SOUND_FILE = "alert.mp3"   # Plays ONCE when moving straight (COMMAND_FORWARD)
SEARCHING_SOUND_FILE = "sonar.mp3" # Plays when turning (L, R, or search turn 'R')
RANDOM_SOUND_FILES = ["yippee.mp3", "shaw.mp3"] 
# --- END AUDIO CONFIGURATION ---

# --- COLOR TRACKING CONFIGURATION (RED) ---
LOWER_RED_1 = np.array([0, 100, 100])
UPPER_RED_1 = np.array([10, 255, 255])
LOWER_RED_2 = np.array([160, 100, 100])
UPPER_RED_2 = np.array([179, 255, 255])

# Tracking Thresholds (will be dynamically calculated)
CENTER_TOLERANCE_ZONE_WIDTH = 0.0
CENTER_ZONE_START = 0.0
CENTER_ZONE_END = 0.0

MIN_CONTOUR_AREA = 1000 
TRACKING_BOX_COLOR = (0, 255, 255)      
TEXT_COLOR = (255, 255, 255)          

# Global sound variable storage
current_tracking_sound = None

# --- Audio Initialization and Control Functions ---
def initialize_audio():
    """Initializes the pygame mixer."""
    try:
        pygame.mixer.init()
        print("Audio mixer initialized successfully.")
    except Exception as e:
        print(f"Warning: Could not initialize audio mixer. Sounds disabled. Reason: {e}")
        return False
    return True

def play_sound(filename):
    """Plays a sound file from the configured folder."""
    if not pygame.mixer.get_init():
        return None
    
    full_path = os.path.join(SOUND_FOLDER, filename)
    if not os.path.exists(full_path):
        print(f"Sound file not found: {full_path}")
        return None

    try:
        sound = pygame.mixer.Sound(full_path)
        # Note: We return the sound object for control in the main loop
        sound.play()
        return sound 
    except Exception as e:
        print(f"Error playing sound {filename}: {e}")
        return None

def initialize_serial(port, baud):
    """Initializes and returns the serial connection object."""
    try:
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        print(f"Serial connection established to {port} at {baud}.")
        return ser
    except serial.SerialException as e:
        print(f"ERROR: Could not open serial port {port}. Motors will be disabled.")
        print(f"Reason: {e}")
        return None

def send_command(ser, command):
    """Sends a motor command over serial if the connection is active."""
    if ser and ser.is_open:
        try:
            ser.write(command.encode('utf-8'))
        except Exception as e:
            print(f"Serial write failed: {e}")

# --- Main Program Loop ---
def run_color_follower():
    # 1. Initialize Hardware
    global current_tracking_sound # Use the global sound variable
    
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE)
    audio_enabled = initialize_audio()
    
    # FIX: Explicitly use V4L2 backend for stability on Raspberry Pi
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2) 
    if not cap.isOpened():
        print(f"Error: Cannot open camera at index {CAMERA_INDEX}. Check connection.")
        if ser: ser.close()
        return

    # Set Resolution and FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 60.0) 
    
    # Get actual settings
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    # DYNAMIC CENTER LINE RECALCULATION (Increased Tolerance)
    global CENTER_TOLERANCE_ZONE_WIDTH, CENTER_ZONE_START, CENTER_ZONE_END
    
    # Divisor 2.5 gives 40% of the screen for straight movement
    CENTER_TOLERANCE_ZONE_WIDTH = actual_width / 2.5 
    CENTER_ZONE_START = (actual_width - CENTER_TOLERANCE_ZONE_WIDTH) // 2 
    CENTER_ZONE_END = CENTER_ZONE_START + CENTER_TOLERANCE_ZONE_WIDTH
    
    # 2. Play Ready Sound (after all critical setup)
    if ser is not None and cap.isOpened() and audio_enabled:
        play_sound(READY_SOUND_FILE)
    
    print("--- Color Follower Ready (Tracking RED) ---")
    print(f"Actual Camera Settings: {actual_width:.0f}x{actual_height:.0f} @ {actual_fps:.2f} FPS.")
    print(f"Target Center Zone: {CENTER_ZONE_START:.0f} to {CENTER_ZONE_END:.0f} pixels.")
    print("Press 'q' or ESC to exit.")
    
    frame_count = 0
    start_time = time.time()
    current_motor_command = COMMAND_STOP 
    
    # Audio State Variables for single-play tracking sound
    last_random_time = time.time()
    next_random_interval = random.uniform(5.0, 15.0)
    tracking_sound_played_this_cycle = False
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # --- A. HSV Color Detection and Tracking ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, LOWER_RED_1, UPPER_RED_1)
        mask2 = cv2.inRange(hsv, LOWER_RED_2, UPPER_RED_2)
        red_mask = mask1 + mask2
        red_mask = cv2.erode(red_mask, None, iterations=2)
        red_mask = cv2.dilate(red_mask, None, iterations=2)
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        target_contour = None
        max_area = 0
        if contours:
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > MIN_CONTOUR_AREA: 
                    if area > max_area:
                        max_area = area
                        target_contour = contour

        
        # --- B. Motor Control Logic ---
        new_motor_command = COMMAND_STOP
        direction_text = "NO ACTION" 

        if target_contour is not None:
            # Target FOUND: Lock on and Follow
            x, y, w, h = cv2.boundingRect(target_contour)
            target_center_x = x + w // 2
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), TRACKING_BOX_COLOR, 2)
            cv2.putText(frame, "TRACKING RED", (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 2)
            
            if target_center_x < CENTER_ZONE_START:
                new_motor_command = COMMAND_LEFT
                direction_text = "TURNING LEFT"
            elif target_center_x > CENTER_ZONE_END:
                new_motor_command = COMMAND_RIGHT
                direction_text = "TURNING RIGHT"
            else:
                new_motor_command = COMMAND_FORWARD
                direction_text = "FORWARD/FOLLOWING"
            
            cv2.circle(frame, (target_center_x, FRAME_HEIGHT // 2), 5, (0, 0, 255), -1)
            
        else:
            # Target LOST: Continuous Search Turn Right
            new_motor_command = COMMAND_SEARCH_TURN
            direction_text = f"SEARCHING (TURNING {COMMAND_SEARCH_TURN})"
        
        # Draw center zone lines
        cv2.line(frame, (int(CENTER_ZONE_START), 0), (int(CENTER_ZONE_START), FRAME_HEIGHT), (255, 255, 0), 1)
        cv2.line(frame, (int(CENTER_ZONE_END), 0), (int(CENTER_ZONE_END), FRAME_HEIGHT), (255, 255, 0), 1)
            
        
        # --- C. Audio Control Logic (FINAL REVISION) ---
        if audio_enabled:
            is_following = (new_motor_command == COMMAND_FORWARD)
            is_turning = (new_motor_command == COMMAND_LEFT or new_motor_command == COMMAND_RIGHT)
            is_searching = (new_motor_command == COMMAND_SEARCH_TURN)

            # 1. Control Tracking/Searching Sounds
            if is_following:
                if not tracking_sound_played_this_cycle:
                    # Play tracking sound ONLY ONCE when entering forward state
                    pygame.mixer.stop()
                    current_tracking_sound = play_sound(TRACKING_SOUND_FILE)
                    tracking_sound_played_this_cycle = True
            
            elif is_turning or is_searching:
                if current_tracking_sound:
                    current_tracking_sound.stop()
                    current_tracking_sound = None
                
                # Reset tracking flag and play searching sound
                tracking_sound_played_this_cycle = False
                
                # Play searching sound if no sound is currently playing 
                if not pygame.mixer.get_busy():
                    play_sound(SEARCHING_SOUND_FILE)
            
            else: # COMMAND_STOP
                if current_tracking_sound:
                    current_tracking_sound.stop()
                    current_tracking_sound = None
                pygame.mixer.stop()
                tracking_sound_played_this_cycle = False


            # 2. Random Sound Check
            if time.time() - last_random_time >= next_random_interval:
                # Only play random sound if NO other sound is currently playing 
                if RANDOM_SOUND_FILES and not pygame.mixer.get_busy():
                    random_file = random.choice(RANDOM_SOUND_FILES)
                    play_sound(random_file)
                
                # Reset timer for the next random sound
                last_random_time = time.time()
                next_random_interval = random.uniform(5.0, 15.0)
        # -------------------------------------------------------------


        # 9. Send motor command ONLY if it has changed
        if new_motor_command != current_motor_command:
            send_command(ser, new_motor_command)
            current_motor_command = new_motor_command
        
        
        # 10. Display Info 
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time > 1:
            fps = frame_count / elapsed_time
            cv2.putText(frame, f"FPS: {fps:.2f}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            frame_count = 0
            start_time = time.time()

        cv2.putText(frame, f"ACTION: {direction_text}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)


        # 11. Display the resulting frame
        cv2.imshow('OpenCV Color Follower - Press Q or ESC to Quit', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

    # 12. Cleanup
    print("Exiting program. Sending STOP command.")
    send_command(ser, COMMAND_STOP) 
    cap.release()
    cv2.destroyAllWindows()
    
    # Ensure tracking sound is stopped on exit
    if current_tracking_sound:
        current_tracking_sound.stop()
    
    if pygame.mixer.get_init():
        pygame.mixer.quit()
        
    if ser:
        ser.close()

if __name__ == "__main__":
    run_color_follower()
