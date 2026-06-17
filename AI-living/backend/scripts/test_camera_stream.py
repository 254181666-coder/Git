#!/usr/bin/env python3
"""Camera capture + green screen + RTMP streaming test"""
import subprocess
import numpy as np
import cv2
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from services.camera import CameraCapture


# Configuration
CAMERA_ID = 0
USE_GREEN_SCREEN = False
BG_IMAGE_PATH = "data/test_background.png"
RTMP_URL = "rtmp://localhost/live/test"
WIDTH, HEIGHT = 1080, 1920
FPS = 25


def main():
    print("=== Camera Capture + RTMP Streaming Test ===")
    print(f"Camera: {CAMERA_ID}")
    print(f"Green Screen: {USE_GREEN_SCREEN}")
    print(f"Resolution: {WIDTH}x{HEIGHT}")
    print(f"FPS: {FPS}")
    print(f"RTMP: {RTMP_URL}")
    
    # Start camera
    camera = CameraCapture(
        camera_id=CAMERA_ID,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        use_green_screen=USE_GREEN_SCREEN
    )
    
    if not camera.start():
        print("Failed to start camera!")
        sys.exit(1)
    
    print("\nWaiting for camera to initialize...")
    time.sleep(1)
    
    if camera.get_frame() is None:
        print("Error: No frames from camera")
        camera.stop()
        sys.exit(1)
    
    print("Camera ready!")
    
    # Start FFmpeg
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-b:v", "3000k",
        "-pix_fmt", "yuv420p",
        "-g", "25",
        "-keyint_min", "25",
        "-sc_threshold", "0",
        "-f", "flv",
        RTMP_URL
    ]
    
    print("\nStarting FFmpeg...")
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    
    # Load background (for green screen mode)
    bg = None
    if USE_GREEN_SCREEN and os.path.exists(BG_IMAGE_PATH):
        bg = cv2.imread(BG_IMAGE_PATH)
        if bg is not None:
            bg = cv2.resize(bg, (WIDTH, HEIGHT))
            print(f"Background loaded: {BG_IMAGE_PATH}")
    
    # Create overlays
    overlay1 = np.zeros((200, 300, 3), dtype=np.uint8)
    overlay1[:, :] = [52, 211, 153]
    cv2.putText(overlay1, "SNACK 1", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(overlay1, "$9.9", (90, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    
    overlay2 = np.zeros((200, 300, 3), dtype=np.uint8)
    overlay2[:, :] = [251, 191, 36]
    cv2.putText(overlay2, "SNACK 2", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(overlay2, "$19.9", (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    
    scroll_text = "LIMITED OFFER - FOLLOW FOR MORE DEALS!"
    scroll_x = WIDTH
    frame_count = 0
    frame_interval = 1.0 / FPS
    last_time = time.time()
    
    print("\nStreaming... Press Ctrl+C to stop")
    
    try:
        while True:
            # Get frame from camera
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # If green screen mode, composite with background
            if USE_GREEN_SCREEN and bg is not None:
                # Frame has green background removed (black areas)
                mask = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mask = (mask > 10).astype(np.uint8) * 255
                mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                
                # Blend
                alpha = mask / 255.0
                result = bg.copy().astype(float)
                for c in range(3):
                    result[:, :, c] = (
                        bg[:, :, c] * (1 - alpha[:, :, c]) +
                        frame[:, :, c] * alpha[:, :, c]
                    )
                frame = result.astype(np.uint8)
            
            # Add overlays
            y1, y2 = 250, 250 + overlay1.shape[0]
            x1, x2 = 50, 50 + overlay1.shape[1]
            frame[y1:y2, x1:x2] = overlay1
            
            y1, y2 = 250, 250 + overlay2.shape[0]
            x1, x2 = WIDTH - 350, WIDTH - 50
            frame[y1:y2, x1:x2] = overlay2
            
            # Scrolling text
            scroll_x -= 5
            if scroll_x < -len(scroll_text) * 30:
                scroll_x = WIDTH
            cv2.putText(
                frame, scroll_text, (scroll_x, HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2
            )
            
            # LIVE indicator
            cv2.putText(frame, "LIVE", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)
            
            # Convert BGR to RGB for FFmpeg
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Ensure contiguous
            frame = np.ascontiguousarray(frame)
            
            # Write to FFmpeg
            try:
                process.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("RTMP connection lost!")
                break
            
            frame_count += 1
            
            # Control frame rate
            elapsed = time.time() - last_time
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            last_time = time.time()
            
            if frame_count % 100 == 0:
                print(f"Frames: {frame_count}")
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        process.stdin.close()
        process.wait()
        camera.stop()
        print(f"Done. Total frames: {frame_count}")


if __name__ == "__main__":
    main()
