# EC2 Deployment Guide - Complete Setup Instructions

## Overview
This guide provides step-by-step instructions for deploying the AI Agent QA system to an EC2 instance. It covers initial setup, code deployment, service configuration, and ongoing maintenance.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [EC2 Instance Setup](#ec2-instance-setup)
3. [Initial Server Configuration](#initial-server-configuration)
4. [Code Deployment](#code-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Service Management](#service-management)
7. [Verification & Testing](#verification--testing)
8. [Common Operations](#common-operations)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Prerequisites

### Required Accounts & Access
- **AWS Account** with EC2 access
- **EC2 Instance** running Ubuntu (tested on Ubuntu 22.04 LTS)
- **SSH Key Pair** (.pem file) for EC2 access
- **GitHub Access** to repository

### Required Software (Local Machine)
- **Git** - Version control
- **SSH Client** - For connecting to EC2
- **Python 3.8+** - For local development (optional)
- **Node.js & npm** - For TypeScript test execution (installed on server)

### Required Information
- **EC2 Instance IP**: `13.222.91.163` (current production)
- **EC2 User**: `ubuntu`
- **SSH Key Path**: `~/Downloads/ai-crdc-hub-key.pem` (adjust as needed)
- **Project Path on Server**: `~/DATAHUB_AI_Agent`
- **GitHub Repository**: `https://github.com/laxmilolla/DATAHUB_AI_Agent.git`

---

## EC2 Instance Setup

### 1. Launch EC2 Instance

**Recommended Instance Type**: `t3.medium` or larger
- Minimum: 2 vCPU, 4 GB RAM
- Recommended: 4 vCPU, 8 GB RAM (for Playwright tests)

**Security Group Configuration**:
- **Inbound Rules**:
  - SSH (22): Your IP only
  - HTTP (80): 0.0.0.0/0 (if using reverse proxy)
  - Custom TCP (5000): Your IP or specific IPs (Flask API)
- **Outbound Rules**: All traffic (for AWS API calls, npm installs)

### 2. Connect to EC2 Instance

```bash
# Set correct permissions on SSH key
chmod 400 ~/Downloads/ai-crdc-hub-key.pem

# Connect to EC2
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163
```

---

## Initial Server Configuration

### 1. Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Required System Packages

```bash
# Python and build tools
sudo apt install -y python3 python3-pip python3-venv git curl

# Node.js and npm (for TypeScript Playwright tests)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
python3 --version  # Should be 3.8+
node --version     # Should be 18.x+
npm --version      # Should be 9.x+
```

### 3. Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/laxmilolla/DATAHUB_AI_Agent.git
cd DATAHUB_AI_Agent
```

### 4. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 5. Install Python Dependencies

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Verify key packages
pip list | grep -E "flask|playwright|boto3|pandas|openpyxl"
```

### 6. Install Playwright Browsers

```bash
# Install Playwright browsers (required for test execution)
npx playwright install chromium
npx playwright install-deps chromium
```

---

## Environment Configuration

### 1. Create .env File

```bash
cd ~/DATAHUB_AI_Agent

# Create .env file
nano .env
```

### 2. Required Environment Variables

Add the following to `.env`:

```bash
# AWS Credentials (for Bedrock/Claude)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# LLM Provider
LLM_PROVIDER=bedrock

# Flask Configuration
FLASK_APP=api/app.py
FLASK_ENV=production
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000

# Project Root (auto-detected, but can be set)
PROJECT_ROOT=/home/ubuntu/DATAHUB_AI_Agent

# TOTP Secret Keys (for two-factor authentication)
TOTP_SECRET_KEY=your_totp_secret_here
TOTP_SECRET_KEY_TS=your_totp_secret_for_typescript_here

# Optional: Logging
LOG_LEVEL=INFO
```

### 3. Secure .env File

```bash
# Set restrictive permissions
chmod 600 .env

# Verify .env is git-ignored
git check-ignore .env
# Should output: .env
```

### 4. Create Required Directories

```bash
cd ~/DATAHUB_AI_Agent

# Create storage directories
mkdir -p storage/executions
mkdir -p storage/screenshots
mkdir -p storage/excel_files
mkdir -p storage/excel_files/metadata
mkdir -p storage/excel_tests
mkdir -p storage/excel_tests/storage/screenshots
mkdir -p element_maps
```

---

## Code Deployment

### Method 1: Git-Based Deployment (Recommended)

**On Local Machine**:
```bash
cd /path/to/ai-agent-qa

# Commit changes
git add .
git commit -m "Your commit message"
git push
```

**On EC2 Server**:
```bash
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163

cd ~/DATAHUB_AI_Agent
git pull

# Restart Flask (see Service Management section)
```

### Method 2: Direct File Transfer (For Quick Fixes)

**Deploy Single File**:
```bash
# From local machine
scp -i ~/Downloads/ai-crdc-hub-key.pem \
  /path/to/local/file.py \
  ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/path/to/file.py
```

**Deploy Directory**:
```bash
# From local machine
rsync -avz -e "ssh -i ~/Downloads/ai-crdc-hub-key.pem" \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='venv' \
  --exclude='node_modules' \
  /path/to/local/directory/ \
  ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/path/to/directory/
```

### Method 3: Complete Project Sync

```bash
# From local machine - sync entire project (excluding sensitive files)
rsync -avz -e "ssh -i ~/Downloads/ai-crdc-hub-key.pem" \
  --exclude='.env' \
  --exclude='venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  /path/to/ai-agent-qa/ \
  ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/
```

---

## Service Management

### Starting Flask Manually

```bash
# SSH to server
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163

cd ~/DATAHUB_AI_Agent
source venv/bin/activate
export FLASK_APP=api/app.py

# Start Flask in background
nohup python -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &

# Verify it's running
ps aux | grep flask
tail -f flask.log
```

### Stopping Flask

```bash
# Find Flask process
ps aux | grep flask | grep -v grep

# Kill Flask process
pkill -f "python.*flask" || pkill -f "python.*app.py"

# Or kill specific port
lsof -ti:5000 | xargs kill -9
```

### Restarting Flask

```bash
# Stop Flask
lsof -ti:5000 | xargs kill -9 2>/dev/null
sleep 2

# Start Flask
cd ~/DATAHUB_AI_Agent
source venv/bin/activate
export FLASK_APP=api/app.py
nohup python -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &

# Verify
sleep 3
ps aux | grep flask | grep -v grep
tail -20 flask.log
```

### Using systemd (Optional - For Production)

**Create systemd service file**:
```bash
sudo nano /etc/systemd/system/flask.service
```

**Service file content**:
```ini
[Unit]
Description=AI Agent QA Flask Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/DATAHUB_AI_Agent
Environment="PATH=/home/ubuntu/DATAHUB_AI_Agent/venv/bin"
Environment="FLASK_APP=api/app.py"
ExecStart=/home/ubuntu/DATAHUB_AI_Agent/venv/bin/python -m flask run --host=0.0.0.0 --port=5000
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/DATAHUB_AI_Agent/flask.log
StandardError=append:/home/ubuntu/DATAHUB_AI_Agent/flask.log

[Install]
WantedBy=multi-user.target
```

**Enable and start service**:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable flask

# Start service
sudo systemctl start flask

# Check status
sudo systemctl status flask

# View logs
sudo journalctl -u flask -f
```

**Service management commands**:
```bash
sudo systemctl start flask      # Start
sudo systemctl stop flask       # Stop
sudo systemctl restart flask    # Restart
sudo systemctl status flask     # Status
```

---

## Verification & Testing

### 1. Verify Flask is Running

```bash
# Check process
ps aux | grep flask | grep -v grep

# Check port
lsof -i:5000

# Check logs
tail -f ~/DATAHUB_AI_Agent/flask.log
```

### 2. Test API Endpoints

**From Local Machine**:
```bash
# Health check
curl http://13.222.91.163:5000/api/health

# Expected response:
# {"status":"healthy","architecture":"Pure Python + Playwright"}
```

**From Server**:
```bash
curl http://localhost:5000/api/health
```

### 3. Test Excel Upload

```bash
# Upload Excel file
curl -X POST http://13.222.91.163:5000/api/excel/upload \
  -F "file=@test_case.xlsx"

# Expected response includes excel_id
```

### 4. Access Web UI

Open in browser:
```
http://13.222.91.163:5000
```

---

## Common Operations

### Deploy and Restart (Quick Command)

**From Local Machine**:
```bash
# Deploy via git
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "cd ~/DATAHUB_AI_Agent && git pull && \
   lsof -ti:5000 | xargs kill -9 2>/dev/null; sleep 2; \
   source venv/bin/activate && export FLASK_APP=api/app.py && \
   nohup python -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &"
```

### Monitor Logs

```bash
# Real-time log monitoring
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "tail -f ~/DATAHUB_AI_Agent/flask.log"

# Filter for specific patterns
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "tail -f ~/DATAHUB_AI_Agent/flask.log | grep -E 'ERROR|Step|excel_exec'"
```

### Check Execution Status

```bash
# List recent executions
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "ls -lth ~/DATAHUB_AI_Agent/storage/executions/ | head -10"

# View specific execution
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "cat ~/DATAHUB_AI_Agent/storage/executions/excel_exec_20260121_180918_7b11cea5.json | python3 -m json.tool"
```

### View Screenshots

```bash
# List screenshots
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "ls -lth ~/DATAHUB_AI_Agent/storage/excel_tests/storage/screenshots/ | head -20"

# Download screenshot
scp -i ~/Downloads/ai-crdc-hub-key.pem \
  ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/storage/excel_tests/storage/screenshots/pw_step13_dropdown_failed.png \
  ~/Downloads/
```

### Update Dependencies

```bash
# Update Python packages
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 << 'EOF'
cd ~/DATAHUB_AI_Agent
source venv/bin/activate
pip install --upgrade -r requirements.txt
EOF

# Update Node.js packages (if needed)
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 << 'EOF'
cd ~/DATAHUB_AI_Agent/storage/excel_tests
npm update
EOF
```

---

## Troubleshooting

### Issue: Flask Not Starting

**Symptoms**: Process dies immediately or doesn't start

**Diagnosis**:
```bash
# Check logs
tail -50 ~/DATAHUB_AI_Agent/flask.log

# Check Python path
cd ~/DATAHUB_AI_Agent
source venv/bin/activate
python -c "import flask; print(flask.__version__)"

# Check imports
python -c "from api.app import create_app; app = create_app(); print('OK')"
```

**Common Causes**:
- Missing dependencies: `pip install -r requirements.txt`
- Wrong Python version: Use `python3` explicitly
- Missing .env file: Create `.env` with required variables
- Port already in use: `lsof -ti:5000 | xargs kill -9`

### Issue: AWS Credentials Error

**Symptoms**: `AccessDeniedException` or credential errors

**Diagnosis**:
```bash
# Check .env file
cat ~/DATAHUB_AI_Agent/.env | grep AWS

# Test AWS credentials
aws sts get-caller-identity --region us-east-1
```

**Solution**:
1. Verify AWS credentials in `.env`
2. Check IAM permissions for Bedrock access
3. Verify AWS region is correct (`us-east-1`)
4. If credentials are compromised, see `AWS_CREDENTIALS_FIX.md`

### Issue: Test Execution Fails

**Symptoms**: Tests fail with "Element not found" or timeout errors

**Diagnosis**:
```bash
# Check test file
cat ~/DATAHUB_AI_Agent/storage/excel_tests/test_excel_*.spec.ts | grep -A 5 "Step 13"

# Check registry
cat ~/DATAHUB_AI_Agent/element_maps/hub-stage.datacommons.cancer.gov/data-submissions_page.json | python3 -m json.tool | grep -A 10 "dropdown_16"

# Check screenshots
ls -lth ~/DATAHUB_AI_Agent/storage/excel_tests/storage/screenshots/ | head -10
```

**Common Causes**:
- XPath mismatch between Excel and registry
- Element not in registry
- Modal scoping issue
- Test file needs regeneration

### Issue: Port 5000 Already in Use

**Symptoms**: `Address already in use` error

**Solution**:
```bash
# Find process using port 5000
lsof -i:5000

# Kill process
lsof -ti:5000 | xargs kill -9

# Or use different port
export FLASK_RUN_PORT=5001
python -m flask run --host=0.0.0.0 --port=5001
```

### Issue: Playwright Tests Not Running

**Symptoms**: "Node.js not found" or Playwright errors

**Diagnosis**:
```bash
# Check Node.js
node --version
npm --version

# Check Playwright
npx playwright --version

# Install browsers if missing
npx playwright install chromium
```

### Issue: Git Pull Conflicts

**Symptoms**: `error: The following untracked working tree files would be overwritten`

**Solution**:
```bash
# Option 1: Reset and pull (WARNING: Discards local changes)
cd ~/DATAHUB_AI_Agent
git reset --hard
git pull

# Option 2: Stash local changes
git stash
git pull
git stash pop
```

---

## Security Considerations

### 1. SSH Key Security

```bash
# Set correct permissions
chmod 400 ~/Downloads/ai-crdc-hub-key.pem

# Never commit SSH keys to git
git check-ignore *.pem
```

### 2. Environment Variables

- **Never commit `.env` file** to git
- Use `.gitignore` to exclude `.env`
- Rotate AWS credentials regularly
- Use AWS IAM roles when possible (instead of access keys)

### 3. Firewall Configuration

```bash
# Install and configure UFW (Uncomplicated Firewall)
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow Flask (only from specific IPs if possible)
sudo ufw allow from YOUR_IP_ADDRESS to any port 5000

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 4. File Permissions

```bash
# Secure sensitive files
chmod 600 ~/DATAHUB_AI_Agent/.env
chmod 600 ~/Downloads/ai-crdc-hub-key.pem

# Verify .env is git-ignored
cd ~/DATAHUB_AI_Agent
git check-ignore .env
```

### 5. Regular Updates

```bash
# Update system packages monthly
sudo apt update && sudo apt upgrade -y

# Update Python packages
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Update Node.js packages
cd storage/excel_tests
npm update
```

---

## Quick Reference Commands

### Deployment Workflow

```bash
# 1. Local: Commit and push
cd /path/to/ai-agent-qa
git add .
git commit -m "Your changes"
git push

# 2. Server: Pull and restart
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "cd ~/DATAHUB_AI_Agent && git pull && \
   lsof -ti:5000 | xargs kill -9 2>/dev/null; sleep 2; \
   source venv/bin/activate && export FLASK_APP=api/app.py && \
   nohup python -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &"

# 3. Verify
curl http://13.222.91.163:5000/api/health
```

### Monitoring Commands

```bash
# Watch logs
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "tail -f ~/DATAHUB_AI_Agent/flask.log"

# Check Flask status
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "ps aux | grep flask | grep -v grep"

# Check recent executions
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "ls -lth ~/DATAHUB_AI_Agent/storage/executions/ | head -5"
```

### Emergency Commands

```bash
# Kill Flask
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "lsof -ti:5000 | xargs kill -9"

# Restart Flask
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 \
  "cd ~/DATAHUB_AI_Agent && source venv/bin/activate && \
   export FLASK_APP=api/app.py && \
   nohup python -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &"
```

---

## File Structure on Server

```
~/DATAHUB_AI_Agent/
├── api/                    # Flask API routes
│   └── app.py              # Flask application entry point
├── REFACTOR/               # Refactored code modules
│   ├── api/                # API blueprints
│   │   ├── excel_routes.py  # Excel test generation routes
│   │   └── instructions_routes.py
│   └── generator/          # Test generators
│       ├── excel_generator_ts.py  # TypeScript generator
│       └── excel_registry_helper.py
├── agent/                  # AI agent modules
├── validator/             # Test runners
│   └── typescript_test_runner.py
├── web/                    # Web UI templates and static files
├── element_maps/          # JSON element registries
│   └── {domain}/
│       └── {page}_page.json
├── storage/               # Runtime data
│   ├── executions/        # Execution results JSON
│   ├── screenshots/       # Screenshots
│   ├── excel_files/       # Uploaded Excel files
│   └── excel_tests/       # Generated test files
├── venv/                  # Python virtual environment
├── .env                   # Environment variables (NOT in git)
├── flask.log              # Flask application logs
├── requirements.txt      # Python dependencies
└── package.json          # Node.js dependencies (in storage/excel_tests/)
```

---

## Checklist for New Deployment

### Initial Setup
- [ ] EC2 instance launched and accessible
- [ ] SSH key configured with correct permissions
- [ ] System packages updated
- [ ] Python 3.8+ installed
- [ ] Node.js 18+ installed
- [ ] Git repository cloned
- [ ] Virtual environment created and activated
- [ ] Python dependencies installed
- [ ] Playwright browsers installed
- [ ] `.env` file created with all required variables
- [ ] Storage directories created
- [ ] Flask starts successfully
- [ ] Health check endpoint responds

### First Deployment
- [ ] Code pulled from git
- [ ] Dependencies updated
- [ ] Flask restarted
- [ ] API endpoints tested
- [ ] Web UI accessible
- [ ] Excel upload tested
- [ ] Test generation works
- [ ] Test execution works

### Ongoing Maintenance
- [ ] Regular git pulls
- [ ] Monitor logs for errors
- [ ] Check disk space regularly
- [ ] Update dependencies monthly
- [ ] Backup important data
- [ ] Rotate AWS credentials as needed

---

## Support & Resources

### Key Files to Reference
- **System Flow**: `docs/EXCEL_TEST_SYSTEM_FLOW.md`
- **Cursor Rules**: `.cursorrules` (contains project-specific rules)
- **API Documentation**: `REFACTOR/api/README.md`

### Common Issues Documentation
- **AWS Credentials**: See `docs/AWS_CREDENTIALS_FIX.md` if credentials are compromised
- **Deployment**: See `docs/DEPLOYMENT_COMPLETE.md` for previous deployment notes

### Getting Help
1. Check logs: `tail -f ~/DATAHUB_AI_Agent/flask.log`
2. Check execution results: `storage/executions/{execution_id}.json`
3. Review screenshots: `storage/excel_tests/storage/screenshots/`
4. Check registry: `element_maps/{domain}/{page}_page.json`

---

## Notes

- **Never commit `.env` file** - Always verify with `git check-ignore .env`
- **Flask runs on port 5000** - Ensure security group allows access
- **Test files are generated** - Don't edit generated `.spec.ts` files manually
- **Registry is source of truth** - Update Excel, then regenerate tests
- **Use git for deployment** - Avoid manual file edits on server when possible

---

**Last Updated**: January 21, 2026
**Server**: 13.222.91.163
**Project Path**: ~/DATAHUB_AI_Agent

