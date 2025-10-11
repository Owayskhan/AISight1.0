# Azure App Service Deployment Guide

## Problem Solved
This guide addresses the Pydantic import error that occurs during Azure App Service deployment due to version conflicts in the dependency tree.

## Root Cause
The error `from pydantic import _migration` was caused by:
1. Conflicting Pydantic versions during Azure's build process
2. Missing Azure-specific configuration files
3. Incomplete dependency specification in requirements.txt

## Files Added/Modified

### 1. **startup.sh** - Azure startup script
- Ensures proper Python environment initialization
- Verifies critical packages before starting the app
- Sets PYTHONPATH correctly

### 2. **runtime.txt** - Python version specification
- Explicitly sets Python 3.12 for Azure

### 3. **.deployment** - Azure deployment configuration
- Enables build during deployment

### 4. **requirements.txt** - Fixed with strict version pinning
- **CRITICAL**: Pydantic and related packages pinned to exact versions
- All dependencies explicitly versioned to avoid conflicts

### 5. **.github/workflows/main_aisightapi.yml** - Enhanced CI/CD
- Added package verification step
- Upgraded pip before installation

## Deployment Steps

### Option 1: Deploy via GitHub Actions (Recommended)

1. **Commit all changes**:
   ```bash
   git add .
   git commit -m "fix: Azure deployment with pinned dependencies"
   git push origin main
   ```

2. **GitHub Actions will automatically**:
   - Build the application
   - Install dependencies with correct versions
   - Verify packages
   - Deploy to Azure

3. **Monitor deployment**:
   - Go to GitHub Actions tab
   - Watch the workflow progress
   - Check logs for any errors

### Option 2: Deploy via Azure CLI

1. **Login to Azure**:
   ```bash
   az login
   ```

2. **Set the startup command in Azure Portal**:
   - Go to Azure Portal → Your App Service → Configuration → General Settings
   - Set **Startup Command**: `bash startup.sh`
   - Click Save

3. **Deploy the code**:
   ```bash
   az webapp up --name aisightapi --resource-group aisight-rg
   ```

### Option 3: Deploy via VS Code Azure Extension

1. Install Azure App Service extension
2. Right-click on your project → "Deploy to Web App"
3. Select your app service
4. Confirm deployment

## Azure App Service Configuration

### Required Environment Variables
Set these in Azure Portal → Configuration → Application Settings:

```
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
PERPLEXITY_API_KEY=your-key-here
PINECONE_API_KEY=your-key-here
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=citation-analysis
TAVILY_API_KEY=your-key-here
WEBSITES_PORT=8000
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

### Startup Command
In Azure Portal → Configuration → General Settings:
```bash
bash startup.sh
```

Or if startup.sh doesn't work:
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Troubleshooting

### Issue: "Session is closed" error
**Solution**: Already handled in code with retry logic

### Issue: "Module not found" errors
**Solution**: Verify all imports in main.py use relative paths correctly:
- ✅ `from core.models.main import Queries`
- ❌ `from models.main import Queries`

### Issue: Slow cold start
**Solution**:
- Use Azure App Service Plan B1 or higher (not F1 Free tier)
- Enable "Always On" in Configuration → General Settings

### Issue: Memory errors
**Solution**:
- Scale up to B2 or B3 tier
- Optimize batch sizes in config.py

### Issue: Import errors persist
**Solution**: Clear build cache in Azure
```bash
az webapp deployment source delete --name aisightapi --resource-group aisight-rg
az webapp up --name aisightapi --resource-group aisight-rg
```

## Verification

### 1. Check Application Logs
```bash
az webapp log tail --name aisightapi --resource-group aisight-rg
```

### 2. Test the API
```bash
curl https://aisightapi.azurewebsites.net/
```

Expected response:
```json
{
  "message": "Citation Count API",
  "endpoints": ["/analyze"]
}
```

### 3. Monitor in Azure Portal
- Go to App Service → Monitoring → Logs
- Check for startup errors
- Verify Python packages loaded correctly

## Performance Optimization

### 1. Enable Application Insights
```bash
az monitor app-insights component create \
  --app aisight-insights \
  --location eastus \
  --resource-group aisight-rg
```

### 2. Configure Scaling
- Enable autoscaling based on CPU/memory
- Set min instances to 1, max to 3

### 3. Optimize Startup
- Reduce initial cold start time by:
  - Using "Always On" setting
  - Minimizing imports in main.py
  - Lazy loading heavy dependencies

## Cost Management

### Recommended Tiers
- **Development**: B1 Basic ($13/month) - Good for testing
- **Production**: P1V2 Premium ($73/month) - Better performance
- **High Traffic**: P2V2 Premium ($146/month) - Optimal for scale

### Cost Optimization Tips
1. Use "Scale down" during off-hours
2. Monitor API usage with Application Insights
3. Set up budget alerts in Azure

## Next Steps

1. ✅ Verify deployment works
2. ⬜ Set up custom domain (optional)
3. ⬜ Configure SSL certificate
4. ⬜ Enable Application Insights monitoring
5. ⬜ Set up staging slots for zero-downtime deployments
6. ⬜ Configure autoscaling rules

## Support

If deployment still fails:
1. Check Azure Portal logs
2. Verify all environment variables are set
3. Ensure Python 3.12 is selected in Azure
4. Confirm startup command is configured correctly
5. Review GitHub Actions logs for build errors

## References
- [Azure App Service Python documentation](https://docs.microsoft.com/en-us/azure/app-service/quickstart-python)
- [FastAPI deployment guide](https://fastapi.tiangolo.com/deployment/)
- [Troubleshooting Azure App Service](https://docs.microsoft.com/en-us/azure/app-service/troubleshoot-diagnostic-logs)
