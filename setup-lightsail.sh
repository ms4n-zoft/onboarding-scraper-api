#!/bin/bash

# Product Scraper Engine - Lightsail Deployment Script
# This script helps set up the application on a fresh AWS Lightsail instance

set -e

echo "=========================================="
echo "Product Scraper Engine - Setup Script"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Please do not run this script as root${NC}"
    exit 1
fi

# Step 1: Update system
echo -e "${GREEN}Step 1: Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Step 2: Install Docker
echo -e "${GREEN}Step 2: Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${YELLOW}Note: You'll need to log out and back in for Docker group changes to take effect${NC}"
else
    echo "Docker already installed"
fi

# Step 3: Install Docker Compose
echo -e "${GREEN}Step 3: Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo apt install docker-compose -y
else
    echo "Docker Compose already installed"
fi

# Step 4: Clone repository (if not already done)
echo -e "${GREEN}Step 4: Checking repository...${NC}"
if [ ! -d "product-scraper-engine" ]; then
    echo "Please clone the repository first:"
    echo "git clone https://github.com/your-org/product-scraper-engine.git"
    echo "Then run this script from the parent directory"
    exit 1
fi

cd product-scraper-engine

# Step 5: Create environment file
echo -e "${GREEN}Step 5: Creating environment configuration...${NC}"
if [ ! -f ".env.production" ]; then
    cp .env.example .env.production
    echo -e "${YELLOW}Created .env.production from .env.example${NC}"
    echo -e "${YELLOW}Please edit .env.production with your actual credentials:${NC}"
    echo -e "${YELLOW}nano .env.production${NC}"
    echo ""
    echo "Required variables:"
    echo "  - AZURE_OPENAI_ENDPOINT"
    echo "  - AZURE_OPENAI_API_KEY"
    echo "  - AZURE_OPENAI_DEPLOYMENT_NAME"
    echo "  - REDIS_URL"
    echo ""
    read -p "Press Enter after you've configured .env.production..."
else
    echo ".env.production already exists"
fi

# Step 6: Build Docker images
echo -e "${GREEN}Step 6: Building Docker images...${NC}"
docker-compose build

# Step 7: Start services
echo -e "${GREEN}Step 7: Starting services...${NC}"
docker-compose --env-file .env.production up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Step 8: Check status
echo -e "${GREEN}Step 8: Checking service status...${NC}"
docker-compose ps

# Step 9: Test health endpoint
echo -e "${GREEN}Step 9: Testing API health...${NC}"
if curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✓ API is healthy!${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    echo "Check logs with: docker-compose logs"
fi

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)

# Step 10: Display next steps
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Your Product Scraper Engine is now running!"
echo ""
echo "API Access:"
echo "  Local:    http://localhost:8000"
echo "  Public:   http://${PUBLIC_IP}:8000"
echo "  Docs:     http://${PUBLIC_IP}:8000/docs"
echo ""
echo "Management commands:"
echo "  - View logs:     docker-compose logs -f"
echo "  - Restart all:   docker-compose restart"
echo "  - Stop all:      docker-compose down"
echo "  - Start all:     docker-compose up -d"
echo "  - Scale workers: docker-compose up -d --scale worker=6 --no-recreate"
echo ""
echo "Next steps:"
echo "  1. Test API: curl http://localhost:8000/health"
echo "  2. Create static IP in Lightsail Console (recommended)"
echo "  3. Update firewall to restrict SSH to your IP"
echo "  4. Test from your machine: curl http://${PUBLIC_IP}:8000/health"
echo ""
echo "Read docs/DEPLOYMENT.md for detailed instructions"
echo ""
