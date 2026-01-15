// Experiment Area JavaScript

let currentSessionId = null;
let screenshotPollInterval = null;
let statusPollInterval = null;

// Start browser session
async function startBrowser() {
    try {
        const btn = document.getElementById('start-browser-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Starting...';
        
        const response = await fetch('/api/experiment/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!response.ok) {
            throw new Error('Failed to start browser');
        }
        
        const data = await response.json();
        currentSessionId = data.session_id;
        const browserLocation = data.browser_location || 'server';
        const message = data.message || 'Browser started';
        
        // Update UI
        if (browserLocation === 'local') {
            // Local browser - show message that it's visible on screen
            document.getElementById('browser-viewport').innerHTML = `
                <div class="browser-placeholder">
                    <div class="icon">✅</div>
                    <p><strong>Browser Running Locally!</strong></p>
                    <p style="font-size: 0.9em; margin-top: 10px; color: #8B6F47;">
                        Check your screen - the browser window should be visible.<br>
                        You can interact with it directly.
                    </p>
                </div>
            `;
        } else {
            // Server browser - show placeholder with note
            document.getElementById('browser-viewport').innerHTML = `
                <div class="browser-placeholder">
                    <div class="icon">🌐</div>
                    <p><strong>Browser Running on Server</strong></p>
                    <p style="font-size: 0.9em; margin-top: 10px; color: #6B5B3D;">
                        Browser is running on the server (not visible).<br>
                        Screenshots will appear below as the test runs.
                    </p>
                </div>
            `;
        }
        
        document.getElementById('start-browser-btn').style.display = 'none';
        document.getElementById('stop-browser-btn').disabled = false;
        document.getElementById('execute-btn').disabled = false;
        
        showMessage(message, 'success');
        
    } catch (error) {
        console.error('Error starting browser:', error);
        showMessage('❌ Failed to start browser: ' + error.message, 'error');
        document.getElementById('start-browser-btn').disabled = false;
        document.getElementById('start-browser-btn').innerHTML = '▶ Start Browser';
    }
}

// Stop browser session
async function stopBrowser() {
    if (!currentSessionId) return;
    
    try {
        const btn = document.getElementById('stop-browser-btn');
        btn.disabled = true;
        
        await fetch(`/api/experiment/${currentSessionId}/stop`, {
            method: 'POST'
        });
        
        // Clear intervals
        if (screenshotPollInterval) {
            clearInterval(screenshotPollInterval);
            screenshotPollInterval = null;
        }
        if (statusPollInterval) {
            clearInterval(statusPollInterval);
            statusPollInterval = null;
        }
        
        // Reset UI
        document.getElementById('browser-viewport').innerHTML = `
            <div class="browser-placeholder">
                <div class="icon">🌐</div>
                <p>Click "Start Browser" to begin</p>
            </div>
        `;
        
        document.getElementById('start-browser-btn').style.display = 'inline-block';
        document.getElementById('stop-browser-btn').disabled = true;
        document.getElementById('execute-btn').disabled = true;
        document.getElementById('download-excel-btn').disabled = true;
        
        currentSessionId = null;
        showMessage('✅ Browser stopped', 'success');
        
    } catch (error) {
        console.error('Error stopping browser:', error);
        showMessage('❌ Failed to stop browser: ' + error.message, 'error');
    }
}

// Execute instructions
async function executeInstructions() {
    if (!currentSessionId) {
        showMessage('❌ Please start browser first', 'error');
        return;
    }
    
    const instructions = document.getElementById('instructions-input').value.trim();
    if (!instructions) {
        showMessage('❌ Please enter test instructions', 'error');
        return;
    }
    
    try {
        const btn = document.getElementById('execute-btn');
        btn.disabled = true;
        btn.querySelector('.btn-text').style.display = 'none';
        btn.querySelector('.btn-loading').style.display = 'inline-block';
        
        // Show status section
        document.getElementById('status-section').style.display = 'block';
        document.getElementById('status-text').textContent = 'Starting execution...';
        
        // Show screenshots section
        document.getElementById('screenshots-section').style.display = 'block';
        document.getElementById('screenshots-grid').innerHTML = '<div class="empty-state"><div class="icon">⏳</div><p>Waiting for screenshots...</p></div>';
        
        // Start execution
        const response = await fetch(`/api/experiment/${currentSessionId}/execute`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({instructions: instructions})
        });
        
        if (!response.ok) {
            throw new Error('Failed to execute instructions');
        }
        
        const data = await response.json();
        
        // Start polling for status and screenshots
        startPolling();
        
        showMessage('✅ Test execution started!', 'success');
        
    } catch (error) {
        console.error('Error executing instructions:', error);
        showMessage('❌ Failed to execute: ' + error.message, 'error');
        
        const btn = document.getElementById('execute-btn');
        btn.disabled = false;
        btn.querySelector('.btn-text').style.display = 'inline';
        btn.querySelector('.btn-loading').style.display = 'none';
    }
}

