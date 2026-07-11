# Gocab - Ride Sharing Application

A comprehensive ride-sharing platform built with Django, featuring real-time WebSocket communication, location tracking, and driver-rider matching capabilities.

## 🚗 Features

### Core Functionality
- **User Management**: Separate profiles for riders and drivers
- **Real-time Location Tracking**: Live GPS tracking for drivers
- **WebSocket Communication**: Real-time updates using Django Channels
- **Trip Management**: Complete ride booking and tracking system
- **Driver Verification**: Comprehensive document upload and approval system
- **Payment Integration**: Ready for payment gateway integration

### Technical Features
- **Background Tasks**: Asynchronous task processing
- **Redis Integration**: Caching and session management
- **Database**: PostgreSQL support with SQLite for development
- **Static File Management**: Optimized static file serving
- **API Ready**: Structured for REST API development

## 🛠 Tech Stack

- **Backend**: Django 4.2.26
- **Real-time Communication**: Django Channels with Daphne
- **Database**: PostgreSQL (production), SQLite (development)
- **Caching**: Redis 7.0.1
- **Background Tasks**: Django Background Tasks
- **WebSockets**: Channels-Redis
- **Static Files**: Whitenoise
- **External APIs**: Google Maps Integration

## 📁 Project Structure

```
Gocab/
├── Gocabservices/          # Main Django project
│   ├── settings.py         # Django settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI configuration
├── gocabapp/              # Core application
│   ├── models.py          # Database models (Rider, Driver, Trip, etc.)
│   ├── views/             # View modules
│   ├── consumers.py       # WebSocket consumers
│   ├── forms.py           # Django forms
│   ├── templates/         # HTML templates
│   └── utils/             # Utility functions
├── media/                 # User uploaded files
├── static/                # Static assets
└── requirements.txt       # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- PostgreSQL (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Gocab/Gocabservices
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

4. **Set up environment variables**
   ```bash
   # Create .env file with necessary configurations
   # Database settings, Redis settings, Google Maps API key, etc.
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Start the development server**
   ```bash
   python manage.py runserver
   ```

9. **Start Redis server** (in separate terminal)
   ```bash
   redis-server
   ```

## 📊 Database Models

### Core Models
- **Rider**: User profile for ride customers
- **Driver**: Driver profile with verification documents
- **Trip**: Ride booking and tracking information
- **Vehicle**: Vehicle information and documents
- **Payment**: Payment processing records

### Key Features
- Driver document verification system
- Real-time location tracking
- Trip status management
- Rating and review system

## 🔧 Configuration

### Environment Variables
Set up the following environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `GOOGLE_MAPS_API_KEY`: Google Maps API key
- `SECRET_KEY`: Django secret key

### Database Setup
```bash
# For development (SQLite)
# Default configuration works out of the box

# For production (PostgreSQL)
DATABASE_URL=postgresql://username:password@localhost:5432/gocab
```

## 🌐 API Endpoints

The application is structured to support REST API development:
- User authentication and registration
- Driver registration and verification
- Trip booking and management
- Real-time location updates
- Payment processing

## 🧪 Testing

```bash
# Run tests
python manage.py test

# Run specific app tests
python manage.py test gocabapp
```

## 📝 Development Notes

### WebSocket Integration
- Uses Django Channels for real-time communication
- Redis as channel layer backend
- Consumers handle live location updates and trip status

### Background Tasks
- Driver location tracking
- Trip status updates
- Notification processing

### Security Features
- Rate limiting on sensitive endpoints
- Document verification system
- User authentication and authorization

## 🚀 Deployment

### Build Script
```bash
chmod +x build.sh
./build.sh
```

### Production Considerations
- Use PostgreSQL for production database
- Configure Redis for caching and sessions
- Set up proper static file serving
- Configure SSL certificates
- Set up monitoring and logging

## 📄 License

This project is proprietary and intended for commercial use.

## 🤝 Contributing

Contact the development team for contribution guidelines.

## 📞 Support

For technical support or questions, please contact the development team.

---

**Note**: This is a ride-sharing application in active development. Features and configurations may evolve.
