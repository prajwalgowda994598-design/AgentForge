# AgentForge – Deployment Guide

## Prerequisites

- Ubuntu 22.04 LTS EC2 instance (t3.medium recommended, t3.large for production)
- Domain name (optional, but recommended for HTTPS)
- Docker Hub account

---

## 1. Provision AWS EC2

1. Launch an EC2 instance:
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t3.medium (4GB RAM minimum)
   - Storage: 20GB gp3 SSD
   - Security group: Open ports 22, 80, 443, 8000 (restrict 8000 to your IP)

2. Allocate an Elastic IP and attach it.

---

## 2. Server Setup

SSH into your instance and run:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

---

## 3. Deploy AgentForge

```bash
# Clone the repository
sudo mkdir -p /opt/agentforge
sudo chown $USER:$USER /opt/agentforge
cd /opt/agentforge
git clone https://github.com/prajwalgowda994598-design/AgentForge.git .

# Configure environment
cp .env.example .env
nano .env    # Fill in all required values

# Start all services
docker compose up -d --build

# Verify
docker compose ps
docker compose logs backend --tail=50
```

---

## 4. Configure GitHub Actions Secrets

In your GitHub repo → Settings → Secrets → Actions:

| Secret | Description |
|--------|-------------|
| `DOCKER_HUB_USERNAME` | Your Docker Hub username |
| `DOCKER_HUB_TOKEN` | Docker Hub access token |
| `EC2_HOST` | EC2 public IP / DNS |
| `EC2_USER` | ubuntu |
| `EC2_SSH_KEY` | Private SSH key (entire PEM file content) |
| `OPENAI_API_KEY` | OpenAI API key |
| `POSTGRES_PASSWORD` | Strong database password |
| `NEO4J_PASSWORD` | Strong Neo4j password |
| `SECRET_KEY` | Random 64-char secret for JWT |

---

## 5. HTTPS with Let's Encrypt (Optional but Recommended)

```bash
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d yourdomain.com

# Update nginx.conf to use SSL certificates
# Then mount certs in the docker-compose.yml frontend service
```

---

## 6. Monitoring & Logs

```bash
# View all logs
docker compose logs -f

# Check health
curl http://localhost:8000/health/ready | python3 -m json.tool

# Postgres
docker compose exec postgres psql -U agentforge -d agentforge

# Neo4j – open browser at http://YOUR_IP:7474

# Redis CLI
docker compose exec redis redis-cli
```

---

## 7. Backup

```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U agentforge agentforge | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup FAISS index
tar -czf faiss_backup_$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/agentforge_faiss_index/
```

---

## 8. Scaling

For higher load, consider:
- Increasing `WORKERS` in `.env` (backend Uvicorn workers)
- Moving to a managed RDS PostgreSQL instance
- Using ElastiCache for Redis
- Running Neo4j on dedicated instance with AuraDB
- Adding an Application Load Balancer (ALB) for multi-instance deployment
