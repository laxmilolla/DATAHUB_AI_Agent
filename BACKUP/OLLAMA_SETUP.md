# Ollama Setup - FREE Local LLM

## Why Ollama?

✅ **100% FREE** - No API costs  
✅ **Runs locally** - No internet required after download  
✅ **Private** - Your data stays on your machine  
✅ **Fast** - No network latency  
✅ **No AWS/API keys needed**

## Quick Setup (5 minutes)

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
# OR download from https://ollama.ai/download
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download installer from https://ollama.ai/download

### 2. Start Ollama

```bash
ollama serve
```

This starts Ollama on `http://localhost:11434`

### 3. Download a Model

**Recommended (fast, good quality):**
```bash
ollama pull llama3.2
```

**Other options:**
```bash
# Smaller, faster
ollama pull llama3.2:1b

# Better quality, slower
ollama pull llama3.1:8b

# Best quality, slowest
ollama pull llama3.1:70b
```

### 4. Configure .env

Edit your `.env` file:
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 5. Test It

```bash
# Test Ollama is running
curl http://localhost:11434/api/tags

# Should return list of installed models
```

### 6. Run Your App

```bash
python api/app.py
```

The app will automatically use Ollama!

## Model Recommendations

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llama3.2:1b` | 1.3GB | ⚡⚡⚡ | ⭐⭐ | Fast testing, simple tasks |
| `llama3.2` | 2GB | ⚡⚡ | ⭐⭐⭐ | **Recommended** - Good balance |
| `llama3.1:8b` | 4.7GB | ⚡ | ⭐⭐⭐⭐ | Better quality, slower |
| `llama3.1:70b` | 40GB | 🐌 | ⭐⭐⭐⭐⭐ | Best quality, very slow |

## Troubleshooting

**Ollama not starting:**
```bash
# Check if port 11434 is in use
lsof -i :11434

# Kill existing process
killall ollama

# Restart
ollama serve
```

**Model not found:**
```bash
# List installed models
ollama list

# Pull the model again
ollama pull llama3.2
```

**Connection refused:**
- Make sure `ollama serve` is running
- Check `OLLAMA_BASE_URL` in `.env` matches your Ollama URL

## Performance Tips

1. **Use smaller models for testing** - `llama3.2:1b` is fastest
2. **Close other apps** - More RAM = better performance
3. **Use GPU if available** - Ollama auto-detects GPU
4. **Monitor RAM usage** - Models need RAM (1b=2GB, 8b=8GB, 70b=40GB)

## Cost Comparison

| Provider | Cost per 1M tokens | Monthly (1000 tests) |
|----------|-------------------|---------------------|
| **Ollama** | **$0** | **$0** |
| AWS Bedrock | $3-15 | $50-200 |
| OpenAI GPT-4 | $30-60 | $500-1000 |
| Anthropic Claude | $3-15 | $50-200 |

**Ollama = FREE forever!** 🎉

