# Quick Command Reference

## 🚀 Deploy to Railway (Fastest - 5 min)

```bash
# 1. Push to GitHub
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Go to https://railway.app
# - Sign in with GitHub
# - New Project → Deploy from GitHub → Select your repo
# - Add PostgreSQL database (click "+ New" → PostgreSQL)
# - Add environment variables:
#   APP_ENV=production
#   DATABASE_URL=${{Postgres.DATABASE_URL}}
#   SECRET_KEY=<paste-generated-key>
#   ACCESS_TOKEN_EXPIRE_MINUTES=120

# 4. After deploy, run migrations in Railway Terminal:
alembic upgrade head

# Done! Your API is live at: https://your-app.railway.app
```

---

## 🐳 Test Locally with Docker

```bash
# 1. Create environment file
cp .env.example .env

# 2. Edit .env (use your local database)
nano .env

# 3. Start everything
docker-compose up -d

# 4. Check logs
docker-compose logs -f backend

# 5. Test API
curl http://localhost:8000/
# Or open: http://localhost:8000/docs

# 6. Stop everything
docker-compose down
```

---

## 📝 Before You Deploy

```bash
# Check your current database URL
cat .env | grep DATABASE_URL

# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check pending migrations
alembic current

# Create new migration (if needed)
alembic revision --autogenerate -m "description"

# Apply migrations locally
alembic upgrade head

# Check Python dependencies
pip freeze | tee requirement.txt
```

---

## 🔐 Generate Secure Credentials

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate password hash for admin user
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"

# Generate random database password
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

## 🗃️ Database Operations

```bash
# Connect to local database
psql postgresql://postgres:password@localhost:5432/inventory_db

# Connect to production database (Railway/Render)
psql $DATABASE_URL

# Backup database
pg_dump $DATABASE_URL > backup.sql

# Restore database
psql $DATABASE_URL < backup.sql

# Check database size
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size('inventory_db'));"

# List all tables
psql $DATABASE_URL -c "\dt"
```

---

## 🔄 Database Migrations

```bash
# Check current version
alembic current

# See migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "add new field"

# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# See SQL for migration (without applying)
alembic upgrade head --sql
```

---

## 🧪 Testing & Debugging

```bash
# Test API endpoint
curl http://localhost:8000/

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@powergenix.com","password":"your-password"}'

# Test with authentication
TOKEN="your-jwt-token"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/suppliers

# Check Docker logs
docker-compose logs -f backend

# Enter backend container
docker-compose exec backend bash

# Check Python version
python --version

# List installed packages
pip list
```

---

## 🔍 Troubleshooting

```bash
# Port already in use
sudo lsof -i :8000
sudo kill -9 <PID>

# Database connection test
psql $DATABASE_URL -c "SELECT version();"

# Check environment variables (in container)
docker-compose exec backend env

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build

# Remove all containers and volumes
docker-compose down -v

# View all containers
docker ps -a

# View Docker networks
docker network ls
```

---

## 📦 Dependency Management

```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirement.txt

# Install from requirements
pip install -r requirement.txt

# Check for outdated packages
pip list --outdated

# Update all packages (careful!)
pip install --upgrade pip
pip list --outdated | cut -d ' ' -f1 | xargs -n1 pip install -U
```

---

## 🌐 Production Updates

```bash
# Update code on Railway/Render (they auto-deploy)
git add .
git commit -m "Update message"
git push origin main

# Manual restart on Railway
# Use Railway dashboard → Service → Restart

# Check production logs
# Railway: Dashboard → Logs tab
# Render: Dashboard → Logs tab

# Run commands on production (Railway Terminal)
alembic upgrade head
python manage.py <command>
```

---

## 🔐 Environment Variables (Production)

### Railway Dashboard:
```
Variables → New Variable → Add each:

APP_ENV=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=120
PORT=8000
```

### Render Dashboard:
```
Environment → Add Environment Variable:

APP_ENV=production
DATABASE_URL=<from database>
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=120
PYTHON_VERSION=3.11.0
```

---

## 📊 Monitoring

```bash
# Check API health
curl https://your-app.railway.app/

# Check API docs
# Open: https://your-app.railway.app/docs

# Monitor database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check database size
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size(current_database()));"

# View active queries
psql $DATABASE_URL -c "SELECT pid, query, state FROM pg_stat_activity WHERE state != 'idle';"
```

---

## 🔄 Git Operations

```bash
# Check status
git status

# Add all changes
git add .

# Commit changes
git commit -m "Your message"

# Push to GitHub
git push origin main

# Create new branch
git checkout -b feature/new-feature

# View branches
git branch -a

# Switch branch
git checkout main

# Pull latest changes
git pull origin main
```

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start local | `docker-compose up -d` |
| Stop local | `docker-compose down` |
| View logs | `docker-compose logs -f backend` |
| Run migrations | `alembic upgrade head` |
| Test API | `curl http://localhost:8000/` |
| Generate secret | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| Connect DB | `psql $DATABASE_URL` |
| Push to deploy | `git push origin main` |

---

## 📱 One-Line Commands

```bash
# Complete local setup
cp .env.example .env && docker-compose up -d && docker-compose logs -f backend

# Deploy to production
git add . && git commit -m "Deploy" && git push origin main

# Quick database backup
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Check if everything is running
docker-compose ps && curl http://localhost:8000/ && psql $DATABASE_URL -c "SELECT 1;"

# Fresh start (caution: deletes data)
docker-compose down -v && docker-compose up -d --build
```

---

## 🆘 Emergency Commands

```bash
# If deployment fails, check logs immediately
# Railway: Dashboard → Logs
# Render: Dashboard → Logs

# Rollback migration
alembic downgrade -1

# Force rebuild on Railway
# Dashboard → Settings → Deploy → Redeploy

# Reset database (DANGER - deletes all data!)
# Don't run in production unless you're sure!
docker-compose down -v
# Or in production: Drop and recreate database
```

---

**Pro Tip:** Bookmark this file for quick reference! 📌
