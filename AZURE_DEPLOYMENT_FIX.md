# Fixing typing_extensions Error in Azure App Service

## The Error
```
ImportError: cannot import name 'Sentinel' from 'typing_extensions' (/agents/python/typing_extensions.py)
```

## Root Cause
Azure App Service has a system-level Python path at `/agents/python/` that contains an outdated `typing_extensions.py` file. This conflicts with the package we need.

---

## ✅ Solution Steps

### **Step 1: Update requirements.txt**
The file has been updated with explicit version constraints to force correct versions:

```txt
pydantic>=2.5.0
pydantic-core>=2.14.0
typing-extensions>=4.8.0
```

### **Step 2: Add Startup Command in Azure**

In Azure Portal → Your App Service → Configuration → General Settings → Startup Command:

**Option A: Override PYTHONPATH (Recommended)**
```bash
PYTHONPATH=/home/site/wwwroot:$PYTHONPATH python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Option B: Use pip install before start**
```bash
pip install --force-reinstall --no-cache-dir typing-extensions>=4.8.0 pydantic>=2.5.0 && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### **Step 3: Deploy Updated Code**

```bash
# From your local machine
cd /home/asmaa/projects/AISight1.0

# Commit the updated requirements.txt
git add requirements.txt
git commit -m "Fix typing_extensions conflict for Azure deployment"

# Push to Azure
git push azure main
# OR if using GitHub Actions
git push origin main
```

### **Step 4: Verify Deployment**

Check the deployment logs in Azure Portal:
1. Go to App Service → Deployment Center → Logs
2. Look for successful installation of packages
3. Verify no import errors

Test the API:
```bash
curl https://your-app.azurewebsites.net/
# Should return: {"message": "Citation Count API", "endpoints": ["/analyze"]}
```

---

## Alternative Solutions

### **Option 1: Add .deployment file**

Create a file named `.deployment` in your project root:

```ini
[config]
command = deploy.sh
```

Create `deploy.sh`:

```bash
#!/bin/bash

# Install dependencies with correct versions
pip install --upgrade pip
pip install --force-reinstall --no-cache-dir typing-extensions>=4.8.0 pydantic>=2.5.0 pydantic-core>=2.14.0
pip install -r requirements.txt

echo "Deployment complete"
```

Make it executable:
```bash
chmod +x deploy.sh
```

### **Option 2: Use Python 3.11 Instead of 3.12**

In Azure Portal → Configuration → General Settings:
- Change Python version from 3.12 to 3.11
- Python 3.11 has better compatibility with the `/agents/python/` path

### **Option 3: Create startup.sh Script**

Create `startup.sh` in your project root:

```bash
#!/bin/bash

# Ensure correct Python path order
export PYTHONPATH="/home/site/wwwroot:/home/site/wwwroot/antenv/lib/python3.12/site-packages:$PYTHONPATH"

# Reinstall critical packages
pip install --force-reinstall --no-cache-dir typing-extensions>=4.8.0 pydantic>=2.5.0

# Start the application
cd /home/site/wwwroot
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

In Azure Portal → Configuration → General Settings → Startup Command:
```
bash startup.sh
```

---

## Testing After Deployment

### 1. Check Application Logs
Azure Portal → App Service → Log stream

Look for:
```
✅ Application startup complete
❌ No ImportError messages
```

### 2. Test Health Endpoint
```bash
curl https://your-app.azurewebsites.net/
```

Expected response:
```json
{
  "message": "Citation Count API",
  "endpoints": ["/analyze"]
}
```

### 3. Test Full Analysis (with API keys)
```bash
curl -X POST https://your-app.azurewebsites.net/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "TestBrand",
    "brand_url": "https://example.com",
    "url_type": "category",
    "product_category": "electronics",
    "k": 6,
    "api_keys": {
      "openai_api_key": "sk-..."
    }
  }'
```

---

## Environment Variables to Set in Azure

Go to: App Service → Configuration → Application Settings

Add these if not already present:

```
OPENAI_API_KEY = sk-...
TAVILY_API_KEY = tvly-...
AZURE_WEBPUBSUB_CONNECTION_STRING = Endpoint=...
```

---

## Common Issues & Fixes

### Issue 1: Still Getting typing_extensions Error

**Fix:** Clear build cache in Azure
```bash
# In Azure Portal → Development Tools → Advanced Tools (Kudu) → Debug Console
rm -rf /home/.pip-cache
rm -rf /tmp/*
```

Then restart the app service.

### Issue 2: Package Installation Timeout

**Fix:** Increase the timeout in Azure
- App Service → Configuration → General Settings
- Set: `SCM_COMMAND_IDLE_TIMEOUT = 600`

### Issue 3: Module Not Found After Deployment

**Fix:** Ensure all imports are relative
```python
# ❌ Wrong
from queries.context_builder import ...

# ✅ Correct
from core.queries.context_builder import ...
```

---

## Recommended Startup Command

This is the **best solution** for Azure:

```bash
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH && pip install --quiet --force-reinstall --no-cache-dir typing-extensions>=4.8.0 pydantic-core>=2.14.0 && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Paste this in: Azure Portal → App Service → Configuration → General Settings → Startup Command

---

## Quick Checklist

- [ ] Updated requirements.txt with explicit versions
- [ ] Set startup command in Azure Portal
- [ ] Committed and pushed changes
- [ ] Verified deployment logs show success
- [ ] Tested health endpoint
- [ ] Tested with sample request
- [ ] No import errors in logs

---

**Status:** Ready to deploy
**Estimated Fix Time:** 5-10 minutes after deployment
