# Deployment Guide

This guide covers deploying the Product Scraper Engine to production environments.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  API Server │────▶│    Redis    │
│  (Browser)  │◀────│  (FastAPI)  │◀────│   (Queue)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │ RQ Workers  │
                                        │  (N nodes)  │
                                        └─────────────┘
```

## Components

1. **API Server** (FastAPI): Handles HTTP requests, submits jobs
2. **RQ Workers** (N instances): Process jobs in background
3. **Redis** (Upstash/hosted): Job queue and event storage
4. **Azure OpenAI**: LLM for content analysis

## Deployment Options

### Option 1: Single Server (Small Scale)

For development or small-scale production:

```
Server (1 instance)
├── API Server (uvicorn)
├── Worker (2-4 processes)
└── Redis (Upstash hosted)
```

### Option 2: Multi-Server (Production Scale)

For production workloads:

```
Load Balancer
├── API Server 1
├── API Server 2
└── API Server N

Worker Pool
├── Worker Server 1 (4-8 workers)
├── Worker Server 2 (4-8 workers)
└── Worker Server N (4-8 workers)

External Services
├── Redis (Upstash/ElastiCache)
└── Azure OpenAI
```

## Prerequisites

- Python 3.11+
- Redis (Upstash recommended for managed service)
- Azure OpenAI resource
- Server(s) with systemd or Docker

## Deployment Methods

### Method 1: Systemd Services (Linux)

#### 1. Install Application

```bash
# Clone repository
git clone https://github.com/your-org/product-scraper-engine.git
cd product-scraper-engine

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
# Create production environment file
sudo mkdir -p /etc/scraper
sudo nano /etc/scraper/production.env
```

Add your variables:

```bash
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-08-01-preview
REDIS_URL=rediss://...
```

#### 3. Create Systemd Service for API

Create `/etc/systemd/system/scraper-api.service`:

```ini
[Unit]
Description=Product Scraper API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/product-scraper-engine
Environment="PATH=/opt/product-scraper-engine/venv/bin"
EnvironmentFile=/etc/scraper/production.env

ExecStart=/opt/product-scraper-engine/venv/bin/uvicorn \
    src.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4. Create Systemd Service for Worker

Create `/etc/systemd/system/scraper-worker@.service`:

```ini
[Unit]
Description=Product Scraper Worker %i
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/product-scraper-engine
Environment="PATH=/opt/product-scraper-engine/venv/bin"
Environment="RQ_WORKER_NAME=worker-%i"
EnvironmentFile=/etc/scraper/production.env

ExecStart=/opt/product-scraper-engine/venv/bin/python worker.py

Restart=always
RestartSec=10

StandardOutput=append:/var/log/scraper/worker-%i.log
StandardError=append:/var/log/scraper/worker-%i-error.log

[Install]
WantedBy=multi-user.target
```

#### 5. Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start API server
sudo systemctl start scraper-api
sudo systemctl enable scraper-api

# Start workers (4 instances)
sudo systemctl start scraper-worker@{1..4}
sudo systemctl enable scraper-worker@{1..4}

# Check status
sudo systemctl status scraper-api
sudo systemctl status scraper-worker@1
```

#### 6. Monitor Logs

```bash
# API logs
sudo journalctl -u scraper-api -f

# Worker logs
sudo journalctl -u scraper-worker@1 -f

# All workers
sudo journalctl -u "scraper-worker@*" -f
```

### Method 2: Docker Compose

#### 1. Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Create docker-compose.yml

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME}
      - AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}
      - REDIS_URL=${REDIS_URL}
    command: uvicorn src.api:app --host 0.0.0.0 --port 8000 --workers 4
    restart: unless-stopped

  worker:
    build: .
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME}
      - AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}
      - REDIS_URL=${REDIS_URL}
      - RQ_WORKER_NAME=worker-${HOSTNAME}
    command: python worker.py
    deploy:
      replicas: 4
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

#### 3. Deploy

```bash
# Create .env.production file
cp .env.example .env.production
# Edit with production values

# Build and start
docker-compose --env-file .env.production up -d

# Scale workers
docker-compose --env-file .env.production up -d --scale worker=8

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Stop
docker-compose down
```

### Method 3: Kubernetes

#### 1. Create ConfigMap and Secret

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: scraper-secrets
type: Opaque
stringData:
  AZURE_OPENAI_API_KEY: "your-key-here"
  REDIS_URL: "rediss://..."

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: scraper-config
data:
  AZURE_OPENAI_ENDPOINT: "https://..."
  AZURE_OPENAI_DEPLOYMENT_NAME: "gpt-4o-mini"
  AZURE_OPENAI_API_VERSION: "2024-08-01-preview"
```

