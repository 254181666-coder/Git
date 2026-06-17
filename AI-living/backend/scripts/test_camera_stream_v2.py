#!/usr/bin/env python3
"""Enhanced camera + RTMP streaming with advanced features"""
import subprocess
import numpy as np
import cv2
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from services.camera_v2 import EnhancedCameraCapture, CameraConfig
from services.streaming_v2 import EnhancedStreamingService, StreamConfig, StreamStats


# Configuration
CAMERA_ID = 0
USE_GREEN_SCREEN = False
BG_IMAGE_PATH = "data/test_background.png"
RTMP_URL = "rtmp://localhost/live/test"
WIDTH, HEIGHT = 1080, 1920
FPS = 25


def main():
    print("=== Enhanced Camera + RTMP Streaming ===")
    print(f"Camera: {CAMERA_ID}")
    print(f"Green Screen: {USE_GREEN_SCREEN}")
    print(f"Resolution: {WIDTH}x{HEIGHT}")
    print(f"FPS: {FPS}")
    print(f"RTMP: {RTMP_URL}")
    
    # Start camera with enhanced config
    cam_config = CameraConfig(
        camera_id=CAMERA_ID,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        use_green_screen=USE_GREEN_SCREEN,
        # Green screen optimization (学习相芯科技)
        green_lower_h=35,
        green_upper_h=77,
        edge_feather=3,
        spill_suppression=True
    )
    
    camera = EnhancedCameraCapture(cam_config)
    
    if not camera.start():
        print("Failed to start camera!")
        sys.exit(1)
    
    print("\nWaiting for camera to initialize...")
    time.sleep(2)
    
    if camera.get_frame() is None:
        print("Error: No frames from camera")
        camera.stop()
        sys.exit(1)
    
    print("Camera ready!")
    
    # Start streaming service (学习硅基智能稳定性设计)
    stream_config = StreamConfig(
        rtmp_url=RTMP_URL,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        bitrate=3000,
        preset="ultrafast",
        keyint=25
    )
    
    streaming = EnhancedStreamingService()
    
    if not streaming.start(stream_config):
        print("Failed to start streaming!")
        camera.stop()
        sys.exit(1)
    
    print("\nStreaming started!")
    
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
    print("Stats will be printed every 100 frames")
    
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
            
            # Write to streaming service
            success = streaming.write_frame(frame.tobytes())
            if not success:
                print("Warning: Failed to write frame")
            
            frame_count += 1
            
            # Control frame rate
            elapsed = time.time() - last_time
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            last_time = time.time()
            
            # Print stats every 100 frames (学习播助手的数据展示)
            if frame_count % 100 == 0:
                stats = streaming.get_stats()
                print(f"\n=== Stream Stats ===")
                print(f"Frames: {stats['total_frames']}")
                print(f"Dropped: {stats['dropped_frames']} ({stats['drop_rate']:.1f}%)")
                print(f"FPS: {stats.get('actual_fps', 0):.1f}")
                print(f"Reconnects: {stats['reconnect_count']}")
                print(f"Uptime: {stats['uptime']:.0f}s")
                print(f"====================\n")
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        streaming.stop()
        camera.stop()
        stats = streaming.get_stats()
        print(f"\nFinal Stats:")
        print(f"Total frames: {stats['total_frames']}")
        print(f"Dropped frames: {stats['dropped_frames']}")
        print(f"Drop rate: {stats['drop_rate']:.2f}%")
        print(f"Reconnects: {stats['reconnect_count']}")
        print(f"Uptime: {stats['uptime']:.0f}s")


if __name__ == "__main__":
    main()
