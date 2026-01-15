# Groq Setup - FREE Cloud LLM (No Local Resources!)

## Why Groq?

✅ **100% FREE** - No API costs  
✅ **No local resources** - Runs in cloud, doesn't slow your computer  
✅ **Very fast** - GPU-powered, faster than local  
✅ **No installation** - Just need API key  
✅ **No RAM/CPU usage** - Your computer stays fast  

## Quick Setup (2 minutes)

### 1. Get Free API Key

1. Go to https://console.groq.com
2. Sign up (free, no credit card needed)
3. Go to API Keys section
4. Create new API key
5. Copy the key

### 2. Configure .env

Edit your `.env` file:
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

### 3. Install Groq Package

```bash
pip install groq
```

### 4. Run Your App

```bash
python api/app.py
```

That's it! No local resources used, your computer stays fast! 🚀

## Available Models

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `llama-3.1-8b-instant` | ⚡⚡⚡ | ⭐⭐⭐⭐ | **Recommended** - Fast & good |
| `llama-3.1-70b-versatile` | ⚡⚡ | ⭐⭐⭐⭐⭐ | Best quality, slower |
| `mixtral-8x7b-32768` | ⚡⚡⚡ | ⭐⭐⭐⭐ | Fast, good for long context |

## Free Tier Limits

- **30 requests/minute** - More than enough for testing
- **No daily limit** - Use as much as you want
- **No credit card** - Truly free

## Comparison

| Provider | Cost | Local Resources | Speed | Setup Time |
|----------|------|----------------|-------|------------|
| **Groq** | **FREE** | **None** | ⚡⚡⚡ | 2 min |
| Ollama | FREE | High (RAM/CPU) | ⚡⚡ | 5 min |
| AWS Bedrock | $3-15/1M | None | ⚡⚡ | 10 min |
| OpenAI | $30-60/1M | None | ⚡⚡ | 5 min |

**Groq = FREE + Fast + No local resources!** 🎉

## Troubleshooting

**API key invalid:**
- Make sure you copied the full key (starts with `gsk_`)
- Check for extra spaces in `.env` file

**Rate limit:**
- Groq allows 30 requests/minute
- If you hit limit, wait 1 minute
- For production, consider paid tier

**Connection error:**
- Check internet connection
- Verify `GROQ_API_KEY` is set correctly

