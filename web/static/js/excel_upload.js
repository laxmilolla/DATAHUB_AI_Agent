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
    // Support both excel_upload.html and index.html
    const statusMessage = document.getElementById('excelStatusMessage') || document.getElementById('statusMessage');
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
        if (fileName) fileName.textContent = file.name;
        if (fileInfo) fileInfo.style.display = 'block';
        uploadBtn.disabled = false;
        
        // Reset state
        currentExcelId = null;
        generateBtn.disabled = true;
        if (validationResults) validationResults.style.display = 'none';
        if (resultsSection) resultsSection.style.display = 'none';
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
        const uploadBtnText = uploadBtn.querySelector('.btn-text');
        const uploadBtnLoading = uploadBtn.querySelector('.btn-loading');
        if (uploadBtnText) uploadBtnText.style.display = 'none';
        if (uploadBtnLoading) uploadBtnLoading.style.display = 'inline-block';
        
        hideMessage();
        if (validationResults) validationResults.style.display = 'none';
        
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
            const uploadBtnText = uploadBtn.querySelector('.btn-text');
            const uploadBtnLoading = uploadBtn.querySelector('.btn-loading');
            if (uploadBtnText) uploadBtnText.style.display = 'inline';
            if (uploadBtnLoading) uploadBtnLoading.style.display = 'none';
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
        const generateBtnText = generateBtn.querySelector('.btn-text');
        const generateBtnLoading = generateBtn.querySelector('.btn-loading');
        if (generateBtnText) generateBtnText.style.display = 'none';
        if (generateBtnLoading) generateBtnLoading.style.display = 'inline-block';
        
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
                showMessage('Test generated successfully!', 'success');
                
                // If execution_id is provided, redirect to results page (main page integration)
                if (data.execution_id) {
                    // Refresh executions list if loadExecutions function exists (on main page)
                    if (typeof loadExecutions === 'function') {
                        setTimeout(() => {
                            loadExecutions();
                        }, 1000);
                    }
                    // Redirect to results page after a short delay
                    setTimeout(() => {
                        window.location.href = `/results/${data.execution_id}`;
                    }, 2000);
                } else if (resultsSection) {
                    // Show results section if on excel_upload.html page
                    displayResults(data);
                }
            } else {
                showMessage('Generation failed: ' + (data.error || 'Unknown error'), 'error');
            }
            
        } catch (error) {
            showMessage('Generation failed: ' + error.message, 'error');
        } finally {
            generateBtn.disabled = false;
            const generateBtnText = generateBtn.querySelector('.btn-text');
            const generateBtnLoading = generateBtn.querySelector('.btn-loading');
            if (generateBtnText) generateBtnText.style.display = 'inline';
            if (generateBtnLoading) generateBtnLoading.style.display = 'none';
        }
    }
    
    // Display validation results
    function displayValidationResults(validation) {
        if (!validationResults || !validationContent) return;
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
        if (!resultsSection || !resultsContent) return;
        resultsSection.style.display = 'block';
        
        let html = `
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #28a745;">✅ Test Generated Successfully</h3>
                <p><strong>Test Name:</strong> ${data.test_name || 'N/A'}</p>
                <p><strong>Rows Processed:</strong> ${data.rows_processed || 0}</p>
                <p><strong>Generated At:</strong> ${new Date(data.generated_at).toLocaleString()}</p>
            </div>
            
            <div class="action-buttons">
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
        if (statusMessage) {
            statusMessage.textContent = message;
            statusMessage.className = 'status-message ' + type;
            statusMessage.style.display = 'block';
        }
    }
    
    // Hide message
    function hideMessage() {
        if (statusMessage) {
            statusMessage.style.display = 'none';
        }
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

