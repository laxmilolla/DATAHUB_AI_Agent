// Main app JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('story-form');
    const executeBtn = document.getElementById('execute-btn');
    const statusDiv = document.getElementById('status');
    const statusText = document.getElementById('status-text');
    const statusDetails = document.getElementById('status-details');
    
    // Load recent executions
    loadExecutions();
    
    // Handle form submission
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const story = document.getElementById('story').value.trim();
            
            if (!story) {
                alert('Please enter a test scenario');
                return;
            }
            
            // Disable form
            executeBtn.disabled = true;
            executeBtn.querySelector('.btn-text').style.display = 'none';
            executeBtn.querySelector('.btn-loading').style.display = 'inline-block';
            
            // Show status
            statusDiv.style.display = 'block';
            statusText.textContent = 'Starting agent...';
            statusDetails.innerHTML = '<p>Initializing Bedrock Agent and MCP server...</p>';
            
            try {
                // Start execution
                const response = await fetch('/api/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ story })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Execution failed');
                }
                
                const executionId = data.execution_id;
                
                statusText.textContent = 'Agent is executing...';
                statusDetails.innerHTML = '<p>The AI agent is now working on your scenario. This may take a few minutes...</p>';
                
                // Poll for status
                pollExecutionStatus(executionId);
                
            } catch (error) {
                statusText.textContent = 'Error';
                statusDetails.innerHTML = `<p class="error">${error.message}</p>`;
                
                // Re-enable form
                executeBtn.disabled = false;
                executeBtn.querySelector('.btn-text').style.display = 'inline';
                executeBtn.querySelector('.btn-loading').style.display = 'none';
            }
        });
    }
});

async function pollExecutionStatus(executionId) {
    const statusText = document.getElementById('status-text');
    const statusDetails = document.getElementById('status-details');
    const executeBtn = document.getElementById('execute-btn');
    
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/executions/${executionId}/status`);
            const data = await response.json();
            
            const status = data.status;
            const actionsCount = data.actions_count || 0;
            const screenshotsCount = data.screenshots_count || 0;
            
            statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            
            let detailsHtml = `
                <p>Execution ID: ${executionId}</p>
                <p>Actions taken: ${actionsCount}</p>
                <p>Screenshots: ${screenshotsCount}</p>
            `;
            
            if (data.summary) {
                detailsHtml += `<p><strong>Summary:</strong> ${data.summary}</p>`;
            }
            
            if (data.error) {
                detailsHtml += `<p class="error"><strong>Error:</strong> ${data.error}</p>`;
            }
            
            statusDetails.innerHTML = detailsHtml;
            
            // Check if execution is complete
            if (status === 'completed' || status === 'error' || status === 'timeout') {
                clearInterval(pollInterval);
                
                // Re-enable form
                executeBtn.disabled = false;
                executeBtn.querySelector('.btn-text').style.display = 'inline';
                executeBtn.querySelector('.btn-loading').style.display = 'none';
                
                // Add link to results
                statusDetails.innerHTML += `
                    <p style="margin-top: 15px;">
                        <a href="/results/${executionId}" style="color: #667eea; font-weight: 600;">
                            View Full Results →
                        </a>
                    </p>
                `;
                
                // Reload executions list
                loadExecutions();
            }
            
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 2000); // Poll every 2 seconds
}

async function loadExecutions() {
    const container = document.getElementById('executions-list');
    
    if (!container) return;
    
    try {
        const response = await fetch('/api/executions');
        const data = await response.json();
        
        if (data.executions && data.executions.length > 0) {
            container.innerHTML = '';
            
            data.executions.forEach(exec => {
                const item = document.createElement('div');
                item.className = 'execution-item';
                item.style.cursor = 'pointer';
                
                const statusClass = `status-${exec.status}`;
                
                item.innerHTML = `
                    <div class="execution-header">
                        <span class="status-badge ${statusClass}">${exec.status}</span>
                        <span>${new Date(exec.started_at).toLocaleString()}</span>
                    </div>
                    <div class="execution-story">${exec.story}</div>
                    <div class="execution-stats">
                        <span>🎬 ${exec.actions_count} actions</span>
                        <span>📸 ${exec.screenshots_count} screenshots</span>
                        ${exec.duration ? `<span>⏱️ ${exec.duration.toFixed(1)}s</span>` : ''}
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    window.location.href = `/results/${exec.execution_id}`;
                });
                
                container.appendChild(item);
            });
        } else {
            container.innerHTML = '<p class="loading">No executions yet. Start your first test above!</p>';
        }
        
    } catch (error) {
        console.error('Error loading executions:', error);
        container.innerHTML = '<p class="error">Error loading executions</p>';
    }
}