#### 2. Create Deployments

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scraper-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scraper-api
  template:
    metadata:
      labels:
        app: scraper-api
    spec:
      containers:
        - name: api
          image: your-registry/scraper:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: scraper-config
            - secretRef:
                name: scraper-secrets
          command:
            [
              "uvicorn",
              "src.api:app",
              "--host",
              "0.0.0.0",
              "--port",
              "8000",
              "--workers",
              "4",
            ]
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"

---
# worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scraper-worker
spec:
  replicas: 6
  selector:
    matchLabels:
      app: scraper-worker
  template:
    metadata:
      labels:
        app: scraper-worker
    spec:
      containers:
        - name: worker
          image: your-registry/scraper:latest
          envFrom:
            - configMapRef:
                name: scraper-config
            - secretRef:
                name: scraper-secrets
          env:
            - name: RQ_WORKER_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          command: ["python", "worker.py"]
          resources:
            requests:
              memory: "1Gi"
              cpu: "1000m"
            limits:
              memory: "2Gi"
              cpu: "2000m"

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: scraper-api
spec:
  selector:
    app: scraper-api
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer
```

#### 3. Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f secrets.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f worker-deployment.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/scraper-api
kubectl logs -f deployment/scraper-worker

# Scale workers
kubectl scale deployment scraper-worker --replicas=12
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Worker health (check logs)
sudo journalctl -u scraper-worker@1 --since "1 minute ago"
```

### Metrics to Monitor

1. **Queue Size**: Number of pending jobs
2. **Worker Count**: Number of active workers
3. **Job Success Rate**: Completed vs failed jobs
4. **Average Job Duration**: Time to process jobs
5. **API Response Time**: Endpoint latency
6. **Error Rate**: Failed requests

### Using RQ Dashboard

```bash
# Install
pip install rq-dashboard

# Run
rq-dashboard --redis-url $REDIS_URL

# Access at http://localhost:9181
```

## Performance Tuning

### API Server

- **Workers**: 2-4x CPU cores
- **Worker Class**: Use `uvicorn.workers.UvicornWorker` for async
- **Timeout**: 300s for long operations

### RQ Workers

- **Count**: Start with 2 workers per CPU core
- **Timeout**: 600s (10 minutes) for scraping jobs
- **Concurrency**: Run workers on separate processes/servers

### Redis

- **Connection Pool**: Default is usually sufficient
- **Max Connections**: Ensure Redis can handle (API workers + RQ workers)
- **Memory**: Plan for ~1MB per job in queue

## Security Checklist

- [ ] Environment variables stored securely (not in code)
- [ ] Redis requires authentication
- [ ] Redis uses TLS (rediss://)
- [ ] API behind reverse proxy (nginx/Caddy)
- [ ] HTTPS enabled with valid certificates
- [ ] Rate limiting configured
- [ ] CORS restricted to known origins
- [ ] Firewall rules limit access
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up

## Backup Strategy

### Redis Data

```bash
# Manual backup
redis-cli --rdb dump.rdb

# Automated (use Upstash backup feature or Redis persistence)
```

### Application Logs

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/scraper

/var/log/scraper/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

## Troubleshooting

### Workers not processing jobs

1. Check worker is running: `ps aux | grep worker.py`
2. Check Redis connection: `python tests/test_worker_setup.py`
3. Check queue size: Use RQ dashboard
4. Check logs: `sudo journalctl -u scraper-worker@1 -n 100`

### API slow to respond

1. Check queue size (may be overloaded)
2. Increase worker count
3. Check Azure OpenAI rate limits
4. Enable API caching if appropriate

### High memory usage

1. Reduce concurrent workers
2. Increase job timeout (allow jobs to finish)
3. Monitor for memory leaks in scraping code
4. Consider horizontal scaling

## Rollback Plan

```bash
# Systemd
sudo systemctl stop scraper-api scraper-worker@*
cd /opt/product-scraper-engine
git checkout <previous-commit>
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl start scraper-api scraper-worker@*

# Docker
docker-compose down
git checkout <previous-commit>
docker-compose build
docker-compose up -d
```
