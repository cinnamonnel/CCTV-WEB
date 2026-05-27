#!/usr/bin/env python
"""
Test script to verify camera functionality in the CCTV system
"""
import cv2
import sys
import os

def test_webcam_directly():
    """Test webcam access directly with OpenCV"""
    print("=== Testing webcam directly ===")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open webcam (device 0)")
        return False

    print("Webcam opened successfully")

    # Try to capture a frame
    ret, frame = cap.read()
    if not ret:
        print("ERROR: Could not read frame from webcam")
        cap.release()
        return False

    print(f"Frame captured successfully - Shape: {frame.shape}")

    # Save a test frame to verify
    test_path = "test_frame.jpg"
    cv2.imwrite(test_path, frame)
    print(f"Test frame saved as {test_path}")

    cap.release()
    return True

def test_stream_url_handling():
    """Test how the application handles different stream URLs"""
    print("\n=== Testing stream URL handling ===")

    # Test cases that should work
    test_cases = [
        ("0", "Webcam (special case)"),
        ("1", "Second webcam if available"),
    ]

    for stream_url, description in test_cases:
        print(f"\nTesting {description}: '{stream_url}'")
        if stream_url.strip() == '0':
            processed_url = 0
            print(f"  -> Converted to integer: {processed_url} (for webcam)")
        else:
            processed_url = stream_url
            print(f"  -> Using as string: {repr(processed_url)}")

        cap = cv2.VideoCapture(processed_url)
        if cap.isOpened():
            print(f"  SUCCESS: Successfully opened stream")
            cap.release()
        else:
            print(f"  ERROR: Failed to open stream")

def check_database_config():
    """Check current camera configuration in database"""
    print("\n=== Checking database configuration ===")

    try:
        import sqlite3
        conn = sqlite3.connect('instance/cctv_web.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM camera_config;')
        rows = cursor.fetchall()

        if not rows:
            print("ERROR: No camera configuration found in database")
            conn.close()
            return False

        for row in rows:
            config_id, stream_url, updated_at = row
            print(f"Camera Config ID: {config_id}")
            print(f"   Stream URL: {repr(stream_url)}")
            print(f"   Updated at: {updated_at}")

            # Test how this would be processed
            if stream_url is None:
                print("   -> Would generate 'No camera configured' error")
            elif stream_url.strip() == '0':
                print("   -> Would be processed as webcam (integer 0)")
            elif not stream_url.strip():
                print("   -> Would generate 'Empty camera URL' error")
            else:
                print(f"   -> Would be used as RTSP/HTTP stream: {stream_url}")

        conn.close()
        return True

    except Exception as e:
        print(f"Error checking database: {e}")
        return False

if __name__ == "__main__":
    print("CCTV Camera System Test")
    print("=" * 50)

    # Test direct webcam access
    webcam_ok = test_webcam_directly()

    # Test URL handling logic
    test_stream_url_handling()

    # Check database configuration
    db_ok = check_database_config()

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  Webcam access: {'PASS' if webcam_ok else 'FAIL'}")
    print(f"  Database config: {'READ' if db_ok else 'ERROR'}")

    if webcam_ok:
        print("\nSUCCESS: Your webcam is working correctly!")
        print("   If you're not seeing video in the browser:")
        print("   1. Make sure you've logged into the CCTV system")
        print("   2. Check that your camera configuration is set to '0'")
        print("   3. Visit http://127.0.0.1:8080/camera/dashboard")
        print("   4. Ensure you're not blocking camera access in your browser")
    else:
        print("\nFAILURE: Webcam access failed!")
        print("   Possible issues:")
        print("   - Webcam is being used by another application")
        print("   - Webcam drivers need updating")
        print("   - Privacy settings blocking camera access")
        print("   - No webcam connected to the system")