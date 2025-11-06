# Deployment Guide - AWS Lightsail with Docker

This guide covers deploying the Product Scraper Engine to AWS Lightsail using Docker in a single-server configuration.

## Quick Start

For experienced users, here's the TL;DR:

```bash
# On your Lightsail instance (Ubuntu 22.04)
git clone https://github.com/your-org/product-scraper-engine.git
cd product-scraper-engine
./setup-lightsail.sh

# Or manually:
# 1. Install Docker & Docker Compose
# 2. Copy .env.example to .env.production and configure
# 3. docker-compose build
# 4. docker-compose --env-file .env.production up -d
# 5. Open port 8000 in Lightsail firewall
# 6. Access API at http://<your-ip>:8000
```

## Architecture Overview

```
┌─────────────┐     ┌──────────────────────────────┐     ┌─────────────┐
│   Client    │────▶│   AWS Lightsail Instance     │────▶│   Redis     │
│  (Browser)  │◀────│  ┌────────────────────────┐  │◀────│  (Upstash)  │
└─────────────┘     │  │  Docker Containers     │  │     └─────────────┘
                    │  │  ├── API Server (8000) │  │
                    │  │  ├── Worker 1          │  │     ┌─────────────┐
                    │  │  ├── Worker 2          │  │────▶│    Azure    │
                    │  │  ├── Worker 3          │  │     │   OpenAI    │
                    │  │  └── Worker 4          │  │     └─────────────┘
                    │  └────────────────────────┘  │
                    └──────────────────────────────┘
```

## Components

1. **API Server** (FastAPI in Docker): Handles HTTP requests, submits jobs to queue
2. **RQ Workers** (4 Docker containers): Process scraping jobs in background
3. **Redis** (Upstash hosted): Job queue and event storage
4. **Azure OpenAI** (External): LLM for content analysis

## Prerequisites

- AWS account with Lightsail access
- Upstash Redis account (free tier available)
- Azure OpenAI resource with API key
- Local machine with SSH client

## Recommended Lightsail Instance Size

| Instance Size | vCPU | RAM   | Use Case                       |
| ------------- | ---- | ----- | ------------------------------ |
| $10/month     | 1    | 2 GB  | Development/Testing            |
| $20/month     | 2    | 4 GB  | Small production (recommended) |
| $40/month     | 2    | 8 GB  | Medium production              |
| $80/month     | 4    | 16 GB | High-traffic production        |

**Recommended**: $20/month instance (2 vCPU, 4 GB RAM) for production use.

## Step-by-Step Deployment

### 1. Create Lightsail Instance

