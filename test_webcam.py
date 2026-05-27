import cv2

print("Testing webcam access...")
cap = cv2.VideoCapture(0)

if cap.isOpened():
    print("Webcam opened successfully")
    ret, frame = cap.read()
    if ret:
        print("Frame captured successfully")
        print(f"Frame shape: {frame.shape}")
    else:
        print("Failed to capture frame")
    cap.release()
else:
    print("Failed to open webcam")