# Quick Fix for Amazon Linux EC2

Since you're already on the EC2 instance, here are the manual commands to complete the setup:

## 1. Install Missing Dependencies

```bash
# Update system
sudo yum update -y

# Install Python 3 and pip
sudo yum install -y python3 python3-pip python3-devel

# Create MongoDB repository
sudo tee /etc/yum.repos.d/mongodb-org-7.0.repo << 'EOF'
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc
EOF

# Install MongoDB
sudo yum install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

## 2. Create Project Directory

```bash
# Create directory in ec2-user home (not ubuntu)
mkdir -p /home/ec2-user/proxy-bot
cd /home/ec2-user/proxy-bot
mkdir -p logs

# Install Python dependencies
python3 -m pip install --user pymongo==4.6.0 requests==2.31.0 aiohttp==3.9.1
```

## 3. Upload Files

**From your local machine:**
```bash
# Note: Use ec2-user instead of ubuntu for Amazon Linux
scp -i your-key.pem main.py ecosystem.config.js requirements.txt ec2-user@your-ec2-ip:/home/ec2-user/proxy-bot/
```

## 4. Start the Bot

**Back on EC2:**
```bash
cd /home/ec2-user/proxy-bot

# Start the 10-minute sequential process
pm2 start ecosystem.config.js --only proxy-bot-sequential-10min

# Save PM2 config
pm2 save

# Check status
pm2 status
```

## 5. Monitor

```bash
# View real-time logs
pm2 logs proxy-bot-sequential-10min

# Monitor system
pm2 monit
```

## Test MongoDB Connection

```bash
# Test if MongoDB is working
mongosh --eval 'db.runCommand({hello: 1})'
```

If you get connection errors, MongoDB might need a restart:
```bash
sudo systemctl restart mongod
sudo systemctl status mongod
```