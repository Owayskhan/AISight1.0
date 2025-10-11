# AISight Documentation

## 📚 Documentation Index

### Core Documentation
- [Citation Analysis System](citation-analysis-system.md) - System architecture and design
- [Citation Calculation Methodology](citation-calculation-methodology.md) - How citations are calculated

### API Documentation
- [API Documentation](../API_DOCUMENTATION.md) - Complete API reference

### Deployment Guides
- [Docker Quick Start](deployment/DOCKER_QUICK_START.md) - Fast Docker deployment (recommended)
- [Docker Detailed Guide](deployment/DOCKER_GUIDE.md) - Comprehensive Docker guide
- [Azure Deployment Guide](deployment/AZURE_DEPLOYMENT.md) - Full Azure App Service guide
- [Azure Quick Deploy](deployment/DEPLOY_NOW.md) - Quick Azure deployment steps

### Technical Fixes & Improvements
- [Pinecone Session Fix](fixes/PINECONE_SESSION_FIX.md) - Fixed "Session is closed" errors
- [Firecrawl Integration](fixes/FIRECRAWL_INTEGRATION.md) - Sitemap discovery improvement

---

## 🚀 Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd AISight1.0
   cp .env.example .env  # Add your API keys
   ```

2. **Run with Docker** (easiest):
   ```bash
   docker build -t aisight-api .
   docker run -p 8000:8000 --env-file .env aisight-api
   ```

3. **Or run locally**:
   ```bash
   pip install -r requirements.txt
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

4. **Test**:
   ```bash
   curl http://localhost:8000/
   ```

---

See [Main README](../README.md) for more details.
