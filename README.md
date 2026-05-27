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
[User Browser] 
     ↓ (HTTPS)
[Render/Vercel/Railway Server] 
     ↓ (PostgreSQL via SSL)
[Neon/Supabase Database]
```

### Components:
- **Frontend**: Flask templates with Bootstrap styling
- **Backend**: Python Flask application
- **Database**: PostgreSQL hosted on Neon or Supabase
- **Camera Streaming**: OpenCV video capture with MJPEG streaming
- **Security**: Bcrypt hashing, session management, IP-based rate limiting

## Setup Instructions

### Prerequisites
- Python 3.8+
- Git
- Neon or Supabase account for PostgreSQL database

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
   Replace the DATABASE_URL with your Neon or Supabase connection string.

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

### Deployment to Cloud (Render/Railway/Vercel)

1. **Push to GitHub**
   Ensure your code is committed and pushed to GitHub.

2. **Connect to Render**
   - Create a new Web Service
   - Connect your GitHub repository
   - Set the build command: `pip install -r requirements.txt`
   - Set the start command: `gunicorn app:app --bind 0.0.0.0:8080`
   - Add environment variables:
     - `SECRET_KEY`: your secret key
     - `DATABASE_URL`: your Neon/Supabase PostgreSQL connection string

3. **Deploy**
   Render will automatically build and deploy your application.

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

*Note: Screenshots placeholder - actual screenshots would be added in the screenshots/ directory*

## Security Features

- **Password Security**: Bcrypt hashing with salt
- **Session Management**: Secure Flask sessions with timeout
- **IP Tracking**: All actions logged with IP address
- **Rate Limiting**: Flask-Limiter prevents brute force attacks
- **Input Validation**: Form validation and sanitization
- **Account Lockout**: Temporary lock after 5 failed attempts
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenCV for video processing
- Flask community for excellent documentation
- Neon/Supabase for PostgreSQL hosting