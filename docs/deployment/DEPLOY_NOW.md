# 🚀 Quick Deploy to Azure - Start Here!

## ✅ What Was Fixed

The **Pydantic import error** (`from pydantic import _migration`) has been resolved by:

1. ✅ **Pinned exact versions** in requirements.txt (Pydantic 2.10.3)
2. ✅ **Added startup.sh** for proper Azure initialization
3. ✅ **Added runtime.txt** to specify Python 3.12
4. ✅ **Added .deployment** for Azure build configuration
5. ✅ **Updated GitHub Actions** workflow with package verification

## 🎯 Deploy Now (3 Steps)

### Step 1: Commit and Push
```bash
git add .
git commit -m "fix: Azure deployment with pinned Pydantic dependencies"
git push origin main
```

### Step 2: Configure Azure App Service

**Option A: Via Azure Portal (Easiest)**
1. Go to https://portal.azure.com
2. Navigate to your App Service: **aisightapi**
3. Go to **Configuration → General Settings**
4. Set **Startup Command** to: `bash startup.sh`
5. Click **Save**

**Option B: Via Azure CLI**
```bash
az webapp config set \
  --resource-group aisight-rg \
  --name aisightapi \
  --startup-file "bash startup.sh"
```

### Step 3: Wait for Deployment
- GitHub Actions will automatically deploy (2-5 minutes)
- Monitor at: https://github.com/YOUR_USERNAME/AISight1.0/actions

## 🧪 Test Deployment

```bash
# Test health endpoint
curl https://aisightapi.azurewebsites.net/

# Expected response:
{
  "message": "Citation Count API",
  "endpoints": ["/analyze"]
}
```

## 🔍 Monitor Deployment

**View Live Logs:**
```bash
az webapp log tail --name aisightapi --resource-group aisight-rg
```

**Check Deployment Status:**
```bash
az webapp show --name aisightapi --resource-group aisight-rg --query state
```

## 🆘 If It Still Fails

### Check These First:
1. ✅ Startup command is set to `bash startup.sh`
2. ✅ Python version is 3.12 (Configuration → General Settings)
3. ✅ Environment variables are set (see below)

### Required Environment Variables
Set in **Configuration → Application Settings**:
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `PINECONE_ENVIRONMENT`
- `WEBSITES_PORT=8000`
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true`

### Clear Cache and Redeploy
```bash
# Delete deployment cache
az webapp deployment source delete --name aisightapi --resource-group aisight-rg

# Redeploy
git commit --allow-empty -m "trigger redeploy"
git push origin main
```

## 📊 What Changed in Files

### requirements.txt ✅
- **Before**: `pydantic>=2.0.0,<2.13.0` (caused version conflicts)
- **After**: `pydantic==2.10.3` (exact version, no conflicts)

### New Files Added:
- `startup.sh` - Ensures proper app initialization
- `runtime.txt` - Specifies Python 3.12
- `.deployment` - Azure build configuration
- `web.config` - IIS integration (optional)
- `.azure/config` - Azure CLI defaults

## 💡 Why This Fixes the Error

The original error:
```
File ".../pydantic/__init__.py", line 5, in <module>
  from ._migration import getattr_migration
```

**Root Cause**: Azure's Oryx build system was installing incompatible Pydantic versions due to:
1. Loose version constraints (`>=2.0.0,<2.13.0`)
2. Dependency resolution conflicts between LangChain packages
3. Missing `pydantic-core` version specification

**Solution**: Exact version pinning ensures consistent dependency tree:
```
pydantic==2.10.3
pydantic-core==2.27.1
typing-extensions==4.12.2
annotated-types==0.7.0
```

## 🎉 Success Indicators

You'll know it worked when:
1. ✅ GitHub Actions build completes successfully
2. ✅ Azure logs show: "Application startup complete"
3. ✅ API responds at `https://aisightapi.azurewebsites.net/`
4. ✅ No "import pydantic._migration" errors in logs

## 📚 More Help

- **Full guide**: See `AZURE_DEPLOYMENT.md`
- **Azure logs**: Portal → App Service → Log stream
- **GitHub Actions**: Repository → Actions tab

---

**Ready? Run Step 1 above to deploy! 🚀**
