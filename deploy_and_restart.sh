#!/bin/bash
# Deploy and restart Flask script

echo "=== Deploying files ==="
scp -i ~/Downloads/ai-crdc-hub-key.pem /Users/lollal/Documents/ai-agent-qa/generator/pw_codegen/step_generators.py ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/generator/pw_codegen/step_generators.py
echo "✅ step_generators.py deployed"

scp -i ~/Downloads/ai-crdc-hub-key.pem /Users/lollal/Documents/ai-agent-qa/api/routes.py ubuntu@13.222.91.163:~/DATAHUB_AI_Agent/api/routes.py
echo "✅ routes.py deployed"

echo ""
echo "=== Restarting Flask ==="
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@13.222.91.163 << 'EOF'
cd ~/DATAHUB_AI_Agent
echo "Stopping Flask..."
pkill -f "python.*app.py" || echo "No Flask process found"
sleep 2
echo "Starting Flask..."
source venv/bin/activate
nohup python api/app.py > flask.log 2>&1 &
sleep 3
echo ""
echo "=== Flask Status ==="
ps aux | grep "python.*app.py" | grep -v grep || echo "Flask not running"
echo ""
echo "=== Flask Log (last 15 lines) ==="
tail -15 flask.log
EOF

echo ""
echo "✅ Deployment complete!"



