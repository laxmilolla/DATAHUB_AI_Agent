# Experiment Area - CDP Setup Guide

## Problem
Flask runs on EC2 server, but you want to:
1. Set up preconditions manually in your local Chrome (login, TOTP, navigate)
2. Then run test instructions that execute in that same browser

## Solution: SSH Reverse Port Forwarding

### Step 1: Start Chrome Locally with Remote Debugging

On your Mac, open Terminal and run:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

This starts Chrome with CDP enabled on port 9222.

### Step 2: Set Up SSH Reverse Port Forwarding

In a **new terminal window**, run:
```bash
ssh -R 9222:localhost:9222 -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163
```

**What this does:**
- `-R 9222:localhost:9222` = Reverse forward: port 9222 on the SERVER forwards to port 9222 on YOUR machine
- When Flask on the server connects to `localhost:9222`, it will actually connect to your Chrome

### Step 3: Keep SSH Connection Open

**Important:** Keep this SSH terminal window open! The port forwarding only works while the SSH connection is active.

### Step 4: Use Experiment Area

1. Go to: `http://13.222.91.163:5000/experiment`
2. Check "Use My Chrome Browser"
3. Click "Start Browser"
4. Flask will connect to your Chrome via the forwarded port
5. You'll see "Connected to Your Chrome Browser!" message
6. Set up preconditions manually (login, TOTP, navigate to page)
7. Enter test instructions
8. Click "Execute Test"

## Alternative: Keep SSH Connection in Background

If you want to keep the SSH connection running in the background:

```bash
ssh -R 9222:localhost:9222 -N -f -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163
```

- `-N` = Don't execute remote commands
- `-f` = Run in background
- To stop: `ps aux | grep ssh` and kill the process

## Troubleshooting

**If connection fails:**
1. Make sure Chrome is running with `--remote-debugging-port=9222`
2. Check Chrome is listening: `lsof -i :9222` (should show Chrome)
3. Make sure SSH reverse forwarding is active: Check the SSH connection is still open
4. On server, test: `curl http://localhost:9222/json` (should return Chrome debug info)

**Verify Chrome CDP is working:**
```bash
curl http://localhost:9222/json
```

Should return JSON with Chrome tabs/pages info.

