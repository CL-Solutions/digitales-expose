# Production Setup Guide - Digitales Expose Backend

This guide provides instructions for deploying the Digitales Expose backend API to a production environment.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- Redis (for caching and session management)
- S3-compatible storage (e.g., AWS S3, Hetzner Object Storage)
- Domain with SSL certificate
- Reverse proxy (e.g., Nginx, Caddy)

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd digitales-expose
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/digitales_expose_prod

# Security
SECRET_KEY=your-very-secure-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
CORS_ORIGINS=["https://your-frontend-domain.com"]

# S3 Storage
S3_ACCESS_KEY_ID=your-s3-access-key
S3_SECRET_ACCESS_KEY=your-s3-secret-key
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_BUCKET_NAME=digitales-expose-prod
S3_REGION=eu-central-1

# OpenAI (for micro location features)
OPENAI_API_KEY=your-openai-api-key
OPENAI_ASSISTANT_ID=your-assistant-id

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
SMTP_FROM_EMAIL=noreply@example.com

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# Sentry (optional, for error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Environment
ENVIRONMENT=production
DEBUG=false
```

## Database Setup

### 1. Create Database

```bash
sudo -u postgres psql
CREATE DATABASE digitales_expose_prod;
CREATE USER digitales_expose_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE digitales_expose_prod TO digitales_expose_user;
\q
```

### 2. Run Migrations

```bash
alembic upgrade head
```

### 3. Create Initial Super Admin

```bash
python scripts/create_superadmin.py
```

## Application Server

### Using Gunicorn

Create a `gunicorn_config.py` file:

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

Start the server:

```bash
gunicorn app.main:app -c gunicorn_config.py
```

### Using Systemd Service

Create `/etc/systemd/system/digitales-expose.service`:

```ini
[Unit]
Description=Digitales Expose API
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/digitales-expose
Environment="PATH=/var/www/digitales-expose/venv/bin"
ExecStart=/var/www/digitales-expose/venv/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable digitales-expose
sudo systemctl start digitales-expose
```

## Reverse Proxy Setup

### Nginx Configuration

Create `/etc/nginx/sites-available/digitales-expose`:

```nginx
server {
    listen 80;
    server_name api.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    location /static {
        alias /var/www/digitales-expose/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/digitales-expose /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL Certificate

Using Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.your-domain.com
```

## Database Backups

Create a backup script `/usr/local/bin/backup-digitales-expose.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/digitales-expose"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="digitales_expose_prod"
DB_USER="digitales_expose_user"

mkdir -p $BACKUP_DIR
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/backup_$TIMESTAMP.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

Add to crontab:

```bash
0 2 * * * /usr/local/bin/backup-digitales-expose.sh
```

## Monitoring

### Health Check Endpoint

The API provides a health check endpoint at `/api/v1/health` that returns:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "s3": "connected"
}
```

### Logging

Configure structured logging by updating the logging configuration in `app/core/config.py`:

```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/digitales-expose/api.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["file"]
    }
}
```

## Performance Optimization

### 1. Database Indexes

Ensure proper indexes are created:

```sql
-- Properties search performance
CREATE INDEX idx_properties_active ON properties(active);
CREATE INDEX idx_properties_project_id ON properties(project_id);
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_purchase_price ON properties(purchase_price);

-- Projects search performance
CREATE INDEX idx_projects_city ON projects(city);
CREATE INDEX idx_projects_status ON projects(status);
```

### 2. Redis Caching

Enable Redis caching for frequently accessed data:

```python
# In app/core/cache.py
CACHE_CONFIG = {
    "default_ttl": 300,  # 5 minutes
    "city_list_ttl": 3600,  # 1 hour
    "project_list_ttl": 600,  # 10 minutes
}
```

### 3. Database Connection Pooling

Configure SQLAlchemy connection pool in `app/core/database.py`:

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Security Checklist

- [ ] Use strong, unique passwords for all services
- [ ] Enable firewall (ufw) and only allow necessary ports
- [ ] Keep all dependencies updated regularly
- [ ] Enable rate limiting on the API
- [ ] Use environment variables for all sensitive data
- [ ] Enable CORS only for your frontend domain
- [ ] Regular security audits with `pip audit`
- [ ] Monitor for suspicious activity in logs
- [ ] Enable SQL injection protection
- [ ] Validate all user inputs

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify connection string in `.env`
   - Check database user permissions

2. **S3 Upload Failures**
   - Verify S3 credentials and endpoint
   - Check bucket permissions
   - Ensure bucket exists and is accessible

3. **High Memory Usage**
   - Reduce Gunicorn workers
   - Enable database connection pooling
   - Check for memory leaks in custom code

4. **Slow API Responses**
   - Enable query logging to identify slow queries
   - Add database indexes
   - Enable Redis caching
   - Use database query optimization

## Maintenance

### Regular Tasks

1. **Weekly**
   - Review error logs
   - Check disk space
   - Monitor API performance

2. **Monthly**
   - Update dependencies
   - Review security updates
   - Analyze usage patterns

3. **Quarterly**
   - Full system backup
   - Security audit
   - Performance optimization review

## Support

For issues or questions:
- Check application logs: `/var/log/digitales-expose/`
- Database logs: `/var/log/postgresql/`
- Nginx logs: `/var/log/nginx/`

## Version History

- 1.0.0 - Initial production release