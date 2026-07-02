# AI Booth Backend API

AI-powered photo booth management system with advanced features for events, photo processing, and sharing.

## Features

- 🔐 User authentication with JWT
- 👥 Team management and permissions
- 📸 Event and photo session management
- 🎨 Template-based photo customization
- 🖨️ Print job queue management
- 🔗 Photo sharing with short links
- 🤖 AI-powered image processing
- 📊 Analytics and reporting
- 💳 Subscription management (Stripe integration)
- 🚀 Production-ready with Docker

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for development)
- Redis 7+

### Development Setup

1. **Clone and navigate to the backend directory**

```bash
cd AIBooth/Backend
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. **Create `.env` file** (optional, defaults work for development)

```bash
cp .env.example .env
```

5. **Run database migrations**

```bash
alembic upgrade head
```

6. **Start the development server**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- API documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Using Docker

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- Backend API server
- Celery worker

## Testing

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=html
```

## Project Structure

```
Backend/
├── alembic/              # Database migrations
├── app/
│   ├── api/              # API routes
│   │   └── v1/           # API version 1
│   ├── core/             # Core configuration
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── repositories/     # Data access layer
├── tests/                # Test suite
├── logs/                 # Application logs
├── .env.example          # Environment variables template
├── Dockerfile            # Container definition
├── docker-compose.yml    # Multi-container setup
└── requirements.txt      # Python dependencies
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### Teams
- `GET /api/v1/teams` - List teams
- `POST /api/v1/teams` - Create team
- `GET /api/v1/teams/{id}` - Get team details
- `PUT /api/v1/teams/{id}` - Update team
- `DELETE /api/v1/teams/{id}` - Delete team

### Events
- `GET /api/v1/events` - List events
- `POST /api/v1/events` - Create event
- `GET /api/v1/events/{id}` - Get event details
- `PUT /api/v1/events/{id}` - Update event
- `DELETE /api/v1/events/{id}` - Delete event

### Photos
- `POST /api/v1/photos` - Upload photo
- `GET /api/v1/photos` - List photos
- `GET /api/v1/photos/{id}` - Get photo
- `DELETE /api/v1/photos/{id}` - Delete photo

### Templates
- `GET /api/v1/templates` - List templates
- `POST /api/v1/templates` - Create template
- `PUT /api/v1/templates/{id}` - Update template
- `DELETE /api/v1/templates/{id}` - Delete template

And more...

## Configuration

All configuration is done via environment variables. See `.env.example` for available options.

Key configurations:
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT signing key (auto-generated in dev)
- `CORS_ORIGINS` - Allowed CORS origins
- `RATE_LIMIT_PER_MINUTE` - API rate limit

## Production Deployment

1. Set environment variables in `.env`
2. Use PostgreSQL instead of SQLite
3. Set `DEBUG=False`
4. Set secure `SECRET_KEY`
5. Configure proper CORS origins
6. Use Docker Compose for deployment

## License

Proprietary
