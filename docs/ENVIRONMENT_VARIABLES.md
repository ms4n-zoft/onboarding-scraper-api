# Environment Variables Reference

This document lists all environment variables used by the Product Scraper Engine.

## Required Variables

### Azure OpenAI Configuration

```bash
# Azure OpenAI endpoint URL
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Azure OpenAI API key
AZURE_OPENAI_API_KEY=your-api-key-here

# Azure OpenAI deployment name (the model you deployed)
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Azure OpenAI API version
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

### Redis Configuration

```bash
# Redis connection URL (Upstash or self-hosted)
# Format: redis://[[username]:[password]@]host[:port][/database]
# For Upstash with TLS: rediss://default:password@host:port
REDIS_URL=rediss://default:your-password@your-redis-host.upstash.io:6379
```

### Tavily API Configuration

```bash
# Primary Tavily API key for web search
TAVILY_API_KEY=tvly-your-primary-api-key-here

# Optional: Comma-separated list of backup API keys for automatic fallback
# when primary key hits rate limits
TAVILY_BACKUP_KEYS=tvly-backup-key-1,tvly-backup-key-2,tvly-backup-key-3
```

## Optional Variables

### Worker Configuration

```bash
# Custom worker name for identification in logs and monitoring
# Default: Uses system hostname
RQ_WORKER_NAME=worker-1

# Run worker in burst mode (process all jobs then exit)
# Useful for testing or one-time batch processing
# Default: false
RQ_WORKER_BURST=false
```

### API Configuration

```bash
# API server host (for uvicorn)
# Default: 0.0.0.0
API_HOST=0.0.0.0

# API server port (for uvicorn)
# Default: 8000
API_PORT=8000

# Number of API workers (for uvicorn)
# Default: 1
API_WORKERS=4
```

## Environment Setup

### Development (.env file)

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env

# Edit with your values
vim .env
```

Example `.env` file:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=abc123...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Redis (Upstash)
REDIS_URL=rediss://default:password@host.upstash.io:6379

# Worker (optional)
RQ_WORKER_NAME=dev-worker
```

### Production (System Environment)

For production deployments, set environment variables at the system level:

#### Using systemd

In your systemd service file (`/etc/systemd/system/scraper-worker.service`):

```ini
[Service]
Environment="AZURE_OPENAI_ENDPOINT=https://..."
Environment="AZURE_OPENAI_API_KEY=..."
Environment="REDIS_URL=rediss://..."
Environment="RQ_WORKER_NAME=worker-1"
```

#### Using Docker

In your `docker-compose.yml`:

```yaml
services:
  worker:
    environment:
      - AZURE_OPENAI_ENDPOINT=https://...
      - AZURE_OPENAI_API_KEY=...
      - REDIS_URL=rediss://...
      - RQ_WORKER_NAME=worker-1
```

Or using `.env` file:

```yaml
services:
  worker:
    env_file:
      - .env.production
```

#### Using Kubernetes

In your deployment YAML:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: scraper-secrets
type: Opaque
stringData:
  AZURE_OPENAI_API_KEY: "your-key"
  REDIS_URL: "rediss://..."

---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: worker
          envFrom:
            - secretRef:
                name: scraper-secrets
          env:
            - name: RQ_WORKER_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
```

## Security Best Practices

### 1. Never Commit Secrets

Add `.env` to `.gitignore`:

```bash
# .gitignore
.env
.env.*
!.env.example
```

### 2. Use Secret Management

For production, use proper secret management:

- **AWS**: AWS Secrets Manager or Parameter Store
- **Azure**: Azure Key Vault
- **GCP**: Google Secret Manager
- **Kubernetes**: Sealed Secrets or External Secrets Operator

### 3. Rotate Credentials Regularly

- Rotate API keys every 90 days
- Use different credentials per environment
- Monitor for unauthorized access

### 4. Restrict Access

- Use principle of least privilege
- Limit API key permissions to required scopes only
- Use separate Redis databases for dev/staging/prod

## Validation

To verify your environment variables are set correctly:

```bash
# Check required variables
python -c "
from src.utils.env import get_required_env_var
try:
    get_required_env_var('REDIS_URL')
    get_required_env_var('AZURE_OPENAI_ENDPOINT')
    print('✓ All required variables set')
except RuntimeError as e:
    print(f'✗ Missing: {e}')
"

# Test Redis connection
python tests/test_worker_setup.py
```

## Troubleshooting

### "Missing required environment variable: REDIS_URL"

**Solution**: Create a `.env` file with the REDIS_URL variable.

### "Missing required environment variable: AZURE_OPENAI_ENDPOINT"

**Solution**: Add Azure OpenAI credentials to your `.env` file.

### Worker can't connect to Redis

**Symptoms**: `ConnectionError` or `timeout` errors

**Solutions**:

1. Check REDIS_URL format (use `rediss://` for TLS)
2. Verify Redis server is accessible
3. Check firewall rules
4. Verify credentials are correct

### API rate limits

**Symptoms**: `RateLimitError` from Azure OpenAI

**Solutions**:

1. Reduce concurrent workers
2. Increase job timeout
3. Upgrade Azure OpenAI tier
4. Add retry logic with exponential backoff
