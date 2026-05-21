from flask import Blueprint, render_template, Response, redirect, url_for, session, request, flash, jsonify
from extensions import db
from models.log import Log
from models.camera import CameraConfig
import cv2
import numpy as np

camera = Blueprint('camera', __name__)


def get_stream_url():
    """Get the camera stream URL from the database, creating a default config if none exists."""
    config = CameraConfig.query.first()
    if config is None:
        config = CameraConfig()
        db.session.add(config)
        db.session.commit()
    return config.stream_url


def generate_frames():
    stream_url = get_stream_url()
    if stream_url is None:
        # Generate a placeholder image indicating no camera configured
        yield from generate_error_frame("No camera configured")
        return

    # Handle special case for webcam (0)
    if stream_url.strip() == '0':
        stream_url = 0
    elif not stream_url.strip():
        # Generate a placeholder image indicating empty URL
        yield from generate_error_frame("Empty camera URL")
        return

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        # Log the error but generate error frames to show in UI
        print(f"Error: Could not open video stream: {stream_url}")
        yield from generate_error_frame(f"Cannot open stream: {stream_url}")
        return

    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Warning: Failed to read frame from video stream")
                yield from generate_error_frame("Lost video signal")
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Warning: Failed to encode frame")
                yield from generate_error_frame("Encoding failed")
                break
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except Exception as e:
        print(f"Error in video stream: {e}")
        yield from generate_error_frame(f"Stream error: {str(e)}")
    finally:
        cap.release()


def generate_error_frame(message):
    """Generate a placeholder frame with an error message when stream fails."""
    import numpy as np
    # Create a black image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some text
    font = cv2.FONT_HERSHEY_SIMPLEX
    # Calculate text size to center it
    text_size = cv2.getTextSize(message, font, 1, 2)[0]
    text_x = (img.shape[1] - text_size[0]) // 2
    text_y = (img.shape[0] + text_size[1]) // 2
    # Add text with background for better readability
    cv2.rectangle(img, (text_x - 10, text_y - text_size[1] - 10),
                  (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
    cv2.putText(img, message, (text_x, text_y), font, 1, (255, 255, 255), 2)

    ret, buffer = cv2.imencode('.jpg', img)
    if not ret:
        # Fallback to a very simple black image if encoding fails
        buffer = np.zeros((100, 100, 3), dtype=np.uint8)
        ret, buffer = cv2.imencode('.jpg', buffer)

    frame = buffer.tobytes()
    # Yield the error frame multiple times to ensure it's displayed
    for _ in range(3):
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@camera.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    log = Log(
        username=session['username'],
        action='Viewed camera feed',
        ip_address=request.remote_addr,
        status='Success'
    )
    db.session.add(log)
    db.session.commit()

    camera_ready = get_stream_url() is not None
    return render_template('dashboard.html', camera_ready=camera_ready)


@camera.route('/video_feed')
def video_feed():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@camera.route('/configure', methods=['GET', 'POST'])
def configure_camera():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    # Optionally restrict to admin users; for now any logged-in user can configure
    config = CameraConfig.query.first()
    if config is None:
        config = CameraConfig()
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        stream_url = request.form.get('stream_url', '').strip()
        if stream_url == '':
            stream_url = None
        config.stream_url = stream_url
        db.session.commit()
        flash('Camera configuration saved.')
        return redirect(url_for('camera.dashboard'))

    return render_template('configure_camera.html', current_url=config.stream_url or '')


@camera.route('/test_connection', methods=['POST'])
def test_connection():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'stream_url' not in data:
        return jsonify({'success': False, 'error': 'No stream URL provided'}), 400

    stream_url = data['stream_url'].strip()

    # Handle special case for webcam (0)
    if stream_url == '0':
        stream_url = 0
    elif not stream_url:
        return jsonify({'success': False, 'error': 'Empty stream URL'}), 400

    # Test the connection
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        cap.release()
        return jsonify({'success': False, 'error': f'Cannot open video stream: {stream_url}'}), 400

    # Try to read a frame
    success, frame = cap.read()
    cap.release()

    if not success:
        return jsonify({'success': False, 'error': 'Cannot read frames from stream'}), 400

    return jsonify({'success': True, 'message': 'Connection successful'})