// Start polling for status and screenshots
function startPolling() {
    // Poll status every 1 second
    statusPollInterval = setInterval(async () => {
        if (!currentSessionId) return;
        
        try {
            const response = await fetch(`/api/experiment/${currentSessionId}/status`);
            if (response.ok) {
                const data = await response.json();
                updateStatus(data);
                
                // Stop polling if completed
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(statusPollInterval);
                    statusPollInterval = null;
                    
                    // Enable download button
                    document.getElementById('download-excel-btn').disabled = false;
                    
                    // Re-enable execute button
                    const btn = document.getElementById('execute-btn');
                    btn.disabled = false;
                    btn.querySelector('.btn-text').style.display = 'inline';
                    btn.querySelector('.btn-loading').style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 1000);
    
    // Poll screenshots every 2 seconds
    screenshotPollInterval = setInterval(async () => {
        if (!currentSessionId) return;
        
        try {
            const response = await fetch(`/api/experiment/${currentSessionId}/screenshots`);
            if (response.ok) {
                const data = await response.json();
                updateScreenshotGrid(data.screenshots || []);
            }
        } catch (error) {
            console.error('Error polling screenshots:', error);
        }
    }, 2000);
}

// Update status display
function updateStatus(data) {
    const statusText = document.getElementById('status-text');
    const status = data.status || 'unknown';
    const currentStep = data.current_step || 0;
    const totalSteps = data.total_steps || 0;
    const stepDescription = data.step_description || '';
    
    if (status === 'running') {
        statusText.textContent = `Step ${currentStep}/${totalSteps}: ${stepDescription}`;
        statusText.style.color = '#8B6F47';
    } else if (status === 'completed') {
        statusText.textContent = `✅ Completed! ${totalSteps} steps executed`;
        statusText.style.color = '#8B6F47';
    } else if (status === 'failed') {
        statusText.textContent = `❌ Failed: ${data.error || 'Unknown error'}`;
        statusText.style.color = '#3D3D3D';
    } else {
        statusText.textContent = `Status: ${status}`;
    }
}

// Update screenshot grid
function updateScreenshotGrid(screenshots) {
    const grid = document.getElementById('screenshots-grid');
    
    if (screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="icon">📸</div><p>No screenshots yet</p></div>';
        return;
    }
    
    grid.innerHTML = screenshots.map((screenshot, idx) => {
        const filename = screenshot.split('/').pop();
        return `
            <div class="screenshot-item" onclick="window.open('/api/screenshots/${filename}', '_blank')">
                <img src="/api/screenshots/${filename}" 
                     alt="Step ${idx + 1}"
                     onerror="this.parentElement.innerHTML='<div style=\\'padding: 20px; text-align: center;\\'>📷 Not Found</div>'">
                <div class="screenshot-label">Step ${idx + 1}</div>
            </div>
        `;
    }).join('');
    
    // Auto-scroll to latest screenshot
    grid.scrollLeft = grid.scrollWidth;
}

// Download Excel
async function downloadExcel() {
    if (!currentSessionId) {
        showMessage('❌ No active session', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/experiment/${currentSessionId}/excel`);
        if (!response.ok) {
            throw new Error('Failed to generate Excel');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `experiment_${currentSessionId}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showMessage('✅ Excel file downloaded!', 'success');
        
    } catch (error) {
        console.error('Error downloading Excel:', error);
        showMessage('❌ Failed to download Excel: ' + error.message, 'error');
    }
}

// Show message
function showMessage(message, type) {
    // Simple alert for now - can be enhanced with toast notifications
    const statusSection = document.getElementById('status-section');
    if (statusSection) {
        statusSection.style.display = 'block';
        const statusText = document.getElementById('status-text');
        statusText.textContent = message;
        statusText.style.color = type === 'error' ? '#3D3D3D' : '#8B6F47';
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (screenshotPollInterval) clearInterval(screenshotPollInterval);
    if (statusPollInterval) clearInterval(statusPollInterval);
    if (currentSessionId) {
        // Try to stop browser (fire and forget)
        fetch(`/api/experiment/${currentSessionId}/stop`, {method: 'POST'}).catch(() => {});
    }
});

