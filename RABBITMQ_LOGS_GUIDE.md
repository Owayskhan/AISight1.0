# RabbitMQ Container Logs Guide

## 🐰 Your RabbitMQ Container

**Container Name:** `sola-rabbitmq`
**Image:** `rabbitmq:3-management`
**Ports:**
- `5672` - AMQP protocol (message broker)
- `15672` - Management UI (Web interface)

---

## 📋 Quick Reference: Accessing RabbitMQ Logs

### Method 1: View Logs from Host (Recommended)

```bash
# View live logs (tail -f style)
docker logs -f sola-rabbitmq

# View last 100 lines
docker logs --tail 100 sola-rabbitmq

# View logs since 1 hour ago
docker logs --since 1h sola-rabbitmq

# View logs with timestamps
docker logs -t sola-rabbitmq

# Save logs to file
docker logs sola-rabbitmq > rabbitmq-logs.txt
```

### Method 2: Access Logs Inside Container

```bash
# Enter the container
docker exec -it sola-rabbitmq bash

# Once inside, view logs
tail -f /var/log/rabbitmq/*.log

# View specific log files
cat /var/log/rabbitmq/rabbit@*.log
```

### Method 3: RabbitMQ Management UI (Visual)

```bash
# Access via browser
open http://localhost:15672

# Default credentials (unless changed):
# Username: guest
# Password: guest

# Navigate to: Admin → Server → Log files
```

---

## 📁 RabbitMQ Log File Locations

### Inside the Container:

```bash
/var/log/rabbitmq/
├── rabbit@hostname.log           # Main log file
├── rabbit@hostname-sasl.log      # SASL (authentication) logs
└── rabbit@hostname_upgrade.log   # Upgrade logs (if applicable)
```

### Common Log Locations:

| Log Type | Path |
|----------|------|
| **Main Log** | `/var/log/rabbitmq/rabbit@*.log` |
| **SASL/Auth** | `/var/log/rabbitmq/rabbit@*-sasl.log` |
| **Startup** | First entries in main log |
| **Errors** | Search for `ERROR` or `CRASH` in main log |

---

## 🔍 Useful Log Commands

### 1. Monitor Live Logs

```bash
# Live tail (most common)
docker logs -f sola-rabbitmq

# Follow with grep filter
docker logs -f sola-rabbitmq | grep ERROR

# Follow multiple patterns
docker logs -f sola-rabbitmq | grep -E "ERROR|WARNING|CRASH"
```

### 2. Search Logs

```bash
# Search for errors in last 1000 lines
docker logs --tail 1000 sola-rabbitmq | grep -i error

# Search for connection issues
docker logs sola-rabbitmq | grep -i "connection"

# Search for specific queue
docker logs sola-rabbitmq | grep -i "queue_name"

# Search for authentication failures
docker logs sola-rabbitmq | grep -i "auth"
```

### 3. Extract Logs by Time

```bash
# Logs from last hour
docker logs --since 1h sola-rabbitmq

# Logs from last 30 minutes
docker logs --since 30m sola-rabbitmq

# Logs between specific times
docker logs --since 2024-01-15T10:00:00 --until 2024-01-15T11:00:00 sola-rabbitmq

# Today's logs
docker logs --since $(date -d 'today 00:00' -Iseconds) sola-rabbitmq
```

### 4. Inside Container Log Commands

```bash
# Enter container
docker exec -it sola-rabbitmq bash

# View all RabbitMQ logs
ls -lah /var/log/rabbitmq/

# Tail main log
tail -f /var/log/rabbitmq/rabbit@*.log

# Search for errors
grep -i error /var/log/rabbitmq/rabbit@*.log

# View last 50 lines
tail -n 50 /var/log/rabbitmq/rabbit@*.log

# View logs with pagination
less /var/log/rabbitmq/rabbit@*.log
```

---

## 🛠️ Troubleshooting Common Issues

### Issue 1: Can't Find Log Files

```bash
# Check RabbitMQ status
docker exec sola-rabbitmq rabbitmqctl status

# Check RabbitMQ environment
docker exec sola-rabbitmq rabbitmqctl environment

# Find log directory
docker exec sola-rabbitmq rabbitmqctl eval 'rabbit:log_locations().'
```

### Issue 2: Logs Not Updating

```bash
# Check if RabbitMQ is running
docker exec sola-rabbitmq rabbitmqctl ping

# Restart RabbitMQ (service only, not container)
docker exec sola-rabbitmq rabbitmqctl stop_app
docker exec sola-rabbitmq rabbitmqctl start_app

# Restart container (if needed)
docker restart sola-rabbitmq
```

### Issue 3: Too Many Logs (Performance)

```bash
# Rotate logs manually
docker exec sola-rabbitmq rabbitmqctl rotate_logs

# Check log size
docker exec sola-rabbitmq du -sh /var/log/rabbitmq/

# Clear old logs (careful!)
docker exec sola-rabbitmq find /var/log/rabbitmq/ -name "*.log.*" -delete
```

---

## 📊 RabbitMQ Management UI (Web Dashboard)

### Access the Dashboard

```bash
# Open in browser
http://localhost:15672

# Or with curl
curl -u guest:guest http://localhost:15672/api/overview
```

### View Logs in UI

1. **Login** → `http://localhost:15672`
2. **Navigate** → Top menu: "Admin"
3. **Select** → "Server" section
4. **View** → "Log file" tab

**Features:**
- ✅ Real-time log viewer
- ✅ Download logs
- ✅ Filter by severity
- ✅ Search within logs

