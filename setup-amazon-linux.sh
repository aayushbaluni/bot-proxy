#!/bin/bash

# Amazon Linux EC2 Setup Script for Proxy Bot
echo "🚀 Setting up Proxy Bot on Amazon Linux EC2..."

# Update system
echo "📦 Updating system packages..."
sudo yum update -y

# Install Python 3.11 and pip
echo "🐍 Installing Python 3.11+..."
sudo yum install -y python3 python3-pip python3-devel

# Create MongoDB repository file
echo "🍃 Setting up MongoDB repository..."
sudo tee /etc/yum.repos.d/mongodb-org-7.0.repo << 'EOF'
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc
EOF

# Install MongoDB
echo "🍃 Installing MongoDB..."
sudo yum install -y mongodb-org

# Start and enable MongoDB
echo "🍃 Starting MongoDB service..."
sudo systemctl start mongod
sudo systemctl enable mongod

# Check MongoDB status
echo "🍃 Checking MongoDB status..."
sudo systemctl status mongod --no-pager

# Install Node.js and npm
echo "📦 Installing Node.js and npm..."
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Install PM2 globally
echo "⚡ Installing PM2..."
sudo npm install -g pm2

# Create project directory with correct permissions
echo "📁 Setting up project directory..."
mkdir -p /home/ec2-user/proxy-bot
cd /home/ec2-user/proxy-bot

# Create logs directory
mkdir -p logs

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cat > requirements.txt << EOF
pymongo==4.6.0
requests==2.31.0
aiohttp==3.9.1
asyncio
EOF

python3 -m pip install --user -r requirements.txt

# Setup PM2 to start on boot for ec2-user
echo "🚀 Setting up PM2 startup..."
sudo pm2 startup systemd -u ec2-user --hp /home/ec2-user

# Set correct ownership
sudo chown -R ec2-user:ec2-user /home/ec2-user/proxy-bot

echo ""
echo "✅ Amazon Linux EC2 setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Upload your main.py and ecosystem.config.js files to /home/ec2-user/proxy-bot/"
echo "2. Start the proxy bot with: pm2 start ecosystem.config.js --only proxy-bot-sequential-10min"
echo "3. Save PM2 configuration: pm2 save"
echo "4. Check status with: pm2 status"
echo "5. View logs with: pm2 logs"
echo ""
echo "🔧 Upload files command (run from your local machine):"
echo "   scp -i your-key.pem main.py ecosystem.config.js ubuntu@your-ec2-ip:/home/ec2-user/proxy-bot/"
echo ""
echo "🔧 Useful PM2 commands:"
echo "   pm2 start ecosystem.config.js --only proxy-bot-sequential-10min"
echo "   pm2 stop proxy-bot-sequential-10min"
echo "   pm2 restart proxy-bot-sequential-10min"
echo "   pm2 logs proxy-bot-sequential-10min"
echo "   pm2 monit"
echo ""
echo "🔧 Test MongoDB:"
echo "   mongosh --eval 'db.runCommand({hello: 1})'"