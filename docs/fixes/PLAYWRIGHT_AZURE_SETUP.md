# Playwright Setup for Azure App Service CI/CD

## 🎯 Overview

Your Azure App Service deployment uses **GitHub Actions CI/CD** (not Docker containers). This means Playwright needs to be installed in **two places**:

1. **GitHub Actions build** (for creating the deployment artifact)
2. **Azure App Service startup** (for runtime execution)

---

## ✅ Changes Applied

### 1. GitHub Actions Workflow - `.github/workflows/main_aisightapi.yml`

**Added Playwright browser installation step:**

```yaml
- name: Install Playwright browsers (if needed)
  run: |
    source venv/bin/activate
    if pip list | grep -q playwright; then
      echo "Playwright detected, installing browsers..."
      playwright install --with-deps chromium
    else
      echo "Playwright not in requirements.txt, skipping browser installation"
    fi
```

**What this does:**
- ✅ Checks if Playwright is in your requirements.txt
- ✅ Installs Chromium browser + system dependencies
- ✅ Only runs if Playwright is detected (won't break current setup)
- ✅ Includes the browsers in the deployment artifact

---

### 2. Startup Script - `startup.sh`

**Added Playwright runtime initialization:**

```bash
# Set Playwright browser path
export PLAYWRIGHT_BROWSERS_PATH=/home/site/wwwroot/.playwright

# Install Playwright browsers if Playwright is installed
echo "Checking for Playwright..."
if python -c "import playwright" 2>/dev/null; then
    echo "Playwright detected, installing browsers..."
    python -m playwright install --with-deps chromium || echo "Warning: Playwright browser installation failed (may need system dependencies)"
else
    echo "Playwright not installed, skipping browser setup"
fi
```

**What this does:**
- ✅ Sets the browser installation path
- ✅ Checks if Playwright is available at runtime
- ✅ Installs browsers on first container startup
- ✅ Gracefully handles failures (won't crash your app)

---

### 3. Dockerfile - `Dockerfile` (Bonus - for local/container deployments)

**Added for future Docker-based deployments:**

```dockerfile
# System dependencies for Playwright
RUN apt-get update && apt-get install -y \
    # ... all Playwright dependencies ...

# Install Playwright browsers
RUN if pip list | grep -q playwright; then \
    playwright install --with-deps chromium && \
    playwright install-deps; \
    fi
```

**Note:** This won't be used by your current Azure App Service deployment, but it's ready if you switch to Azure Container Instances or Docker.

---

## 🚀 How to Enable Playwright

### Option 1: Keep Current Setup (Firecrawl)

**Do nothing!** Your current deployment uses Firecrawl and doesn't need Playwright. All changes are conditional and won't affect your app.

### Option 2: Switch to Playwright

**Step 1:** Add Playwright to `requirements.txt`:

```bash
echo "playwright" >> requirements.txt
```

**Step 2:** Commit and push to trigger CI/CD:

```bash
git add requirements.txt .github/workflows/main_aisightapi.yml startup.sh
git commit -m "Add Playwright support for Azure App Service"
git push origin main
```

**Step 3:** Monitor the deployment:
- GitHub Actions will install Playwright browsers during build
- Azure App Service will configure Playwright on startup
- Check logs at: `https://aisightapi.scm.azurewebsites.net/api/logstream`

---

## ⚠️ Important: Azure App Service Limitations

### System Dependencies

Azure App Service **Python runtime** has limited system packages. Playwright's `--with-deps` flag **may not work fully** because:

- ❌ Cannot install system packages (needs `apt-get`)
- ❌ No root access to install libraries
- ⚠️ Some Playwright features may fail

### Solutions

#### Solution A: Use Docker Deployment (Recommended for Playwright)

Switch from native Python runtime to Docker:

1. **Create Azure Container Registry:**
   ```bash
   az acr create --name aisightregistry --resource-group aisight-rg --sku Basic
   ```

2. **Update GitHub Actions to build Docker image:**
   ```yaml
   - name: Build and push Docker image
     run: |
       docker build -t aisightregistry.azurecr.io/aisight:${{ github.sha }} .
       docker push aisightregistry.azurecr.io/aisight:${{ github.sha }}
   ```

3. **Deploy container to App Service:**
   - App Service can run Docker containers
   - Full control over system dependencies
   - Playwright will work perfectly

#### Solution B: Use Azure Container Instances (ACI)

Deploy as a containerized service:
- Full Docker support
- Better isolation
- More expensive but more flexible

#### Solution C: Keep Firecrawl (Current - Easiest)

Firecrawl handles all the complexity:
- ✅ No browser needed
- ✅ No system dependencies
- ✅ Works on Azure App Service Python runtime
- ✅ Reliable and maintained

---

## 🔍 Current Architecture

### What You Have Now

```
GitHub Actions (Build)
  ├─ Install Python dependencies
  ├─ Create deployment artifact
  └─ Deploy to Azure App Service
      ├─ Python 3.12 runtime
      ├─ Firecrawl for web crawling
      └─ No browser needed ✅
```

### If You Add Playwright

```
GitHub Actions (Build)
  ├─ Install Python dependencies
  ├─ Install Playwright + Chromium ⚠️
  ├─ Create deployment artifact (larger)
  └─ Deploy to Azure App Service
      ├─ Python 3.12 runtime
      ├─ Playwright startup script
      └─ May fail due to missing system libs ❌
```

### Recommended: Docker-based Deployment

```
GitHub Actions (Build)
  ├─ Build Docker image
  │   ├─ System dependencies ✅
  │   ├─ Python dependencies ✅
  │   └─ Playwright + Chromium ✅
  ├─ Push to Container Registry
  └─ Deploy to Azure App Service (Container Mode)
      └─ Everything works perfectly ✅
```

---

## 📊 Comparison Table

| Feature | Current (Firecrawl) | Playwright on App Service | Docker + Playwright |
|---------|---------------------|---------------------------|---------------------|
| **Setup Complexity** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐ Complex |
| **Reliability** | ✅ High | ⚠️ Medium | ✅ High |
| **System Dependencies** | ✅ None needed | ❌ May fail | ✅ Full control |
| **Deployment Time** | ⚡ Fast (2-3 min) | ⏱️ Slow (5-8 min) | ⏱️ Slow (6-10 min) |
| **Cost** | 💰 App Service + Firecrawl API | 💰 App Service only | 💰💰 App Service + ACR |
| **JS Rendering** | ✅ Via Firecrawl | ✅ Via Playwright | ✅ Via Playwright |
| **Maintenance** | ⭐ Low | ⭐⭐ Medium | ⭐⭐⭐ Higher |

---

## 🎯 Recommendation

### Keep Firecrawl (Current Setup) ✅

**Reasons:**
1. ✅ Already working and deployed
2. ✅ No infrastructure changes needed
3. ✅ Reliable and maintained
4. ✅ Your code already uses it ([crawler.py](core/website_crawler/crawler.py))
5. ✅ No Azure limitations to worry about

### Switch to Playwright Only If:

1. 🔹 Firecrawl API costs are too high
2. 🔹 You need more control over crawling logic
3. 🔹 You're willing to migrate to Docker deployment
4. 🔹 You need custom browser automation features

---

## 🚨 Testing the Setup

If you decide to test Playwright:

### 1. Check GitHub Actions Logs

After pushing, check the workflow run:
```
https://github.com/YOUR_USERNAME/AISight1.0/actions
```

Look for:
```
✅ Playwright detected, installing browsers...
✅ Downloading Chromium...
✅ Chromium installed successfully
```

### 2. Check Azure App Service Logs

Stream logs in real-time:
```bash
az webapp log tail --name aisightapi --resource-group aisight-rg
```

Or via portal:
```
https://aisightapi.scm.azurewebsites.net/api/logstream
```

Look for:
```
✅ Playwright detected, installing browsers...
✅ Chromium installed successfully
```

Or:
```
⚠️ Warning: Playwright browser installation failed (may need system dependencies)
```

### 3. Test API Endpoint

```bash
curl https://aisightapi.azurewebsites.net/
```

---

## 📝 Summary

✅ **GitHub Actions workflow updated** - Will install Playwright if in requirements.txt
✅ **Startup script updated** - Will configure Playwright at runtime
✅ **Dockerfile updated** - Ready for Docker deployments
✅ **Backward compatible** - Won't break current Firecrawl setup
⚠️ **Azure limitations** - May need Docker for full Playwright support

**Next Step:** Decide whether to keep Firecrawl or migrate to Docker + Playwright.

---

## 💬 Questions?

- **Using Firecrawl and happy?** → No changes needed! ✅
- **Want to use Playwright?** → Consider Docker deployment first
- **Need help migrating?** → Let me know and I'll create the Docker CI/CD workflow
