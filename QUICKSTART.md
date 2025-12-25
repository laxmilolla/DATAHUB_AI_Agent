# Quick Start Guide - AI Agent QA

## 📦 What You Have

A complete **Architecture 2** system where an AI agent (Claude via Bedrock) autonomously executes tests by making real-time decisions and controlling the browser via MCP.

**Key Difference from Old System:**
- ❌ OLD: LLM generates plan → Python executes plan (rigid)
- ✅ NEW: LLM makes decisions in real-time → Direct browser control (adaptive)

## 🚀 Setup (5 minutes)

### 1. Prerequisites

- Python 3.10+ installed
- Node.js 18+ installed
- AWS account with Bedrock access to Claude 3.5 Sonnet

### 2. Install

```bash
cd /Users/lollal/Documents/ai-agent-qa

# Run setup script
./scripts/setup.sh
```

This will:
- Create Python virtual environment
- Install Python dependencies (boto3, Flask)
- Install Node dependencies (@modelcontextprotocol/sdk, Playwright)
- Install Chromium browser
- Create storage directories

### 3. Configure AWS Credentials

Edit `.env` file (created from `env.example`):

```bash
# Edit this file
nano .env

# Add your AWS credentials:
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
```

**Where to get credentials:**
1. AWS Console → IAM → Users → Your User → Security Credentials
2. Create Access Key
3. Save the key ID and secret

**Required Permissions:**
- `bedrock:InvokeModel` for Claude 3.5 Sonnet
- `bedrock:InvokeModelWithResponseStream` (optional)

### 4. Start the Application

```bash
./scripts/start.sh
```

This starts Flask on http://localhost:5000

## 🎯 Usage

### Web Interface

1. Open http://localhost:5000
2. Enter a test scenario in natural language:
   ```
   Go to amazon.com and search for "wireless headphones".
   Find a product under $50 and take a screenshot.
   ```
3. Click "Execute Test"
4. Watch the agent work!

The agent will:
- Navigate to the site
- Examine the page
- Find elements
- Perform actions
- Take screenshots
- Report results

### Example Test Scenarios

**Simple Navigation:**
```
Go to google.com and take a screenshot
```

**Search Test:**
```
Navigate to amazon.com
Search for "laptop stand"
Click on the first result
Take a screenshot of the product page
```

**Form Filling:**
```
Go to example.com/contact
Fill in the name field with "Test User"
Fill in the email field with "test@example.com"
Click the submit button
```

**Complex Scenario:**
```
Go to amazon.com
Search for "mechanical keyboard"
Filter results to show only items under $100
Sort by customer reviews
Take a screenshot of the results page
```

## 📁 Project Structure

```
ai-agent-qa/
├── agent/              # Bedrock agent core
│   └── bedrock_agent.py
├── mcp-server/        # MCP browser tools
│   └── server.js
├── api/               # Flask API
│   ├── app.py
│   └── routes.py
├── web/               # Web UI
│   ├── templates/
│   └── static/
├── storage/           # Results & screenshots
│   ├── executions/
│   └── screenshots/
└── scripts/           # Setup & start
```

## 🧪 Testing

Run a simple test:

```bash
# Activate venv
source venv/bin/activate

# Run test
python tests/test_agent.py
```

This tests basic navigation to Google.

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'boto3'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "AWS credentials not configured"
Check your `.env` file has valid AWS credentials.

### "MCP server failed to start"
```bash
cd mcp-server
npm install
npx playwright install chromium
```

### "Port 5000 already in use"
Stop other Flask apps or change port in `api/app.py`

## 📊 Viewing Results

1. After execution completes, click "View Full Results"
2. See:
   - Execution status
   - All actions taken
   - Screenshots captured
   - Agent's summary

## 🔄 How It Works

1. **User submits story** → Flask API
2. **API starts agent** → `BedrockAgentQA`
3. **Agent starts MCP server** → Playwright browser tools available
4. **Agent loops:**
   - Agent reads story
   - Agent decides next action
   - Agent calls browser tool (navigate, click, fill, screenshot, evaluate)
   - Agent receives result
   - Agent adapts based on result
   - Repeat until task complete
5. **Agent reports** → Results saved + screenshots
6. **User views results** → Web UI

## 🆚 vs Architecture 1 (Old System)

| Aspect | Architecture 1 | Architecture 2 (This) |
|--------|---------------|---------------------|
| **LLM Role** | Generate test plan once | Make decisions continuously |
| **Execution** | Python loops through plan | Agent calls tools dynamically |
| **Adaptability** | Fails if page changes | Adapts to changes |
| **Maintenance** | Update Python code | Update system prompt |
| **Complexity** | 2800+ lines | ~500 lines |
| **Debugging** | Multi-layer (LLM→Python→HTTP→Bridge→MCP) | Two-layer (LLM→MCP) |

## 📝 Next Steps

1. ✅ Setup complete - Try the example scenarios
2. Test with your own applications
3. Customize system prompt in `agent/bedrock_agent.py`
4. Add more browser tools in `mcp-server/server.js`
5. Deploy to EC2 (see `README.md` for deployment guide)

## 💡 Tips

- **Start simple:** Test with basic scenarios first (navigate + screenshot)
- **Be specific:** More detailed scenarios get better results
- **Check logs:** MCP server logs go to stderr, visible in terminal
- **Screenshots:** All screenshots saved to `storage/screenshots/`
- **Results:** All execution results saved to `storage/executions/`

## 🆘 Support

Issues? Check:
1. AWS Bedrock is enabled in your region
2. Claude 3.5 Sonnet model is available
3. Your credentials have correct permissions
4. MCP server is running (check for Node.js process)

---

**You're ready to go!** Start the app and try your first test. 🚀

