# Proxy Bot - Automated Proxy Harvesting & Testing System

A comprehensive proxy bot that automatically harvests proxies from multiple sources, validates them, and tests them against target endpoints at configurable intervals.

## Features

- 🔄 **Automated Proxy Harvesting**: Fetches proxies from multiple free sources
- ✅ **Real-time Validation**: Tests proxy functionality with threading
- 🗄️ **MongoDB Storage**: Stores only working proxies with deduplication
- 🎯 **Endpoint Testing**: Tests proxies against specific endpoints
- ⏰ **Scheduled Operations**: Configurable intervals for harvesting and testing
- 🚀 **PM2 Ready**: Production-ready with PM2 process management
- ☁️ **EC2 Optimized**: Easy deployment on AWS EC2

## Quick Start

### Local Usage

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start MongoDB** (if not running):
   ```bash
   # macOS with Homebrew
   brew services start mongodb-community
   
   # Ubuntu/Debian
   sudo systemctl start mongod
   ```

3. **Run commands**:
   ```bash
   # Harvest proxies once
   python main.py --harvest
   
   # Test proxies against endpoint once  
   python main.py --test-endpoint
   
   # Run sequential system (harvest → test → wait → repeat) - RECOMMENDED FOR EC2
   python main.py --sequential --cycle-interval 10
   
   # Run automated system (separate intervals)
   python main.py --auto --fetch-interval 120 --test-interval 15
   ```

## Command Reference

| Command | Description |
|---------|-------------|
| `--harvest` | Run single proxy harvest/validation cycle |
| `--test-endpoint` | Test all working proxies against target endpoint |
| `--sequential` | **Run sequential mode: harvest → test → wait → repeat (RECOMMENDED)** |
| `--cycle-interval N` | Minutes between each harvest+test cycle (default: 10) |
| `--auto` | Run automated system with separate fetch and test intervals |
| `--fetch-interval N` | Minutes between proxy harvesting (default: 60) |
| `--test-interval N` | Minutes between endpoint testing (default: 30) |
| `--endpoint URL` | Custom endpoint to test (default: http://16.171.170.83:3000/) |
| `--stats` | Show current proxy database statistics |

## EC2 Deployment Guide

### 1. Launch EC2 Instance

- **Instance Type**: t3.medium or larger (recommended)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20GB+ SSD
- **Security Group**: Allow SSH (port 22)

### 2. Setup EC2 Environment

```bash
# Upload setup script
scp -i your-key.pem setup-ec2.sh ubuntu@your-ec2-ip:/home/ubuntu/

# Connect to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Run setup script
chmod +x setup-ec2.sh
./setup-ec2.sh
```

### 3. Upload Project Files

```bash
# From your local machine
scp -i your-key.pem main.py ecosystem.config.js requirements.txt ubuntu@your-ec2-ip:/home/ubuntu/proxy-bot/
```

### 4. Start with PM2

```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Navigate to project directory
cd /home/ubuntu/proxy-bot

# Start the 10-minute sequential process (RECOMMENDED)
pm2 start ecosystem.config.js --only proxy-bot-sequential-10min

# Save PM2 configuration for auto-restart on reboot
pm2 save

# Check status
pm2 status
```

## PM2 Process Management

### Available PM2 Configurations

1. **proxy-bot-sequential-10min**: Sequential mode (harvest → test every 10 minutes) - **RECOMMENDED**
2. **proxy-bot-sequential-5min**: Sequential mode (harvest → test every 5 minutes) - Fast mode
3. **proxy-bot-auto**: Automated system with separate intervals (harvest every 60min, test every 30min)

### PM2 Commands

```bash
# Start specific process
pm2 start ecosystem.config.js --only proxy-bot-sequential-10min

# View all processes
pm2 status

# View logs
pm2 logs proxy-bot-sequential-10min

# Monitor in real-time
pm2 monit

# Restart process
pm2 restart proxy-bot-sequential-10min

# Stop process
pm2 stop proxy-bot-sequential-10min

# Delete process
pm2 delete proxy-bot-sequential-10min

# View detailed info
pm2 show proxy-bot-sequential-10min
```

## Configuration

### Environment Variables (Optional)

```bash
export MONGO_URI="mongodb://localhost:27017"
export DB_NAME="proxydb"
export TARGET_ENDPOINT="http://your-endpoint.com/"
```

### Customizing Intervals

Edit `ecosystem.config.js` to change intervals:

```javascript
args: '--auto --fetch-interval 90 --test-interval 20'
```

## Monitoring & Logs

### Log Files (PM2)
- **Combined**: `./logs/proxy-bot-combined.log`
- **Output**: `./logs/proxy-bot-out.log`  
- **Errors**: `./logs/proxy-bot-error.log`

### Database Monitoring

```bash
# Check proxy statistics
python main.py --stats

# MongoDB shell
mongo
use proxydb
db.working_proxies.count()
db.working_proxies.find({"is_working": true}).count()
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**:
   ```bash
   sudo systemctl start mongod
   sudo systemctl status mongod
   ```

2. **Python Dependencies**:
   ```bash
   python3.10 -m pip install --user -r requirements.txt
   ```

3. **PM2 Process Not Starting**:
   ```bash
   pm2 logs proxy-bot-auto
   pm2 describe proxy-bot-auto
   ```

4. **Memory Issues**:
   - Increase EC2 instance size
   - Adjust `max_memory_restart` in ecosystem.config.js

### Performance Tuning

- **Fetch Interval**: Longer intervals (60-120min) for stability
- **Test Interval**: Shorter intervals (15-30min) for fresh data
- **Thread Workers**: Adjust `max_workers` in code based on EC2 instance size

## API Response Example

When testing the endpoint, you'll see responses like:

```json
{
  "message": "Welcome to the Proxy Counter Bot!",
  "yourIP": "::ffff:14.97.86.130", 
  "totalRequestsFromYourIP": 1859,
  "endpoints": {
    "stats": "/stats",
    "history": "/history", 
    "reset": "/reset (POST)"
  }
}
```

Each proxy will show a different `yourIP`, confirming successful IP rotation.

## License

MIT License - Feel free to modify and distribute.