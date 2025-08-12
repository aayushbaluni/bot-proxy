#!/bin/bash

# EC2 Setup Script for Proxy Bot
echo "🚀 Setting up Proxy Bot on EC2..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
echo "🐍 Installing Python 3.10+..."
sudo apt install -y python3.10 python3.10-pip python3.10-venv

# Install MongoDB
echo "🍃 Installing MongoDB..."
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start and enable MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Install Node.js and npm (for PM2)
echo "📦 Installing Node.js and npm..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 globally
echo "⚡ Installing PM2..."
sudo npm install -g pm2

# Create project directory
echo "📁 Setting up project directory..."
mkdir -p /home/ubuntu/proxy-bot
cd /home/ubuntu/proxy-bot

# Create logs directory
mkdir -p logs

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cat > requirements.txt << EOF
pymongo==4.6.0
requests==2.31.0
aiohttp==3.9.1
asyncio
argparse
EOF

python3.10 -m pip install --user -r requirements.txt

# Create systemd service for MongoDB (if not already created)
echo "🔧 Configuring MongoDB service..."
sudo systemctl daemon-reload

# Setup PM2 to start on boot
echo "🚀 Setting up PM2 startup..."
sudo pm2 startup systemd -u ubuntu --hp /home/ubuntu

echo "✅ EC2 setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Upload your main.py and ecosystem.config.js files to /home/ubuntu/proxy-bot/"
echo "2. Start the proxy bot with: pm2 start ecosystem.config.js"
echo "3. Save PM2 configuration: pm2 save"
echo "4. Check status with: pm2 status"
echo "5. View logs with: pm2 logs"
echo ""
echo "🔧 Useful PM2 commands:"
echo "   pm2 start ecosystem.config.js --only proxy-bot-auto"
echo "   pm2 stop proxy-bot-auto"
echo "   pm2 restart proxy-bot-auto"
echo "   pm2 logs proxy-bot-auto"
echo "   pm2 monit"