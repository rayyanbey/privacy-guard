"""
PrivacyGuard - Owner Face Registration
Run this ONCE before starting the main app.

Usage:
    python setup_owner.py
"""

import os
import sys
import cv2
import face_recognition
import pickle
import time


ENCODING_PATH = "config/owner_encoding.pkl"
PHOTO_PATH    = "config/owner.jpg"


def capture_from_camera() -> str:
    """Capture owner photo from webcam."""
    print("\n[Setup] Opening camera. Press SPACE to capture, Q to quit.")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error] Cannot open camera.")
        sys.exit(1)

    captured = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.putText(frame, "Press SPACE to capture | Q to quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("PrivacyGuard - Owner Registration", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            captured = frame.copy()
            cv2.imwrite(PHOTO_PATH, captured)
            print(f"[Setup] Photo saved to {PHOTO_PATH}")
            break
        elif key == ord('q'):
            print("[Setup] Cancelled.")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

    cap.release()
    cv2.destroyAllWindows()
    return PHOTO_PATH


def encode_face(image_path: str):
    """Encode face from image file."""
    print(f"[Setup] Encoding face from {image_path}...")
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        print("[Error] No face detected in the image. Try again with better lighting.")
        sys.exit(1)

    if len(encodings) > 1:
        print(f"[Warning] {len(encodings)} faces detected. Using the first (largest) one.")

    return encodings[0]


def main():
    os.makedirs("config", exist_ok=True)
    print("=" * 50)
    print("  PrivacyGuard - Owner Registration")
    print("=" * 50)

    choice = input("\nUse existing photo (e) or capture from camera (c)? [c]: ").strip().lower()

    if choice == 'e':
        path = input("Enter path to your photo: ").strip()
        if not os.path.exists(path):
            print("[Error] File not found.")
            sys.exit(1)
    else:
        path = capture_from_camera()

    encoding = encode_face(path)

    with open(ENCODING_PATH, "wb") as f:
        pickle.dump(encoding, f)

    print(f"\n✅ Owner face registered successfully!")
    print(f"   Encoding saved to: {ENCODING_PATH}")
    print(f"\nYou can now run:  python main.py")


if __name__ == "__main__":
    main()
