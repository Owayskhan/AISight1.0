# 📚 AISight Documentation Index

Quick reference for all documentation in this project.

## 📁 Project Structure

```
AISight1.0/
├── README.md                      # Main project overview
├── API_DOCUMENTATION.md           # Complete API reference
│
├── docs/
│   ├── README.md                  # Documentation index
│   │
│   ├── Core Documentation
│   │   ├── citation-analysis-system.md
│   │   └── citation-calculation-methodology.md
│   │
│   ├── deployment/                # Deployment guides
│   │   ├── DOCKER_QUICK_START.md         ⭐ Recommended
│   │   ├── DOCKER_GUIDE.md
│   │   ├── AZURE_DEPLOYMENT.md
│   │   └── DEPLOY_NOW.md
│   │
│   └── fixes/                     # Technical fixes documentation
│       ├── PINECONE_SESSION_FIX.md
│       └── FIRECRAWL_INTEGRATION.md
```

---

## 🚀 Quick Links

### Getting Started
- **[Main README](README.md)** - Start here!
- **[API Documentation](API_DOCUMENTATION.md)** - API endpoints and usage

### Deployment
- **[Docker Quick Start](docs/deployment/DOCKER_QUICK_START.md)** ⭐ **Recommended**
- [Docker Detailed Guide](docs/deployment/DOCKER_GUIDE.md)
- [Azure Deployment](docs/deployment/AZURE_DEPLOYMENT.md)
- [Azure Quick Deploy](docs/deployment/DEPLOY_NOW.md)

### System Design
- [Citation Analysis System](docs/citation-analysis-system.md)
- [Citation Calculation Methodology](docs/citation-calculation-methodology.md)

### Technical Reference
- [Pinecone Session Fix](docs/fixes/PINECONE_SESSION_FIX.md) - Fixed "Session is closed" errors
- [Firecrawl Integration](docs/fixes/FIRECRAWL_INTEGRATION.md) - Improved sitemap discovery

---

## 🎯 Common Tasks

### I want to...

**Run the API locally**
→ See [README.md](README.md#getting-started)

**Deploy with Docker**
→ See [DOCKER_QUICK_START.md](docs/deployment/DOCKER_QUICK_START.md)

**Deploy to Azure**
→ See [DEPLOY_NOW.md](docs/deployment/DEPLOY_NOW.md)

**Understand the API**
→ See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

**Debug Pinecone errors**
→ See [PINECONE_SESSION_FIX.md](docs/fixes/PINECONE_SESSION_FIX.md)

**Understand citation calculation**
→ See [citation-calculation-methodology.md](docs/citation-calculation-methodology.md)

---

## 📝 Documentation Organization

### Root Level
- **README.md** - Main project documentation
- **API_DOCUMENTATION.md** - API reference
- **This file** - Documentation index

### `/docs` folder
- **Core system documentation** - Architecture and methodology
- **`/deployment`** - All deployment guides (Docker, Azure, etc.)
- **`/fixes`** - Technical fixes and improvements documentation

---

**All documentation is kept in `/docs` to keep the project root clean!**
