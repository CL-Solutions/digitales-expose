# Digitales Expose Backend - Production Setup

## Overview

Digitales Expose is a FastAPI-based property management system with multi-tenant support, designed for managing real estate properties, projects, and investment calculations.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis (for caching and background tasks)
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

Create a `.env` file in the root directory with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/digitales_expose

# Security
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# S3 Storage
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=digitalexpose-prod
S3_REGION=eu-central-1

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS Origins (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Email (Optional - for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourdomain.com

# OpenAI API (for micro location features)
OPENAI_API_KEY=your-openai-api-key
OPENAI_ASSISTANT_ID=your-assistant-id

# Sentry (Optional - for error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## Database Setup

### 1. Create Database

```bash
sudo -u postgres psql
CREATE DATABASE digitales_expose;
CREATE USER digitales_expose_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE digitales_expose TO digitales_expose_user;
\q
```

### 2. Run Migrations

```bash
alembic upgrade head
```

### 3. Create Initial Tenant and Super Admin

```bash
python scripts/create_initial_data.py
```

## Production Deployment

### Option 1: Using Gunicorn with Uvicorn Workers

Create a `gunicorn_config.py` file:

```python
bind = "0.0.0.0:8000"
workers = 4  # Adjust based on CPU cores
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
timeout = 60
graceful_timeout = 30
preload_app = True
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
```

Start the application:

```bash
gunicorn app.main:app -c gunicorn_config.py
```

### Option 2: Using Systemd Service

Create `/etc/systemd/system/digitales-expose.service`:

```ini
[Unit]
Description=Digitales Expose API
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/digitales-expose
Environment="PATH=/opt/digitales-expose/venv/bin"
ExecStart=/opt/digitales-expose/venv/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable digitales-expose
sudo systemctl start digitales-expose
sudo systemctl status digitales-expose
```

### Option 3: Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_config.py"]
```

Build and run:

```bash
docker build -t digitales-expose:latest .
docker run -d \
  --name digitales-expose \
  -p 8000:8000 \
  --env-file .env \
  digitales-expose:latest
```

## Nginx Configuration

Create `/etc/nginx/sites-available/digitales-expose`:

```nginx
upstream digitales_expose {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://digitales_expose;
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
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/digitales-expose /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL Certificate with Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

## Background Tasks with Celery (Optional)

If using Celery for background tasks:

```bash
# Create celery service
sudo nano /etc/systemd/system/digitales-expose-celery.service
```

```ini
[Unit]
Description=Digitales Expose Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/opt/digitales-expose
Environment="PATH=/opt/digitales-expose/venv/bin"
ExecStart=/opt/digitales-expose/venv/bin/celery -A app.celery worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring and Logging

### 1. Application Logs

```bash
# View application logs
sudo journalctl -u digitales-expose -f

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### 2. Health Check Endpoint

The API provides a health check endpoint at `/health` that returns:
- Database connectivity status
- Redis connectivity status
- S3 connectivity status
- Application version

### 3. Monitoring with Prometheus (Optional)

Add Prometheus metrics endpoint:

```python
# In app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

## Backup Strategy

### 1. Database Backup

Create a backup script `/opt/scripts/backup_db.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/postgres"
mkdir -p $BACKUP_DIR

pg_dump digitales_expose | gzip > $BACKUP_DIR/digitales_expose_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

Add to crontab:

```bash
0 2 * * * /opt/scripts/backup_db.sh
```

### 2. S3 Sync (if using local storage)

```bash
aws s3 sync /opt/digitales-expose/uploads s3://digitales-expose-backup/uploads --delete
```

## Performance Optimization

### 1. Database Indexes

Ensure proper indexes are created:

```sql
-- Check migration files for indexes
-- Additional indexes based on query patterns
CREATE INDEX idx_properties_project_id ON properties(project_id);
CREATE INDEX idx_properties_active ON properties(active);
CREATE INDEX idx_projects_city ON projects(city);
CREATE INDEX idx_expose_links_link_id ON expose_links(link_id);
```

### 2. Redis Caching

Configure Redis for caching frequently accessed data:
- User permissions
- Tenant settings
- City data
- Project listings

### 3. CDN for Static Assets

Configure CloudFlare or another CDN for S3 bucket to serve images faster.

## Security Checklist

- [ ] Strong SECRET_KEY generated and stored securely
- [ ] Database credentials are strong and unique
- [ ] S3 credentials have minimal required permissions
- [ ] CORS origins are properly configured
- [ ] SSL certificate is valid and auto-renews
- [ ] Firewall rules restrict database/Redis access
- [ ] Regular security updates applied
- [ ] Rate limiting configured on Nginx
- [ ] Request size limits configured
- [ ] SQL injection protection (SQLAlchemy ORM)
- [ ] XSS protection headers configured

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL format
   - Verify PostgreSQL is running
   - Check firewall rules

2. **S3 Upload Failures**
   - Verify S3 credentials
   - Check bucket permissions
   - Ensure bucket exists

3. **CORS Errors**
   - Add frontend domain to CORS_ORIGINS
   - Restart application after changes

4. **Memory Issues**
   - Adjust Gunicorn workers
   - Monitor memory usage
   - Consider upgrading server

## Maintenance

### Regular Tasks

1. **Weekly**
   - Check application logs for errors
   - Monitor disk space
   - Verify backups are running

2. **Monthly**
   - Update dependencies: `pip install -U -r requirements.txt`
   - Review and rotate logs
   - Check SSL certificate expiration

3. **Quarterly**
   - Security audit
   - Performance review
   - Database optimization

## Support

For issues or questions:
- Check logs: `sudo journalctl -u digitales-expose -n 100`
- Database queries: `sudo -u postgres psql digitales_expose`
- Application shell: `python -m app.shell`