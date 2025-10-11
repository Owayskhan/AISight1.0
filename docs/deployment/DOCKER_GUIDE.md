# Docker Deployment Guide

## 📦 Dockerfile Review - Changes Made

### ✅ **Fixed Issues**

1. **Requirements Path**: Changed from `api/requirements.txt` → `requirements.txt` (root level)
2. **File Copy Order**: Now copies only necessary directories (`api/` and `core/`)
3. **Added curl**: Required for health checks
4. **Optimized Layers**: Combined RUN commands to reduce image size
5. **Better Health Check**: Increased start period to 40s for cold start

### 📁 **File Structure in Container**

```
/app/
├── requirements.txt          # Copied from root
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   └── test_api.py
└── core/
    ├── __init__.py
    ├── config.py
    ├── models/
    ├── queries/
    ├── citation_counter/
    └── ... (other modules)
```

### 🔧 **Dockerfile Changes**

#### Before (Issues):
```dockerfile
COPY api/requirements.txt /app/requirements.txt  # ❌ Wrong path
COPY . /app/                                     # ❌ Copies everything
```

#### After (Fixed):
```dockerfile
COPY requirements.txt .                          # ✅ Correct path
COPY api/ ./api/                                 # ✅ Only api code
COPY core/ ./core/                               # ✅ Only core code
```

## 🚀 Build and Run

### Option 1: Docker Compose (Recommended)

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f citation-api

# Stop
docker-compose down
```

### Option 2: Docker Commands

```bash
# Build image
docker build -t aisight-api:latest .

# Run container
docker run -d \
  --name aisight-api \
  -p 8000:8000 \
  --env-file .env \
  aisight-api:latest

# View logs
docker logs -f aisight-api

# Stop and remove
docker stop aisight-api && docker rm aisight-api
```

## 🧪 Test the Container

### 1. Health Check
```bash
curl http://localhost:8000/
```

**Expected Response:**
```json
{
  "message": "Citation Count API",
  "endpoints": ["/analyze"]
}
```

### 2. Check Container Status
```bash
docker ps
```

Should show `healthy` status after ~40 seconds.

### 3. View Logs
```bash
docker logs aisight-api
```

**Expected Log Output:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🔍 Verify Build

### Check Image Size
```bash
docker images aisight-api
```

**Expected**: ~1.5-2 GB (slim Python + dependencies)

### Inspect Container
```bash
# Check file structure
docker exec -it aisight-api ls -la /app/

# Verify imports work
docker exec -it aisight-api python -c "from api.main import app; print('✅ Imports OK')"

# Check Python packages
docker exec -it aisight-api pip list | grep -E "(fastapi|pydantic|langchain)"
```

## 🐛 Troubleshooting

### Issue: "No such file or directory: requirements.txt"
**Solution**: Ensure requirements.txt exists at root level (not just in api/)
```bash
ls -la requirements.txt  # Should exist
```

### Issue: "ModuleNotFoundError: No module named 'api'"
**Solution**: Check PYTHONPATH is set to `/app`
```bash
docker exec -it aisight-api echo $PYTHONPATH
# Should output: /app
```

### Issue: "ModuleNotFoundError: No module named 'core'"
**Solution**: Verify core/ directory was copied
```bash
docker exec -it aisight-api ls -la /app/core/
# Should show all core modules
```

### Issue: Container exits immediately
**Solution**: Check logs for errors
```bash
docker logs aisight-api
```

### Issue: Health check fails
**Solution**:
1. Increase `start-period` in Dockerfile (already set to 40s)
2. Check if port 8000 is accessible inside container:
```bash
docker exec -it aisight-api curl -f http://localhost:8000/
```

## 📊 Performance Tips

### 1. Multi-stage Build (Optional Optimization)
For production, you can use multi-stage builds to reduce image size:

```dockerfile
FROM python:3.12-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY api/ ./api/
COPY core/ ./core/
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Layer Caching
- Keep `COPY requirements.txt` **before** `COPY api/` and `COPY core/`
- This ensures dependencies only rebuild when requirements.txt changes

### 3. Resource Limits
Add to docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

## 🔐 Security Notes

1. ✅ **Non-root user**: Container runs as `appuser` (not root)
2. ✅ **No .env in image**: .env excluded via .dockerignore
3. ✅ **Minimal base image**: Uses `python:3.12-slim`
4. ⚠️ **Environment variables**: Pass via `--env-file` or docker-compose

## 🌐 Deploy to Cloud

### Deploy to Azure Container Instances
```bash
# Build and push to Azure Container Registry
az acr build --registry <your-acr> --image aisight-api:latest .

# Deploy to ACI
az container create \
  --resource-group aisight-rg \
  --name aisight-api \
  --image <your-acr>.azurecr.io/aisight-api:latest \
  --cpu 2 --memory 4 \
  --ports 8000 \
  --environment-variables \
    OPENAI_API_KEY=$OPENAI_API_KEY \
    PINECONE_API_KEY=$PINECONE_API_KEY
```

### Deploy to Docker Hub
```bash
# Tag and push
docker tag aisight-api:latest yourusername/aisight-api:latest
docker push yourusername/aisight-api:latest
```

## ✅ Verification Checklist

- [ ] Dockerfile builds without errors
- [ ] Container starts successfully
- [ ] Health check passes after 40s
- [ ] API responds to `curl http://localhost:8000/`
- [ ] All imports work inside container
- [ ] Environment variables are properly loaded
- [ ] No sensitive files (.env) in container image

## 📚 Next Steps

1. ✅ Build and test locally with docker-compose
2. ⬜ Set up CI/CD pipeline to build Docker images
3. ⬜ Push to container registry (ACR, Docker Hub, etc.)
4. ⬜ Deploy to cloud container service
5. ⬜ Set up monitoring and logging

---

**Ready to build? Run:** `docker-compose up --build` 🚀