1. Go to [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Click **Create instance**
3. Select:
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only → Ubuntu 22.04 LTS
   - **Instance plan**: $20/month (2 vCPU, 4 GB RAM)
4. Name your instance: `product-scraper-engine`
5. Click **Create instance**

### 2. Configure Firewall

In your Lightsail instance:

1. Go to **Networking** tab
2. Under **IPv4 Firewall**, add these rules:
   - Custom TCP (port 8000) - For API access
   - SSH (port 22) - Already enabled by default

**Note**: Port 8000 will be publicly accessible. For production, consider adding authentication or using a VPN.

### 3. Connect to Instance

Download your SSH key from Lightsail and connect:

```bash
# Change key permissions
chmod 400 ~/Downloads/LightsailDefaultKey-*.pem

# Connect to instance
ssh -i ~/Downloads/LightsailDefaultKey-*.pem ubuntu@<your-instance-ip>
```

### 4. Install Docker and Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Log out and back in for group changes to take effect
exit
# Then reconnect via SSH
```

### 5. Deploy Application

```bash
# Clone repository
cd ~
git clone https://github.com/your-org/product-scraper-engine.git
cd product-scraper-engine

# Create environment file
nano .env.production
```

Add your environment variables:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Redis Configuration (Upstash)
REDIS_URL=rediss://default:your-password@your-redis.upstash.io:6379

# Optional: Application settings
LOG_LEVEL=info
```

### 6. Build and Start Containers

```bash
# Build Docker image
docker-compose build

# Start services
docker-compose --env-file .env.production up -d

# Check running containers
docker-compose ps

# View logs
docker-compose logs -f
```

### 7. Verify Deployment

```bash
# Test API health endpoint locally
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0"}

# Get your instance's public IP
curl ifconfig.me

# Test from your local machine (replace with your instance IP)
curl http://<your-instance-ip>:8000/health

# Access API documentation
# Open in browser: http://<your-instance-ip>:8000/docs
```

**Your API is now accessible at**: `http://<your-instance-ip>:8000`

### 8. Optional: Create Static IP (Recommended)

Lightsail instances get dynamic IPs by default. Create a static IP so it doesn't change:

1. In Lightsail Console, go to **Networking** tab
2. Click **Create static IP**
3. Select your instance
4. Name it: `scraper-static-ip`
5. Click **Create**

Your static IP will remain the same even if you restart the instance.

## Management and Maintenance

### View Application Logs

```bash
# View all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific service
docker-compose logs -f api
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100

# View logs for specific worker
docker-compose logs worker | grep "worker-1"
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart worker

# Full restart (rebuild)
docker-compose down
docker-compose up -d --build
```

### Update Application

```bash
# Navigate to application directory
cd ~/product-scraper-engine

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose --env-file .env.production up -d

# Verify update
docker-compose ps
curl http://localhost:8000/health
```

### Scale Workers

```bash
# Scale to 6 workers
docker-compose up -d --scale worker=6 --no-recreate

# Scale to 2 workers
docker-compose up -d --scale worker=2 --no-recreate

# Check worker count
docker-compose ps | grep worker
```

### Backup and Restore

#### Backup

```bash
# Backup environment configuration
cp .env.production .env.production.backup.$(date +%Y%m%d)

# Export Docker images (optional)
docker save product-scraper-engine:latest | gzip > scraper-image-backup.tar.gz
```

#### Restore

```bash
# Restore environment
cp .env.production.backup.20250106 .env.production

# Restore Docker image (if needed)
gunzip -c scraper-image-backup.tar.gz | docker load
```

## Monitoring and Health Checks

### API Health Endpoint

```bash
# Local health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0"}

# External health check (replace with your IP/domain)
curl http://your-instance-ip:8000/health
curl https://your-domain.com/health
```

### Monitor Container Status

```bash
# Check running containers
docker-compose ps

# Check resource usage
docker stats

# Check specific container logs
docker logs -f product-scraper-engine_api_1
```

### Key Metrics to Monitor

1. **Queue Size**: Number of pending jobs in Redis
2. **Worker Health**: Number of active workers
3. **Job Success Rate**: Completed vs failed jobs
4. **API Response Time**: Endpoint latency
5. **CPU/Memory Usage**: Container resource consumption
6. **Disk Space**: Available storage on Lightsail instance
7. **Error Rate**: Failed requests and job errors

### Using RQ Dashboard (Optional)

Monitor your job queue with a web interface:

```bash
# Create a temporary container to run RQ dashboard
docker run -it --rm \
  -p 9181:9181 \
  -e RQ_DASHBOARD_REDIS_URL=$REDIS_URL \
  eoranged/rq-dashboard

# Access at http://<your-instance-ip>:9181
```

**Note**: Don't forget to open port 9181 in Lightsail firewall if needed, or use SSH tunneling:

```bash
# On your local machine
ssh -L 9181:localhost:9181 -i ~/Downloads/LightsailDefaultKey-*.pem ubuntu@<your-instance-ip>

# Then access http://localhost:9181 on your local machine
```

## Performance Tuning

### Adjust Worker Count

Based on your Lightsail instance size:

| Instance | vCPU | RAM   | Recommended Workers |
| -------- | ---- | ----- | ------------------- |
| $10/mo   | 1    | 2 GB  | 2 workers           |
| $20/mo   | 2    | 4 GB  | 4 workers (default) |
| $40/mo   | 2    | 8 GB  | 6 workers           |
| $80/mo   | 4    | 16 GB | 8-12 workers        |

Edit `docker-compose.yml` to adjust the worker replicas:

```yaml
worker:
  # ... other config ...
  deploy:
    replicas: 6 # Change this number
```

### Optimize API Server

Edit `docker-compose.yml` to adjust uvicorn workers:

```yaml
api:
  # ... other config ...
  command: uvicorn src.api:app --host 0.0.0.0 --port 8000 --workers 2
```

**Rule of thumb**: Use (CPU cores × 2) + 1 for API workers

### Redis Connection Pooling

Monitor Redis connection usage in Upstash dashboard. The default configuration should handle:

- 4 API workers: ~8-16 connections
- 4 RQ workers: ~4-8 connections
- Total: ~12-24 concurrent connections

Upstash free tier supports 1000 concurrent connections.

## Security Best Practices

### Firewall Configuration

Only expose necessary ports:

- **Port 8000** (HTTP): For API access (use with caution - no encryption)
- **Port 22** (SSH): For administration (consider restricting to your IP)

**Important**: Since you're using HTTP without SSL, be careful about:

- Not sending sensitive data through the API
- Using strong authentication if implemented
- Considering a VPN for production access
- Moving to HTTPS when you have a domain

### Environment Variables

- **Never commit** `.env.production` to Git
- Use strong passwords for Redis
- Rotate API keys periodically
- Store sensitive data securely

```bash
# Secure environment file
chmod 600 .env.production

# Add to .gitignore
echo ".env.production" >> .gitignore
```

### Redis Security

- Use `rediss://` (TLS) connection
- Enable authentication (Upstash enforces this)
- Don't expose Redis port publicly
- Use Upstash's built-in security features

### Docker Security

```bash
# Run containers as non-root (already configured in Dockerfile)
# Containers run as user 'appuser' for security

# Keep images updated
docker-compose pull
docker-compose up -d

# Remove unused images
docker image prune -a
```

### Network Security

```bash
# Restrict SSH to your IP (optional)
# In Lightsail Console → Networking → IPv4 Firewall
# Edit SSH rule to allow only your IP address

# Monitor access logs
docker-compose logs api | grep "GET\|POST"
```

## Troubleshooting

### Workers Not Processing Jobs

**Symptoms**: Jobs stuck in queue, nothing happening

**Solutions**:

```bash
# Check if workers are running
docker-compose ps

# Check worker logs for errors
docker-compose logs worker

# Verify Redis connection
docker-compose exec api python -c "from redis import Redis; from src.config.redis import get_redis_url; r = Redis.from_url(get_redis_url()); print(r.ping())"

# Restart workers
docker-compose restart worker

# Check job queue in RQ dashboard
```

### API Not Responding

**Symptoms**: Cannot access API, timeouts

**Solutions**:

```bash
# Check if API container is running
docker-compose ps api

# Check API logs
docker-compose logs api

# Restart API
docker-compose restart api

# Check port binding
sudo netstat -tulpn | grep 8000

# Check firewall rules in Lightsail Console
# Ensure port 8000 is open

# Test from inside the instance
curl http://localhost:8000/health
```

### High Memory Usage

**Symptoms**: Server becoming slow, containers restarting

**Solutions**:

```bash
# Check resource usage
docker stats

# Check system memory
free -h

# Reduce worker count
docker-compose up -d --scale worker=2 --no-recreate

# Restart containers
docker-compose restart

# Consider upgrading Lightsail instance
```

### SSL Certificate Issues

**Symptoms**: Certificate expired, HTTPS not working

**Solutions**:

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Check auto-renewal
sudo systemctl status certbot.timer

# Restart nginx after renewal
sudo systemctl restart nginx
```

### Disk Space Full

**Symptoms**: "No space left on device" errors

**Solutions**:

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a --volumes

# Clean up logs
docker-compose logs --tail=0 > /dev/null

# Rotate/compress logs
sudo journalctl --vacuum-time=7d

# Clear old package cache
sudo apt clean
```

### Connection to Azure OpenAI Fails

**Symptoms**: Jobs failing with API errors

**Solutions**:

```bash
# Verify environment variables
docker-compose exec api env | grep AZURE

# Test API connection
docker-compose exec api python -c "from src.config.azure import get_azure_openai_client; client = get_azure_openai_client(); print('Connected!')"

# Check rate limits in Azure portal
# Verify API key is valid
# Check network connectivity
```

## Cost Optimization

### Lightsail Costs

- **Instance**: $20/month (2 vCPU, 4 GB RAM) - recommended
- **Data Transfer**: 2 TB included, $0.09/GB after
- **Static IP**: Free with instance
- **Snapshots**: $0.05/GB-month

### External Services

- **Upstash Redis**: Free tier (10K commands/day) or $10/month
- **Azure OpenAI**: Pay per token usage
- **Domain**: $10-15/year
- **Let's Encrypt SSL**: Free

### Total Monthly Cost Estimate

| Component                  | Cost             |
| -------------------------- | ---------------- |
| Lightsail Instance ($20)   | $20              |
| Upstash Redis (free tier)  | $0               |
| Azure OpenAI (usage-based) | $10-50           |
| Domain (annual/12)         | $1.25            |
| **Total**                  | **$31-71/month** |

### Cost Saving Tips

1. **Use Upstash free tier** for development/low traffic
2. **Optimize AI prompts** to reduce token usage
3. **Cache common requests** to reduce API calls
4. **Monitor data transfer** to avoid overage charges
5. **Use smaller instance** for development ($10/month)
6. **Stop instance** when not needed (development only)

## Backup and Disaster Recovery

### Create Lightsail Snapshot

```bash
# Via Lightsail Console:
# 1. Go to your instance
# 2. Click "Snapshots" tab
# 3. Click "Create snapshot"
# 4. Name it: scraper-YYYY-MM-DD

# Automate with AWS CLI (optional)
aws lightsail create-instance-snapshot \
  --instance-snapshot-name scraper-$(date +%Y%m%d) \
  --instance-name product-scraper-engine
```

**Recommendation**: Create weekly snapshots

### Backup Strategy

1. **Code**: Stored in Git repository
2. **Configuration**: Backup `.env.production` file securely
3. **Instance**: Weekly Lightsail snapshots
4. **Redis Data**: Upstash has automatic backups
5. **Logs**: Export critical logs periodically

### Disaster Recovery

If your instance fails:

```bash
# 1. Create new instance from snapshot
# Via Lightsail Console → Create instance → Snapshots → Select snapshot

# 2. Assign static IP (or update DNS)
# Via Lightsail Console → Networking → Attach static IP

# 3. Verify services
ssh -i key.pem ubuntu@new-ip
cd ~/product-scraper-engine
docker-compose ps

# 4. Update DNS if using custom domain
# Point your domain to new IP address
```

**Recovery Time Objective (RTO)**: ~15-30 minutes  
**Recovery Point Objective (RPO)**: Last snapshot (up to 7 days)

## Maintenance Schedule

### Daily

- Monitor API health endpoint
- Check error logs for issues

### Weekly

- Review job success rates
- Check disk space and memory usage
- Review security logs

### Monthly

- Create Lightsail snapshot
- Update dependencies (security patches)
- Review and optimize costs
- Backup environment configuration

### Quarterly

- Rotate API keys
- Review and update documentation
- Load testing and performance review

## Scaling Beyond Single Server

When you outgrow a single Lightsail instance:

### Horizontal Scaling Options

1. **Multiple Lightsail Instances**

   - Deploy API and workers on separate instances
   - Use Lightsail load balancer
   - Cost: $18/month for load balancer + instances

2. **AWS EC2 + Auto Scaling**

   - More control and flexibility
   - Auto-scale based on load
   - Use Application Load Balancer

3. **AWS ECS (Elastic Container Service)**

   - Managed container orchestration
   - Better for large-scale deployments
   - Integrates with AWS services

4. **Kubernetes (EKS)**
   - Full container orchestration
   - Complex but highly scalable
   - Best for very large deployments

**Start with single Lightsail server, scale when needed.**

## Support and Resources

### Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [AWS Lightsail Documentation](https://docs.aws.amazon.com/lightsail/)
- [Upstash Redis Documentation](https://docs.upstash.com/redis)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)

### Monitoring Tools

- RQ Dashboard: Monitor job queue
- Docker Stats: Container resource usage
- Lightsail Metrics: Built-in monitoring
- Upstash Console: Redis metrics

### Getting Help

- Check application logs: `docker-compose logs`
- Review this documentation
- Check GitHub issues
- Azure OpenAI support for API issues
- AWS support for Lightsail issues

---

## Quick Reference

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Update application
git pull && docker-compose up -d --build

# Scale workers
docker-compose up -d --scale worker=6 --no-recreate

# Check status
docker-compose ps

# Clean up
docker system prune -a
```

### Important Files

- `~/product-scraper-engine/.env.production` - Environment variables
- `~/product-scraper-engine/docker-compose.yml` - Docker configuration
- `~/product-scraper-engine/Dockerfile` - Container image definition
- `~/product-scraper-engine/logs/` - Application logs

### Health Check URLs

- API Health: `http://<your-instance-ip>:8000/health`
- API Docs: `http://<your-instance-ip>:8000/docs`
- RQ Dashboard: `http://localhost:9181` (when running, access via SSH tunnel)

---

**Last Updated**: November 2025  
**Version**: 1.0.0
