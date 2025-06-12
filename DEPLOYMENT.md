# Money Manager - Deployment Guide

This guide provides detailed instructions for deploying the Money Manager application in various environments.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Environment Variables](#environment-variables)
5. [Database Management](#database-management)
6. [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites
- Python 3.11+
- pip
- Git

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd money-management-app
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

4. **Run the application**
   ```bash
   python src/main.py
   ```

5. **Access the application**
   - URL: http://localhost:5000
   - The database will be automatically created on first run

## Docker Deployment

### Single Container

1. **Build the image**
   ```bash
   docker build -t money-manager .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name money-manager \
     -p 5000:5000 \
     -v $(pwd)/data:/app/src/database \
     money-manager
   ```

### Docker Compose (Recommended)

1. **Start the application**
   ```bash
   docker-compose up -d
   ```

2. **View logs**
   ```bash
   docker-compose logs -f
   ```

3. **Stop the application**
   ```bash
   docker-compose down
   ```

## Production Deployment

### Using Docker with Reverse Proxy

1. **Create production docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     money-manager:
       build: .
       restart: unless-stopped
       volumes:
         - ./data:/app/src/database
       environment:
         - FLASK_ENV=production
       networks:
         - web
   
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
       depends_on:
         - money-manager
       networks:
         - web
   
   networks:
     web:
       external: true
   ```

2. **Configure Nginx (nginx.conf)**
   ```nginx
   events {
       worker_connections 1024;
   }
   
   http {
       upstream money_manager {
           server money-manager:5000;
       }
   
       server {
           listen 80;
           server_name your-domain.com;
           
           location / {
               proxy_pass http://money_manager;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
       }
   }
   ```

### Cloud Deployment Options

#### AWS ECS
1. Push image to ECR
2. Create ECS task definition
3. Deploy to ECS cluster
4. Configure Application Load Balancer

#### Google Cloud Run
1. Build and push to Container Registry
2. Deploy to Cloud Run
3. Configure custom domain

#### Azure Container Instances
1. Push to Azure Container Registry
2. Create container instance
3. Configure networking

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_ENV` | Flask environment | `development` | No |
| `SECRET_KEY` | Flask secret key | Auto-generated | No |
| `DATABASE_URL` | Database connection string | SQLite local file | No |
| `PORT` | Application port | `5000` | No |

### Setting Environment Variables

**Docker:**
```bash
docker run -e FLASK_ENV=production -e SECRET_KEY=your-secret-key money-manager
```

**Docker Compose:**
```yaml
environment:
  - FLASK_ENV=production
  - SECRET_KEY=your-secret-key
```

## Database Management

### Backup Database
```bash
# Local SQLite
cp src/database/app.db backup_$(date +%Y%m%d_%H%M%S).db

# Docker container
docker exec money-manager cp /app/src/database/app.db /tmp/backup.db
docker cp money-manager:/tmp/backup.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

### Restore Database
```bash
# Local
cp backup_file.db src/database/app.db

# Docker
docker cp backup_file.db money-manager:/app/src/database/app.db
docker restart money-manager
```

### Database Migration
The application automatically creates and updates the database schema on startup.

## Health Checks

The application includes health check endpoints:

- **Health Check**: `GET /api/auth/check`
- **Docker Health Check**: Configured in Dockerfile
- **Kubernetes Liveness Probe**: Use `/api/auth/check`

## Monitoring

### Application Logs
```bash
# Docker
docker logs money-manager

# Docker Compose
docker-compose logs money-manager
```

### Performance Monitoring
- Monitor response times for API endpoints
- Track database query performance
- Monitor memory and CPU usage

## Security Considerations

### Production Security Checklist
- [ ] Use HTTPS in production
- [ ] Set strong SECRET_KEY
- [ ] Enable firewall rules
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor access logs
- [ ] Use non-root container user

### SSL/TLS Configuration
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
}
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
```

#### Database Permission Issues
```bash
# Fix permissions
chmod 664 src/database/app.db
chown www-data:www-data src/database/app.db
```

#### Container Won't Start
```bash
# Check logs
docker logs money-manager
# Check container status
docker ps -a
```

#### Memory Issues
```bash
# Limit container memory
docker run --memory=512m money-manager
```

### Debug Mode
Enable debug mode for development:
```bash
export FLASK_ENV=development
python src/main.py
```

### Log Levels
Configure logging in production:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Performance Optimization

### Database Optimization
- Regular VACUUM for SQLite
- Index optimization
- Query optimization

### Application Optimization
- Enable gzip compression
- Use CDN for static assets
- Implement caching
- Connection pooling

### Container Optimization
- Multi-stage Docker builds
- Minimize image size
- Use Alpine Linux base images
- Optimize layer caching

## Scaling

### Horizontal Scaling
- Load balancer configuration
- Session management
- Database clustering
- Container orchestration

### Vertical Scaling
- Increase container resources
- Optimize database configuration
- Monitor resource usage

## Support

For deployment issues:
1. Check application logs
2. Verify configuration
3. Test connectivity
4. Review security settings
5. Contact support team

## Changelog

### Version 1.0.0
- Initial deployment guide
- Docker support
- Production configuration examples
- Security guidelines

