# Quick Start Deployment Guide

## 🚀 Fastest Way to Deploy (5 minutes)

### Option 1: Railway (Recommended)

1. **Push code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy to Railway**
   - Visit https://railway.app
   - Click "Start a New Project"
   - Choose "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect the Dockerfile

3. **Add PostgreSQL Database**
   - In your project, click "+ New"
   - Select "Database" → "PostgreSQL"

4. **Configure Environment Variables**
   
   In your backend service settings, add:
   ```
   APP_ENV=production
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SECRET_KEY=<generate-random-key>
   ACCESS_TOKEN_EXPIRE_MINUTES=120
   ```
   
   Generate SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. **Deploy!**
   - Railway auto-deploys
   - Get your URL: `https://your-app.railway.app`

6. **Run Migrations** (First time)
   - Go to your backend service
   - Open "Terminal" tab
   - Run: `alembic upgrade head`

7. **Update Frontend**
   - Use your Railway URL in frontend API calls
   - Update CORS in `app/main.py` if needed

**Total Time: ~5 minutes**  
**Cost: $5/month** (includes database)

---

## 🐳 Local Docker Deployment

1. **Install Docker**
   ```bash
   # Ubuntu/Debian
   sudo apt install docker.io docker-compose -y
   ```

2. **Create .env file**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Start everything**
   ```bash
   docker-compose up -d
   ```

4. **Access your app**
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Database: localhost:5432

5. **View logs**
   ```bash
   docker-compose logs -f backend
   ```

6. **Stop everything**
   ```bash
   docker-compose down
   ```

**Total Time: ~2 minutes**  
**Cost: Free**

---

## 📝 Pre-Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] `.env` file created (don't commit!)
- [ ] Generated strong SECRET_KEY
- [ ] Database credentials ready
- [ ] CORS origins updated in `app/main.py`

---

## 🆘 Common Issues

### "Database connection failed"
```bash
# Check DATABASE_URL is set correctly
echo $DATABASE_URL

# Format: postgresql://user:password@host:port/dbname
```

### "Module not found"
```bash
# Ensure requirement.txt has all dependencies
pip freeze > requirement.txt
```

### "Migration error"
```bash
# Check current migration status
alembic current

# Upgrade to latest
alembic upgrade head
```

### "CORS error in frontend"
Update `app/main.py`:
```python
origins = [
    "http://localhost:5173",
    "https://your-frontend-domain.com",  # Add your domain
]
```

---

## 📚 More Details

See **DEPLOYMENT_GUIDE.md** for:
- Detailed deployment steps for each platform
- AWS, DigitalOcean, Render instructions
- Security best practices
- Monitoring setup
- Troubleshooting guide

---

## 🎯 Next Steps After Deployment

1. **Create admin user** via database or migration
2. **Test all endpoints** via `/docs`
3. **Setup monitoring** (optional)
4. **Configure backup** (automatic on most platforms)
5. **Update frontend** with production API URL
6. **Enable SSL/HTTPS** (automatic on Railway/Render)

---

**Recommended:** Use Railway for fastest and easiest deployment! 🚂
