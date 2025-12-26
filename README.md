# AI Agent QA - Architecture 2

LLM-powered autonomous test execution using Bedrock Agent + MCP

## Architecture

```
User Story → Bedrock Agent (Claude) → MCP Tools → Playwright → Browser
```

**Key Concept:** The LLM makes real-time decisions. No pre-planned scripts. The agent:
- Reads the user story
- Decides what to do next
- Calls browser tools via MCP
- Adapts based on what it sees
- Self-corrects errors

## Features

✅ **Autonomous Testing** - LLM decides and executes in real-time  
✅ **Self-Healing** - Adapts to page changes automatically  
✅ **No Code Maintenance** - Logic lives in LLM, not Python  
✅ **True Agentic** - Handles unexpected scenarios  

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- AWS Account (Bedrock access)
- AWS credentials configured

### Installation

```bash
# Clone the repo
git clone <your-repo>
cd ai-agent-qa

# Run setup script
./scripts/setup.sh
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

### Run

```bash
# Start all services
./scripts/start.sh
```

Open http://localhost:5000

## Example Usage

**User Story:**
```
Go to amazon.com and search for tooth brushes.
Find one that costs less than $5.
Take a screenshot of the product.
```

**What Happens:**
1. Agent navigates to amazon.com
2. Agent examines page (snapshot)
3. Agent finds search box
4. Agent searches "tooth brushes"
5. Agent examines results (snapshot)
6. Agent evaluates prices (JavaScript)
7. Agent finds product under $5
8. Agent clicks on product
9. Agent takes screenshot
10. Agent reports success

**No Python code needed!** Agent figures everything out.

## Project Structure

```
ai-agent-qa/
├── agent/               # Bedrock agent core
├── mcp-server/         # MCP browser tools
├── api/                # Flask API
├── web/                # Web UI
├── storage/            # Results & screenshots
└── scripts/            # Setup & start scripts
```

## Comparison with Architecture 1

| Feature | Architecture 1 (Old) | Architecture 2 (This) |
|---------|---------------------|---------------------|
| **LLM Role** | Generate plan upfront | Make decisions in real-time |
| **Execution** | Python interprets plan | Agent uses tools directly |
| **Adaptability** | Rigid (fails if page changes) | Adaptive (handles changes) |
| **Maintenance** | High (Python execution logic) | Low (LLM handles logic) |
| **Complexity** | 2800+ lines of Python | <500 lines total |

## Technology Stack

- **LLM:** AWS Bedrock (Claude 3.5 Sonnet)
- **Agent Framework:** Bedrock Converse API with tool calling
- **Browser Automation:** Playwright
- **Protocol:** Model Context Protocol (MCP)
- **Backend:** Flask (Python)
- **Frontend:** HTML/JS/CSS

## License

MIT


