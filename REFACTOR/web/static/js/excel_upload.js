// Excel Upload JavaScript
// Handles Excel file upload, validation, and test generation

document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const generateBtn = document.getElementById('generateBtn');
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const statusMessage = document.getElementById('statusMessage');
    const validationResults = document.getElementById('validationResults');
    const validationContent = document.getElementById('validationContent');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    
    let currentExcelId = null;
    let uploadedFile = null;
    
    // File input click handler
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File input change handler
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    // Handle file selection
    function handleFileSelect(file) {
        // Validate file type
        if (!file.name.match(/\.(xlsx|xls)$/i)) {
            showMessage('Invalid file type. Please select an Excel file (.xlsx or .xls)', 'error');
            return;
        }
        
        uploadedFile = file;
        fileName.textContent = file.name;
        fileInfo.style.display = 'block';
        uploadBtn.disabled = false;
        
        // Reset state
        currentExcelId = null;
        generateBtn.disabled = true;
        validationResults.style.display = 'none';
        resultsSection.style.display = 'none';
        hideMessage();
    }
    
    // Upload button handler
    uploadBtn.addEventListener('click', async () => {
        if (!uploadedFile) {
            showMessage('Please select a file first', 'error');
            return;
        }
        
        await uploadFile();
    });
    
    // Generate button handler
    generateBtn.addEventListener('click', async () => {
        if (!currentExcelId) {
            showMessage('Please upload and validate a file first', 'error');
            return;
        }
        
        await generateTest();
    });
    
    // Download template button handler
    downloadTemplateBtn.addEventListener('click', () => {
        window.location.href = '/api/excel/template?include_examples=true';
    });
    
    // Upload file
    async function uploadFile() {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        
        // Disable button and show loading
        uploadBtn.disabled = true;
        uploadBtn.querySelector('.btn-text').style.display = 'none';
        uploadBtn.querySelector('.btn-loading').style.display = 'inline-block';
        
        hideMessage();
        validationResults.style.display = 'none';
        
        try {
            const response = await fetch('/api/excel/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }
            
            currentExcelId = data.excel_id;
            
            // Show validation results
            if (data.validation) {
                displayValidationResults(data.validation);
            }
            
            if (data.success) {
                showMessage('File uploaded and validated successfully!', 'success');
                generateBtn.disabled = false;
            } else {
                showMessage('File uploaded but validation failed. Check validation results below.', 'error');
            }
            
        } catch (error) {
            showMessage('Upload failed: ' + error.message, 'error');
            currentExcelId = null;
            generateBtn.disabled = true;
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.querySelector('.btn-text').style.display = 'inline';
            uploadBtn.querySelector('.btn-loading').style.display = 'none';
        }
    }
    
    // Generate test
    async function generateTest() {
        if (!currentExcelId) {
            showMessage('No file uploaded', 'error');
            return;
        }
        
        // Disable button and show loading
        generateBtn.disabled = true;
        generateBtn.querySelector('.btn-text').style.display = 'none';
        generateBtn.querySelector('.btn-loading').style.display = 'inline-block';
        
        hideMessage();
        
        try {
            const response = await fetch('/api/excel/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    excel_id: currentExcelId
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Generation failed');
            }
            
            if (data.success) {
                showMessage('Test generated successfully! Running test...', 'success');
                displayResults(data);
                
                // If execution_id is provided, redirect to results page after a delay
                if (data.execution_id && data.results_url) {
                    setTimeout(() => {
                        window.location.href = data.results_url;
                    }, 2000);
                }
            } else {
                showMessage('Generation failed: ' + (data.error || 'Unknown error'), 'error');
            }
            
        } catch (error) {
            showMessage('Generation failed: ' + error.message, 'error');
        } finally {
            generateBtn.disabled = false;
            generateBtn.querySelector('.btn-text').style.display = 'inline';
            generateBtn.querySelector('.btn-loading').style.display = 'none';
        }
    }
    
    // Display validation results
    function displayValidationResults(validation) {
        validationResults.style.display = 'block';
        validationContent.innerHTML = '';
        
        if (validation.valid) {
            validationContent.innerHTML += '<p style="color: #28a745; font-weight: 600;">✅ Validation passed</p>';
        } else {
            validationContent.innerHTML += '<p style="color: #dc3545; font-weight: 600;">❌ Validation failed</p>';
        }
        
        if (validation.row_count) {
            validationContent.innerHTML += `<p><strong>Rows:</strong> ${validation.row_count}</p>`;
        }
        
        if (validation.errors && validation.errors.length > 0) {
            validationContent.innerHTML += '<h5 style="margin-top: 15px; color: #dc3545;">Errors:</h5>';
            validation.errors.forEach(error => {
                validationContent.innerHTML += `<div class="validation-error">• ${error}</div>`;
            });
        }
        
        if (validation.warnings && validation.warnings.length > 0) {
            validationContent.innerHTML += '<h5 style="margin-top: 15px; color: #856404;">Warnings:</h5>';
            validation.warnings.forEach(warning => {
                validationContent.innerHTML += `<div class="validation-warning">• ${warning}</div>`;
            });
        }
    }
    
    // Display generation results
    function displayResults(data) {
        resultsSection.style.display = 'block';
        
        let html = `
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #28a745;">✅ Test Generated Successfully</h3>
                <p><strong>Test Name:</strong> ${data.test_name || 'N/A'}</p>
                <p><strong>Rows Processed:</strong> ${data.rows_processed || 0}</p>
                <p><strong>Generated At:</strong> ${new Date(data.generated_at).toLocaleString()}</p>
                ${data.execution_id ? `<p><strong>Execution ID:</strong> ${data.execution_id}</p>` : ''}
                ${data.test_running ? '<p style="color: #17a2b8;"><strong>⏳ Test is running in background...</strong></p>' : ''}
            </div>
            
            <div class="action-buttons">
                ${data.results_url ? `
                    <button class="btn btn-primary" onclick="window.location.href='${data.results_url}'">
                        View Results & Screenshots
                    </button>
                ` : ''}
                <button class="btn btn-primary" onclick="downloadTest('${currentExcelId}')">
                    Download Test File
                </button>
                <button class="btn btn-secondary" onclick="viewStatus('${currentExcelId}')">
                    View Status
                </button>
                <button class="btn btn-secondary" onclick="downloadExcel('${currentExcelId}')">
                    Download Excel File
                </button>
            </div>
        `;
        
        if (data.warnings && data.warnings.length > 0) {
            html += '<div style="margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 8px;">';
            html += '<h4>Warnings:</h4><ul>';
            data.warnings.forEach(warning => {
                html += `<li>${warning}</li>`;
            });
            html += '</ul></div>';
        }
        
        resultsContent.innerHTML = html;
    }
    
    // Show message
    function showMessage(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = 'status-message ' + type;
        statusMessage.style.display = 'block';
    }
    
    // Hide message
    function hideMessage() {
        statusMessage.style.display = 'none';
    }
    
    // Download test file
    window.downloadTest = function(excelId) {
        window.location.href = `/api/excel/${excelId}/test`;
    };
    
    // View status
    window.viewStatus = async function(excelId) {
        try {
            const response = await fetch(`/api/excel/${excelId}/status`);
            const data = await response.json();
            
            if (response.ok) {
                alert(`Status: ${data.generation_status}\nFilename: ${data.filename}\nUploaded: ${data.uploaded_at}`);
            } else {
                alert('Error: ' + (data.error || 'Failed to get status'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };
    
    // Download Excel file
    window.downloadExcel = function(excelId) {
        window.location.href = `/api/excel/${excelId}/download`;
    };
});

