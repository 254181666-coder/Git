"""
Windows camera diagnostic script.

Run from project root after activating the virtual environment:
    python backend/scripts/diagnose_camera_windows.py
"""
import cv2
import platform


def backends():
    if platform.system() == "Windows":
        return [
            ("DSHOW", cv2.CAP_DSHOW),
            ("MSMF", cv2.CAP_MSMF),
            ("ANY", cv2.CAP_ANY),
        ]
    if platform.system() == "Darwin":
        return [("AVFOUNDATION", cv2.CAP_AVFOUNDATION), ("ANY", cv2.CAP_ANY)]
    return [("ANY", cv2.CAP_ANY)]


def main():
    print(f"System: {platform.system()} {platform.release()}")
    print(f"OpenCV: {cv2.__version__}")
    print("Testing camera ids 0-5...\n")

    found = False
    for camera_id in range(6):
        for name, backend in backends():
            cap = cv2.VideoCapture(camera_id, backend)
            opened = cap.isOpened()
            ok = False
            shape = None
            width = height = fps = None
            if opened:
                ok, frame = cap.read()
                shape = getattr(frame, "shape", None)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                fps = cap.get(cv2.CAP_PROP_FPS) or 0
            cap.release()

            status = "OK" if opened and ok else "--"
            print(
                f"{status} camera_id={camera_id} backend={name} "
                f"opened={opened} read={ok} shape={shape} "
                f"reported={width}x{height}@{fps:.1f}"
            )
            if opened and ok:
                found = True
        print()

    if not found:
        print("No working camera found.")
        print("Check Windows Settings > Privacy & security > Camera.")
        print("Enable camera access and 'Let desktop apps access your camera'.")
    else:
        print("At least one camera path works. Use the first OK camera_id in the app.")


if __name__ == "__main__":
    main()
