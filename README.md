# CCTV Web Monitoring System

A web-based CCTV monitoring system with user authentication, role-based access, activity logging, and live camera streaming capabilities.

## Features

- User authentication with bcrypt password hashing
- Role-based access control (admin/user)
- Comprehensive activity logging (login/logout, IP addresses, actions)
- Live CCTV feed display with monitoring dashboard
- Camera configuration interface
- Rate limiting and security protection
- Responsive web interface

## System Architecture

```
Physical Topology:
[CCTV Camera] ---(Ethernet)--- [Router/Switch] ---(Ethernet)--- [App Server (Flask/Gunicorn)] ---(HTTPS)--- [Browser]

Cloud Architecture:
[Browser]
     ↓ (HTTPS)
[Railway Server]
     ↓ (PostgreSQL via SSL)
[Railway PostgreSQL]
```

### Components:
- **Physical CCTV Camera**: Hikvision, Dahua, or any RTSP-capable camera connected to LAN via router/switch
- **Router/Switch**: Standard network router connecting camera to local network
- **App Server**: Python Flask application running on Railway, receiving RTSP streams from camera
- **Database**: Railway PostgreSQL for persistent storage
- **Frontend**: Flask templates with Bootstrap styling
- **Camera Streaming**: OpenCV video capture with MJPEG streaming over HTTP

## Setup Instructions

### Prerequisites
- Python 3.8+
- Git
- Railway account for PostgreSQL database
- Physical CCTV camera with RTSP support connected to local network

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CCTV-WEB
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-super-secret-key-change-this-in-production
   DATABASE_URL=postgresql://username:password@host:port/dbname
   ```
   Replace the DATABASE_URL with your Railway PostgreSQL connection string.

5. **Initialize the database**
   ```bash
   python app.py
   ```
   The application will create tables on first run.

6. **Run the application**
   ```bash
   python app.py
   ```
   Access the application at http://localhost:8080

### Camera Connection

1. Connect your CCTV camera to the same network as your server via Ethernet or WiFi
2. Note the camera's IP address (usually found via camera's web interface or NVR)
3. Find the camera's RTSP URL from the manufacturer's documentation:
   - Hikvision: `rtsp://camera_ip:554/Streaming/Channels/101`
   - Dahua: `rtsp://camera_ip:554/cam/realmonitor?channel=1&subtype=0`
4. Enter the RTSP URL in the Camera Configuration page after logging in

### Deployment to Railway

1. **Push to GitHub**
   Ensure your code is committed and pushed to GitHub.

2. **Create Railway Project**
   - Go to railway.app and create a new project
   - Add a PostgreSQL database to the project
   - Note the connection string from the database tab

3. **Deploy Application**
   - Connect your GitHub repository to Railway
   - Add environment variables:
     - `SECRET_KEY`: a strong random secret key
     - `DATABASE_URL`: the Railway PostgreSQL connection string
   - Railway will automatically install dependencies and run gunicorn

4. **Verify Deployment**
   - Access your deployed application via the Railway-provided URL
   - Register an admin account (first user is automatically admin)
   - Configure your camera's RTSP stream URL
   - Verify live feed displays correctly

## Database Schema

### Tables
- **users**: Stores user credentials and profile information
- **camera_config**: Stores RTSP/HTTP stream URLs for cameras
- **logs**: Comprehensive activity logging with IP addresses, timestamps, and actions
- **login_attempts**: Tracks failed login attempts for security lockouts

### Relationships
- One-to-many: Users → Logs (each log entry references a user)
- One-to-one: LoginAttempts per IP address
- Single record: CameraConfig (singleton pattern for stream URL)

## Screenshots

### Login Page
![Login Page](screenshots/login.png)
*Secure login with bcrypt password verification*

### Dashboard
![Dashboard](screenshots/dashboard.png)
*Live CCTV feed with camera status indicator*

### Camera Configuration
![Camera Config](screenshots/configure_camera.png)
*Interface to configure RTSP/HTTP stream URLs*

### Activity Logs
![Logs](screenshots/logs.png)
*Complete audit trail with filtering by user*

## Security Features

- **Password Security**: Bcrypt hashing with salt
- **Session Management**: Secure Flask sessions with HttpOnly, Secure, SameSite=Lax cookies, 2-hour expiry
- **IP Tracking**: All actions logged with IP address
- **Rate Limiting**: Flask-Limiter prevents brute force attacks
- **Input Validation**: Form validation and sanitization
- **Account Lockout**: Temporary lock after 5 failed attempts
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **CSRF Protection**: Session-based request validation

## API Endpoints

### Authentication
- `GET /register` - Registration form
- `POST /register` - Process registration
- `GET /login` - Login form
- `POST /login` - Process login
- `GET /logout` - Logout user

### Camera
- `GET /dashboard` - Main dashboard with live feed
- `GET /video_feed` - MJPEG video stream
- `GET /configure` - Camera configuration form
- `POST /configure` - Save camera configuration
- `POST /test_connection` - Test camera stream connectivity

### Logs
- `GET /logs` - View activity logs with filtering

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## Acknowledgments

- OpenCV for video processing
- Flask community for excellent documentation
- Railway for PostgreSQL hosting