---

## 🔧 Advanced: Log Configuration

### Check Current Log Configuration

```bash
# View RabbitMQ configuration
docker exec sola-rabbitmq cat /etc/rabbitmq/rabbitmq.conf

# View environment variables
docker exec sola-rabbitmq env | grep RABBITMQ
```

### Increase Log Detail (Debugging)

```bash
# Set log level to debug (temporary)
docker exec sola-rabbitmq rabbitmqctl set_log_level debug

# Back to info level
docker exec sola-rabbitmq rabbitmqctl set_log_level info
```

### Mount Logs to Host (Persistent)

If you want logs accessible from host filesystem:

```bash
# Stop container
docker stop sola-rabbitmq

# Restart with volume mount
docker run -d \
  --name sola-rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -v /path/on/host/rabbitmq-logs:/var/log/rabbitmq \
  rabbitmq:3-management

# Now logs are at: /path/on/host/rabbitmq-logs
```

---

## 📝 Useful Log Patterns

### Connection Issues

```bash
# Find connection errors
docker logs sola-rabbitmq | grep -E "connection|refused|closed"

# Authentication failures
docker logs sola-rabbitmq | grep -i "auth.*failed"

# Network errors
docker logs sola-rabbitmq | grep -E "timeout|unreachable"
```

### Performance Issues

```bash
# Memory warnings
docker logs sola-rabbitmq | grep -i "memory"

# Disk space warnings
docker logs sola-rabbitmq | grep -i "disk"

# Queue overload
docker logs sola-rabbitmq | grep -i "queue.*full"
```

### Message Issues

```bash
# Message delivery failures
docker logs sola-rabbitmq | grep -E "delivery|reject|nack"

# Dead letter queue activity
docker logs sola-rabbitmq | grep -i "dead.letter"

# Unroutable messages
docker logs sola-rabbitmq | grep -i "unroutable"
```

---

## 🚀 Quick Diagnostic Script

Save this as `check-rabbitmq-logs.sh`:

```bash
#!/bin/bash

CONTAINER="sola-rabbitmq"

echo "=== RabbitMQ Container Status ==="
docker ps --filter "name=$CONTAINER"

echo -e "\n=== Last 20 Log Lines ==="
docker logs --tail 20 $CONTAINER

echo -e "\n=== Recent Errors ==="
docker logs --tail 100 $CONTAINER | grep -i error || echo "No errors found"

echo -e "\n=== Recent Warnings ==="
docker logs --tail 100 $CONTAINER | grep -i warning || echo "No warnings found"

echo -e "\n=== Connection Activity (last 10) ==="
docker logs --tail 100 $CONTAINER | grep -i connection | tail -10

echo -e "\n=== Log Files Inside Container ==="
docker exec $CONTAINER ls -lh /var/log/rabbitmq/

echo -e "\n=== RabbitMQ Status ==="
docker exec $CONTAINER rabbitmqctl status | head -20

echo -e "\n=== Queues ==="
docker exec $CONTAINER rabbitmqctl list_queues name messages consumers

echo -e "\n=== Connections ==="
docker exec $CONTAINER rabbitmqctl list_connections name peer_host peer_port state
```

**Usage:**
```bash
chmod +x check-rabbitmq-logs.sh
./check-rabbitmq-logs.sh
```

---

## 🎯 Quick Commands Cheat Sheet

```bash
# === LIVE MONITORING ===
docker logs -f sola-rabbitmq                    # Follow live logs
docker logs -f --tail 100 sola-rabbitmq         # Follow last 100 lines

# === SEARCH & FILTER ===
docker logs sola-rabbitmq | grep ERROR          # Find errors
docker logs sola-rabbitmq | grep -i connection  # Find connections
docker logs --since 1h sola-rabbitmq            # Last hour only

# === INSIDE CONTAINER ===
docker exec -it sola-rabbitmq bash              # Enter container
tail -f /var/log/rabbitmq/*.log                 # Tail logs inside
grep ERROR /var/log/rabbitmq/*.log              # Search inside

# === MANAGEMENT ===
docker exec sola-rabbitmq rabbitmqctl status    # Check status
docker exec sola-rabbitmq rabbitmqctl list_queues  # List queues
open http://localhost:15672                     # Open UI

# === EXPORT ===
docker logs sola-rabbitmq > rabbitmq.log        # Save to file
docker exec sola-rabbitmq tar czf /tmp/logs.tar.gz /var/log/rabbitmq  # Archive logs
docker cp sola-rabbitmq:/tmp/logs.tar.gz .      # Copy to host
```

---

## 📚 Additional Resources

- **RabbitMQ Logging Docs**: https://www.rabbitmq.com/logging.html
- **Docker Logs Docs**: https://docs.docker.com/engine/reference/commandline/logs/
- **Management Plugin**: https://www.rabbitmq.com/management.html

---

## ⚡ TL;DR - Most Common Commands

```bash
# View live logs
docker logs -f sola-rabbitmq

# View recent errors
docker logs --tail 100 sola-rabbitmq | grep -i error

# Access container shell
docker exec -it sola-rabbitmq bash

# View logs inside container
docker exec -it sola-rabbitmq tail -f /var/log/rabbitmq/rabbit@*.log

# Check RabbitMQ status
docker exec sola-rabbitmq rabbitmqctl status

# Access web UI
http://localhost:15672 (guest/guest)
```

---

**Need Help?** Check your container logs with:
```bash
docker logs -f sola-rabbitmq
```
