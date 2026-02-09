# Deployment Guide - Power Genix Inventory Backend

This guide covers deploying your FastAPI backend and PostgreSQL database to various platforms.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Deployment with Docker](#local-deployment-with-docker)
4. [Cloud Deployment Options](#cloud-deployment-options)
   - [Railway (Recommended - Easiest)](#1-railway-recommended---easiest)
   - [Render](#2-render)
   - [DigitalOcean App Platform](#3-digitalocean-app-platform)
   - [AWS EC2](#4-aws-ec2)
5. [Post-Deployment Tasks](#post-deployment-tasks)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Git repository with your code
- GitHub account (for easy deployment)
- Database backup (if migrating existing data)

---

## Environment Setup

### 1. Create Environment File

Create a `.env` file in your project root (never commit this to git):

```bash
cp .env.example .env
```

Then edit `.env` with your actual values:

```env
APP_ENV=production
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your-very-long-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

### 2. Generate Secure SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Local Deployment with Docker

### Quick Start

1. **Install Docker & Docker Compose**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install docker.io docker-compose -y
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Check Logs**
   ```bash
   docker-compose logs -f backend
   ```

4. **Access Application**
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

5. **Stop Services**
   ```bash
   docker-compose down
   ```

6. **Stop and Remove All Data**
   ```bash
   docker-compose down -v
   ```

---

## Cloud Deployment Options

## 1. Railway (Recommended - Easiest)

**Cost:** $5/month (includes database), Free trial available

### Step-by-Step:

1. **Sign up at Railway**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Add PostgreSQL Database**
   - Click "+ New"
   - Select "Database" → "PostgreSQL"
   - Railway will provision the database

4. **Configure Backend Service**
   
   In your service settings, add these environment variables:
   ```
   APP_ENV=production
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SECRET_KEY=your-secret-key-here
   ACCESS_TOKEN_EXPIRE_MINUTES=120
   PORT=8000
   ```

5. **Configure Build Settings**
   
   Railway should auto-detect, but if needed:
   - **Build Command:** (leave empty - uses Dockerfile)
   - **Start Command:** `./entrypoint.sh`

6. **Deploy**
   - Railway will automatically build and deploy
   - You'll get a URL like: `your-app.railway.app`

7. **Run Migrations** (First time only)
   
   In Railway dashboard:
   - Go to your backend service
   - Click "Terminal" or use CLI
   ```bash
   alembic upgrade head
   ```

### Update CORS

Update `app/main.py` to allow your Railway domain:
```python
origins = [
    "http://localhost:5173",
    "https://your-app.railway.app",  # Add this
]
```

---

## 2. Render

**Cost:** Free tier available (spins down after 15 min inactivity), Paid starts at $7/month

### Step-by-Step:

1. **Sign up at Render**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create PostgreSQL Database**
   - Click "New +"
   - Select "PostgreSQL"
   - Choose free or paid plan
   - Note the Internal Database URL

3. **Create Web Service**
   - Click "New +"
   - Select "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name:** inventory-backend
     - **Environment:** Python 3
     - **Build Command:** `pip install -r requirement.txt`
     - **Start Command:** `./entrypoint.sh`

4. **Environment Variables**
   
   Add these in Render dashboard:
   ```
   APP_ENV=production
   DATABASE_URL=<your-postgres-internal-url>
   SECRET_KEY=<your-secret-key>
   ACCESS_TOKEN_EXPIRE_MINUTES=120
   PYTHON_VERSION=3.11.0
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy automatically

6. **Run Migrations**
   
   In Render Shell:
   ```bash
   alembic upgrade head
   ```

---

## 3. DigitalOcean App Platform

**Cost:** $5/month for basic app + $15/month for managed database

### Step-by-Step:

1. **Sign up at DigitalOcean**
   - Go to https://www.digitalocean.com
   - Create account ($200 free credit with referral)

2. **Create Managed Database**
   - Navigate to "Databases"
   - Click "Create Database Cluster"
   - Select PostgreSQL
   - Choose region and plan ($15/month basic)
   - Note the connection string

3. **Create App**
   - Navigate to "Apps"
   - Click "Create App"
   - Connect GitHub repository
   - Select your branch

4. **Configure App**
   
   Edit Plan:
   - **Name:** inventory-backend
   - **Environment:** Docker
   - **Dockerfile Path:** `Dockerfile`
   - **HTTP Port:** 8000

5. **Environment Variables**
   ```
   APP_ENV=production
   DATABASE_URL=${db.DATABASE_URL}
   SECRET_KEY=<your-secret-key>
   ACCESS_TOKEN_EXPIRE_MINUTES=120
   ```

6. **Add Database Component**
   - Link your PostgreSQL database created earlier

7. **Deploy**
   - Review and create
   - DigitalOcean will build and deploy

---

## 4. AWS EC2 (For Custom Setup)

**Cost:** Variable, ~$10-20/month for t3.small instance + RDS

### Step-by-Step:

1. **Launch EC2 Instance**
   ```bash
   # Launch Ubuntu 22.04 LTS
   # t3.small or larger recommended
   # Configure security group: Allow ports 22, 80, 443, 8000
   ```

2. **Connect to Instance**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

3. **Install Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv nginx postgresql-client git
   ```

4. **Clone Repository**
   ```bash
   git clone https://github.com/your-username/inventory-backend.git
   cd inventory-backend
   ```

5. **Setup Python Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirement.txt
   ```

6. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your values
   ```

7. **Create RDS PostgreSQL Database**
   - Go to AWS RDS Console
   - Create PostgreSQL database
   - Note the endpoint and credentials
   - Update DATABASE_URL in .env

8. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

9. **Setup Systemd Service**
   
   Create `/etc/systemd/system/inventory-backend.service`:
   ```ini
   [Unit]
   Description=Power Genix Inventory Backend
   After=network.target

   [Service]
   Type=notify
   User=ubuntu
   WorkingDirectory=/home/ubuntu/inventory-backend
   Environment="PATH=/home/ubuntu/inventory-backend/venv/bin"
   EnvironmentFile=/home/ubuntu/inventory-backend/.env
   ExecStart=/home/ubuntu/inventory-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

10. **Start Service**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start inventory-backend
    sudo systemctl enable inventory-backend
    sudo systemctl status inventory-backend
    ```

11. **Configure Nginx as Reverse Proxy**
    
    Create `/etc/nginx/sites-available/inventory-backend`:
    ```nginx
    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

    Enable site:
    ```bash
    sudo ln -s /etc/nginx/sites-available/inventory-backend /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    ```

12. **Setup SSL with Let's Encrypt**
    ```bash
    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d your-domain.com
    ```

---

## Post-Deployment Tasks

### 1. Create First Admin User

SSH into your server or use platform's shell, then:

```bash
# If using Railway/Render shell
alembic upgrade head

# Create admin user (you'll need to create a script or use database directly)
psql $DATABASE_URL -c "
INSERT INTO users (user_id, email, password_hash, name, role) 
VALUES ('OWN-ADMIN01', 'admin@powergenix.com', '\$2b\$12\$hashedpassword', 'Admin', 'owner');
"
```

Or create a migration script to seed initial admin user.

### 2. Update Frontend CORS

Update `app/main.py` with your production domain:

```python
origins = [
    "http://localhost:5173",
    "https://your-frontend-domain.com",
    "https://your-backend-domain.com",
]
```

### 3. Setup Monitoring

**For Railway:**
- Built-in metrics available in dashboard

**For Render:**
- Built-in logging and metrics

**For AWS/DigitalOcean:**
```bash
# Install monitoring
pip install python-json-logger sentry-sdk

# Add to main.py
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn")
```

### 4. Database Backup

**Railway:** Automatic backups included
**Render:** Automatic backups on paid plans
**DigitalOcean:** Automatic backups included
**AWS RDS:** Enable automated backups

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker-compose logs backend  # Local
# Or use platform's log viewer

# Common issues:
# 1. DATABASE_URL not set correctly
# 2. SECRET_KEY missing
# 3. Migration errors
```

### Database Connection Errors

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check if database is accessible
pg_isready -h host -p 5432
```

### Migration Errors

```bash
# Check current migration version
alembic current

# See migration history
alembic history

# Downgrade one version
alembic downgrade -1

# Upgrade to specific version
alembic upgrade <revision>
```

### CORS Errors

- Ensure your frontend domain is in `origins` list in `app/main.py`
- Check browser console for specific error
- Verify CORS headers are being sent

### Port Already in Use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

---

## Security Checklist

- [ ] Change SECRET_KEY to strong random value
- [ ] Use strong database password
- [ ] Enable SSL/HTTPS
- [ ] Restrict database access to backend only
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity
- [ ] Backup database regularly
- [ ] Use environment variables, never hardcode secrets

---

## Recommended: Railway Deployment

For the easiest and fastest deployment, I recommend **Railway**:

✅ Simple GitHub integration  
✅ Auto-deploys on git push  
✅ Built-in PostgreSQL  
✅ Free trial, then $5/month  
✅ Automatic SSL certificates  
✅ Easy environment variables management  
✅ Built-in logging and monitoring  

Follow the [Railway deployment steps](#1-railway-recommended---easiest) above to get started!

---

## Need Help?

- Check application logs first
- Review environment variables
- Verify database connectivity
- Check migration status
- Review platform-specific documentation

For platform support:
- Railway: https://docs.railway.app
- Render: https://render.com/docs
- DigitalOcean: https://docs.digitalocean.com
