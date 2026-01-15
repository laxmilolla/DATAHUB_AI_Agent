# Step-by-Step Guide: Fix AWS Credentials for Bedrock

## Problem
AWS has quarantined your credentials due to compromised keys. The `AWSCompromisedKeyQuarantineV3` policy is blocking Bedrock access.

## Solution Steps

### Step 1: Generate New AWS Access Keys

1. **Log into AWS Console**
   - Go to https://console.aws.amazon.com
   - Sign in with your AWS account

2. **Navigate to IAM**
   - Search for "IAM" in the top search bar
   - Click on "IAM" service

3. **Go to Users**
   - Click "Users" in the left sidebar
   - Find and click on your user (the one associated with the quarantined keys)

4. **Create New Access Key**
   - Click the "Security credentials" tab
   - Scroll to "Access keys" section
   - Click "Create access key"
   - Select "Application running outside AWS" (or appropriate use case)
   - Click "Next"
   - Add description (optional): "Bedrock API Access"
   - Click "Create access key"

5. **Save Credentials IMMEDIATELY**
   - **Access Key ID**: Copy this (starts with `AKIA...`)
   - **Secret Access Key**: Copy this (you can only see it once!)
   - ⚠️ **IMPORTANT**: Save these securely - you won't be able to see the secret key again!

### Step 2: Update .env File on Server

**Option A: Using SSH (Recommended)**
```bash
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163
cd ~/DATAHUB_AI_Agent
nano .env
```

**Option B: Using SCP (Edit locally, then upload)**
```bash
# Download current .env
scp -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/.env .env.local

# Edit .env.local with new credentials
# Then upload back
scp -i ~/Downloads/ai-crdc-hub-key.pem .env.local ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/.env
```

**Update these lines in .env:**
```bash
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=<NEW_ACCESS_KEY_ID>
AWS_SECRET_ACCESS_KEY=<NEW_SECRET_ACCESS_KEY>
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Step 3: Deactivate Old Access Keys

1. **In AWS Console → IAM → Users → Your User → Security credentials**
2. Find the OLD access key (the one that's quarantined)
3. Click the "..." menu next to it
4. Click "Deactivate"
5. Confirm deactivation
6. After verifying new keys work, you can delete the old key

### Step 4: Contact AWS Support to Remove Quarantine

1. **Open AWS Support Case**
   - Go to https://console.aws.amazon.com/support
   - Click "Create case"
   - Select "Account and billing support"
   - Case type: "Service limit increase" or "Account"

2. **Request Quarantine Removal**
   - Subject: "Request to remove AWSCompromisedKeyQuarantineV3 policy after credential rotation"
   - Message template:
   ```
   Hello AWS Support,
   
   I have rotated my compromised AWS credentials as instructed:
   - Old access key has been deactivated
   - New access key has been created
   - New credentials are now in use
   
   Please remove the AWSCompromisedKeyQuarantineV3 policy from my account 
   so I can access Bedrock services again.
   
   Thank you.
   ```

3. **Wait for AWS Response**
   - Usually 24-48 hours
   - AWS will verify credentials are rotated
   - They will remove the quarantine policy

### Step 5: Verify Bedrock Access

**Test Bedrock Connection:**
```bash
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163
cd ~/DATAHUB_AI_Agent
source venv/bin/activate
python3 -c "
import boto3
import os
from dotenv import load_dotenv
load_dotenv()

bedrock = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
)

try:
    response = bedrock.converse(
        modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        messages=[{'role': 'user', 'content': [{'text': 'Hello'}]}],
        inferenceConfig={'maxTokens': 10, 'temperature': 0.0}
    )
    print('✅ Bedrock access working!')
except Exception as e:
    print(f'❌ Bedrock access failed: {e}')
"
```

### Step 6: Restart Flask with Bedrock

```bash
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163
cd ~/DATAHUB_AI_Agent
pkill -9 -f "python.*app.py"
source venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"
nohup python3 api/app.py > flask.log 2>&1 &
sleep 3
tail -20 flask.log
```

## Timeline

- **Step 1-2**: 10 minutes (generate keys, update .env)
- **Step 3**: 2 minutes (deactivate old keys)
- **Step 4**: 5 minutes (create support case)
- **Step 5**: 2 minutes (test connection)
- **AWS Response**: 24-48 hours (wait for quarantine removal)
- **Step 6**: 2 minutes (restart Flask)

**Total Active Time**: ~20 minutes  
**Total Wait Time**: 24-48 hours for AWS support

## Quick Commands Reference

```bash
# Update .env on server
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 'cd ~/DATAHUB_AI_Agent && nano .env'

# Verify .env updated
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 'cd ~/DATAHUB_AI_Agent && cat .env | grep AWS'

# Test Bedrock (after AWS removes quarantine)
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 'cd ~/DATAHUB_AI_Agent && source venv/bin/activate && python3 -c "import boto3; from dotenv import load_dotenv; import os; load_dotenv(); bedrock = boto3.client(\"bedrock-runtime\", aws_access_key_id=os.getenv(\"AWS_ACCESS_KEY_ID\"), aws_secret_access_key=os.getenv(\"AWS_SECRET_ACCESS_KEY\"), region_name=\"us-east-1\"); print(\"✅ Bedrock client created successfully\")"'
```

## Notes

- ⚠️ **Never commit .env file** - it contains secrets
- 🔒 **Keep new credentials secure** - don't share or expose
- 📧 **Check AWS Support email** - they'll notify when quarantine is removed
- ✅ **Test immediately** - verify Bedrock works before running full tests

