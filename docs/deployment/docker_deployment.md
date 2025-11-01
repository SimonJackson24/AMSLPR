# Docker Deployment Guide

This guide provides comprehensive instructions for deploying VisiGate using Docker containers.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later
- At least 4GB RAM available
- At least 10GB free disk space
- Network connectivity for camera access

## Quick Start

### Basic Deployment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd visigate
   ```

2. **Start the application:**
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment:**
   ```bash
   docker-compose ps
   curl http://localhost:5001/health
   ```

4. **Access the web interface:**
   Open your browser and navigate to `http://localhost:5001`

## Detailed Deployment Scenarios

### 1. Development Environment

For development and testing purposes:

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  visigate-dev:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5001:5001"
    volumes:
      - ./src:/app/src
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - FLASK_ENV=development
      - DEBUG=true
      - HAILO_ENABLED=false
    command: python run_server.py --debug --port 5001
```

**Usage:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Production Environment

For production deployment with optimized settings:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  visigate-prod:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "80:5001"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
      - ./models:/app/models
    environment:
      - FLASK_ENV=production
      - HAILO_ENABLED=true
      - TZ=UTC
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Usage:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. High Availability Deployment

For production environments requiring high availability:

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  visigate-app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
      - ./models:/app/models
    environment:
      - FLASK_ENV=production
      - HAILO_ENABLED=true
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: visigate
      POSTGRES_USER: visigate
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - visigate-app
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Port to bind the application | `5001` | No |
| `FLASK_ENV` | Flask environment (development/production) | `production` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `HAILO_ENABLED` | Enable Hailo TPU support | `true` | No |
| `TZ` | Timezone | `UTC` | No |
| `REDIS_URL` | Redis connection URL | - | No |
| `DATABASE_URL` | Database connection URL | - | No |

### Volume Mounts

| Host Path | Container Path | Purpose | Required |
|-----------|----------------|---------|----------|
| `./data` | `/app/data` | Application data storage | Yes |
| `./logs` | `/app/logs` | Log files | Yes |
| `./config` | `/app/config` | Configuration files | Yes |
| `./models` | `/app/models` | ML models and assets | No |
| `./ssl` | `/etc/ssl/certs` | SSL certificates | No |

## Docker Image Management

### Building Custom Images

```bash
# Build with specific Python version
docker build --build-arg PYTHON_VERSION=3.9 -t visigate:custom .

# Build with Hailo TPU support
docker build --build-arg HAILO_SDK=true -t visigate:hailo .
```

### Multi-stage Build

For optimized production images:

```dockerfile
# Dockerfile.multi-stage
FROM python:3.9-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9-slim as production

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY . .

EXPOSE 5001
CMD ["python", "run_server.py"]
```

## Networking and Security

### Port Configuration

```yaml
# Expose on standard HTTP port
ports:
  - "80:5001"

# Expose on HTTPS port with SSL
ports:
  - "443:5001"
```

### SSL/TLS Configuration

```yaml
# docker-compose.ssl.yml
version: '3.8'

services:
  visigate-ssl:
    build: .
    ports:
      - "443:5001"
    volumes:
      - ./ssl/cert.pem:/app/ssl/cert.pem
      - ./ssl/key.pem:/app/ssl/key.pem
    environment:
      - SSL_CERT_PATH=/app/ssl/cert.pem
      - SSL_KEY_PATH=/app/ssl/key.pem
```

### Network Security

```yaml
# docker-compose.secure.yml
version: '3.8'

services:
  visigate-secure:
    build: .
    networks:
      - visigate_network
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

networks:
  visigate_network:
    driver: bridge
    internal: true
```

## Monitoring and Logging

### Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Log Management

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  visigate-logging:
    build: .
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    volumes:
      - ./logs:/app/logs

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - visigate-logging
```

## Performance Optimization

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### Scaling

```yaml
# docker-compose.scaled.yml
version: '3.8'

services:
  visigate-scaled:
    build: .
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
    depends_on:
      - redis
      - postgres
```

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Find process using port
   lsof -i :5001
   # Kill process
   kill -9 <PID>
   ```

2. **Permission denied:**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 ./data ./logs ./config
   ```

3. **Hailo TPU not detected:**
   ```bash
   # Check device availability
   ls -la /dev/hailo*
   # Check permissions
   sudo chmod 666 /dev/hailo0
   ```

### Debug Commands

```bash
# View container logs
docker-compose logs -f visigate

# Access container shell
docker-compose exec visigate bash

# Check container resource usage
docker stats

# Inspect container configuration
docker inspect visigate_visigate_1
```

## Backup and Recovery

### Data Backup

```bash
# Backup volumes
docker run --rm -v visigate_data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .
```

### Database Backup

```bash
# Backup PostgreSQL database
docker-compose exec postgres pg_dump -U visigate visigate > backup.sql
```

### Recovery

```bash
# Restore from backup
docker run --rm -v visigate_data:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /data
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/docker-deploy.yml
name: Docker Deploy

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: docker build -t visigate:${{ github.sha }} .

    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker tag visigate:${{ github.sha }} myregistry.com/visigate:latest
        docker push myregistry.com/visigate:latest

    - name: Deploy to production
      run: |
        ssh user@production-server << EOF
          docker-compose pull
          docker-compose up -d
        EOF
```

## Best Practices

1. **Use specific image tags** instead of `latest`
2. **Implement health checks** for all services
3. **Use secrets management** for sensitive data
4. **Regularly update base images** for security
5. **Monitor resource usage** and adjust limits accordingly
6. **Implement proper logging** and log rotation
7. **Use multi-stage builds** for smaller images
8. **Test deployments** in staging environment first
9. **Implement backup strategies** for data persistence
10. **Use orchestration tools** like Kubernetes for production

## Support

For additional support or questions about Docker deployment:

- Check the [troubleshooting guide](../troubleshooting/docker_issues.md)
- Review the [configuration reference](../deployment/configuration.md)
- Contact support at support@visigate.com