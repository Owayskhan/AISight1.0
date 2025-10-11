# Docker Quick Start

## Build
```bash
docker build -t aisight-api .
```

## Run
```bash
docker run -d -p 8000:8000 --env-file .env --name aisight-api aisight-api
```

## Test
```bash
curl http://localhost:8000/
```

## View Logs
```bash
docker logs -f aisight-api
```

## Stop
```bash
docker stop aisight-api && docker rm aisight-api
```

## Structure in Container
```
/app/
├── requirements.txt
├── api/
│   └── main.py
└── core/
    └── (all modules)
```

That's it! Simple and works.
