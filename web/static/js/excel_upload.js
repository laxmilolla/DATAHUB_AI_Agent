// Excel Upload JavaScript
// Handles Excel file upload, validation, and test generation

document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    // Support both excel_upload.html and index.html
    const statusMessage = document.getElementById('excelStatusMessage') || document.getElementById('statusMessage');
    const validationResults = document.getElementById('validationResults');
    const validationContent = document.getElementById('validationContent');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    const testFilesInput = document.getElementById('testFilesInput');
    const testFilesInfo = document.getElementById('testFilesInfo');
    const expectedFilesInfo = document.getElementById('expectedFilesInfo');
    const expectedFilesList = document.getElementById('expectedFilesList');
    
    // Debug: Log element availability
    console.log('🔍 UI Elements check:', {
        statusMessage: !!statusMessage,
        validationResults: !!validationResults,
        validationContent: !!validationContent,
        uploadBtn: !!uploadBtn,
        testFilesInput: !!testFilesInput
    });
    
    let currentExcelId = null;
    let uploadedFile = null;
    let testFiles = [];
    let expectedFilePaths = [];
    
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
        testFiles = [];
        expectedFilePaths = [];
        if (testFilesInput) testFilesInput.value = '';
        if (testFilesInfo) testFilesInfo.textContent = '';
        if (expectedFilesInfo) expectedFilesInfo.style.display = 'none';
        const generateTsBtn = document.getElementById('generateTsBtn');
        if (generateTsBtn) generateTsBtn.disabled = true;
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
    
    // Generate TypeScript button handler
    const generateTsBtn = document.getElementById('generateTsBtn');
    
    if (generateTsBtn) {
        generateTsBtn.addEventListener('click', async () => {
            if (!currentExcelId) {
                showMessage('Please upload and validate a file first', 'error');
                return;
            }
            
            await generateTestTS();
        });
    } else {
        console.error('❌ generateTsBtn NOT FOUND!');
    }
    
    // Download template button handler
    downloadTemplateBtn.addEventListener('click', () => {
        window.location.href = '/api/excel/template?include_examples=true';
    });
    
    // Handle test files selection
    if (testFilesInput) {
        testFilesInput.addEventListener('change', (e) => {
            testFiles = Array.from(e.target.files);
            if (testFiles.length > 0) {
                const fileNames = testFiles.map(f => f.name).join(', ');
                if (testFilesInfo) {
                    testFilesInfo.textContent = `Selected: ${testFiles.length} file(s) - ${fileNames}`;
                }
            } else {
                if (testFilesInfo) testFilesInfo.textContent = '';
            }
        });
    }
    
    // Upload file
    async function uploadFile() {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        
        // Add test files if selected
        if (testFiles && testFiles.length > 0) {
            testFiles.forEach(file => {
                formData.append('test_files', file);
            });
        }
        
        // Disable button and show loading
        uploadBtn.disabled = true;
        const uploadBtnText = uploadBtn.querySelector('.btn-text');
        const uploadBtnLoading = uploadBtn.querySelector('.btn-loading');
        if (uploadBtnText) uploadBtnText.style.display = 'none';
        if (uploadBtnLoading) uploadBtnLoading.style.display = 'inline-block';
        
        hideMessage();
        if (validationResults) validationResults.style.display = 'none';
        
        try {
            console.log('📤 Starting file upload...', uploadedFile?.name);
            const response = await fetch('/api/excel/upload', {
                method: 'POST',
                body: formData
            });
            
            console.log('📥 Response received:', response.status, response.statusText);
            
            let data;
            try {
                data = await response.json();
                console.log('📦 Response data:', data);
            } catch (jsonError) {
                const text = await response.text();
                console.error('❌ Failed to parse JSON response:', text);
                showMessage('Server error: Invalid response format', 'error');
                return;
            }
            
            // Show validation results even if upload failed (400 status)
            if (data.validation) {
                displayValidationResults(data.validation);
            }
            
            // Show validation summary if available (includes detailed XPath mismatches)
            if (data.validation_summary) {
                displayValidationSummary(data.validation_summary);
            }
            
            if (!response.ok) {
                // Show error message but keep validation results visible
                const errorMsg = data.error || 'Upload failed';
                showMessage('Upload failed: ' + errorMsg, 'error');
                currentExcelId = null;
                const generateTsBtn = document.getElementById('generateTsBtn');
                if (generateTsBtn) generateTsBtn.disabled = true;
                return; // Exit early, don't throw - validation results are already displayed
            }
            
            currentExcelId = data.excel_id;
            
            // Show test files upload status if available
            if (data.test_files_upload) {
                const uploadResult = data.test_files_upload;
                
                // Show expected file paths from Excel
                expectedFilePaths = uploadResult.referenced_paths || [];
                if (expectedFilePaths && expectedFilePaths.length > 0) {
                    const expectedFilesMsg = `📁 Excel expects ${expectedFilePaths.length} file path(s):\n${expectedFilePaths.map(p => `  • ${p}`).join('\n')}`;
                    console.log(expectedFilesMsg);
                    
                    // Display expected files/folders in UI
                    if (expectedFilesInfo && expectedFilesList) {
                        expectedFilesInfo.style.display = 'block';
                        expectedFilesList.innerHTML = expectedFilePaths.map(path => {
                            const isFolder = path.endsWith('/');
                            if (isFolder) {
                                const folderName = path.replace(/\/$/, '').split('/').pop() || path;
                                return `<li>📁 <strong>Folder:</strong> <code style="background: #fff; padding: 2px 6px; border-radius: 3px;">${folderName}/</code> <span style="color: #856404;">(${path})</span><br><span style="font-size: 0.85em; color: #6B5B3D; margin-left: 20px;">Upload multiple files - they will be saved to this folder</span></li>`;
                            } else {
                                const filename = path.split('/').pop();
                                return `<li>📄 <strong>File:</strong> <code style="background: #fff; padding: 2px 6px; border-radius: 3px;">${filename}</code> <span style="color: #856404;">(${path})</span></li>`;
                            }
                        }).join('');
                    }
                    
                    // Check if any path is a folder
                    const hasFolderPath = expectedFilePaths.some(p => p.endsWith('/'));
                    
                    // Show in UI if files were renamed or saved to folder
                    if (uploadResult.renamed && uploadResult.renamed.length > 0) {
                        uploadResult.renamed.forEach(rename => {
                            const renameMsg = `✅ Automatically renamed "${rename.original}" → "${rename.renamed_to}" to match Excel reference`;
                            console.log(renameMsg);
                            showMessage(`✅ File renamed: "${rename.original}" → "${rename.renamed_to}"`, 'success');
                        });
                    } else if (hasFolderPath && uploadResult.uploaded && uploadResult.uploaded.length > 0) {
                        // Show success message for folder uploads
                        const folderPath = expectedFilePaths.find(p => p.endsWith('/'));
                        showMessage(`✅ Uploaded ${uploadResult.uploaded.length} file(s) to folder: ${folderPath}`, 'success');
                    } else if (expectedFilePaths.length === 1 && (!uploadResult.uploaded || uploadResult.uploaded.length === 0)) {
                        // Show info if Excel expects a file/folder but none was uploaded
                        const expectedPath = expectedFilePaths[0];
                        const isFolder = expectedPath.endsWith('/');
                        const msg = isFolder 
                            ? `ℹ️ Excel expects files in folder: ${expectedPath}. Upload files in the "Test Files" section above.`
                            : `ℹ️ Excel expects file: ${expectedPath}. Upload it in the "Test Files" section above.`;
                        showMessage(msg, 'info');
                    }
                } else {
                    // Hide expected files section if none
                    if (expectedFilesInfo) expectedFilesInfo.style.display = 'none';
                }
                
                if (uploadResult.uploaded && uploadResult.uploaded.length > 0) {
                    const uploadedMsg = `✅ Uploaded ${uploadResult.uploaded.length} test file(s) to server`;
                    console.log(uploadedMsg, uploadResult.uploaded);
                }
                if (uploadResult.errors && uploadResult.errors.length > 0) {
                    console.warn('⚠️ Test file upload errors:', uploadResult.errors);
                    uploadResult.errors.forEach(error => {
                        showMessage(`❌ ${error}`, 'error');
                    });
                }
            }
            
            if (data.success) {
                let successMsg = 'File uploaded and validated successfully!';
                if (data.test_files_upload && data.test_files_upload.uploaded && data.test_files_upload.uploaded.length > 0) {
                    successMsg += ` ${data.test_files_upload.uploaded.length} test file(s) uploaded.`;
                }
                showMessage(successMsg, 'success');
                const generateTsBtn = document.getElementById('generateTsBtn');
                if (generateTsBtn) generateTsBtn.disabled = false;
            } else {
                showMessage('File uploaded but validation failed. Check validation results below.', 'error');
            }
            
        } catch (error) {
            console.error('❌ Upload error:', error);
            showMessage('Upload failed: ' + error.message, 'error');
            currentExcelId = null;
            const generateTsBtn = document.getElementById('generateTsBtn');
            if (generateTsBtn) generateTsBtn.disabled = true;
        } finally {
            uploadBtn.disabled = false;
            const uploadBtnText = uploadBtn.querySelector('.btn-text');
            const uploadBtnLoading = uploadBtn.querySelector('.btn-loading');
            if (uploadBtnText) uploadBtnText.style.display = 'inline';
            if (uploadBtnLoading) uploadBtnLoading.style.display = 'none';
        }
    }
    
    // Generate TypeScript test
    async function generateTestTS() {
        if (!currentExcelId) {
            showMessage('No file uploaded', 'error');
            return;
        }
        
        const generateTsBtn = document.getElementById('generateTsBtn');
        if (!generateTsBtn) return;
        
        // Disable button and show loading
        generateTsBtn.disabled = true;
        const generateTsBtnText = generateTsBtn.querySelector('.btn-text');
        const generateTsBtnLoading = generateTsBtn.querySelector('.btn-loading');
        if (generateTsBtnText) generateTsBtnText.style.display = 'none';
        if (generateTsBtnLoading) generateTsBtnLoading.style.display = 'inline-block';
        
        hideMessage();
        
        try {
            const response = await fetch('/api/excel/generate-ts', {
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
                throw new Error(data.error || 'TypeScript generation failed');
            }
            
            if (data.success) {
                // If execution_id is provided, redirect to results page (same as Python tests)
                if (data.execution_id || data.results_url) {
                    showMessage('TypeScript test generated! Running test and capturing screenshots...', 'success');
                    
                    // Redirect to results page after a short delay
                    const resultsUrl = data.results_url || `/results/${data.execution_id}`;
                    setTimeout(() => {
                        window.location.href = resultsUrl;
                    }, 1500);
                } else {
                    // Fallback: Show download link if no execution_id (test not running)
                    showMessage('TypeScript test generated successfully!', 'success');
                    
                    // Show zip download link (preferred - includes all files)
                    if (data.zip_download_url) {
                        const downloadLink = document.createElement('a');
                        downloadLink.href = data.zip_download_url;
                        downloadLink.download = data.test_name + '_typescript_complete.zip';
                        downloadLink.textContent = '📦 Download TypeScript Test (Complete Package)';
                        downloadLink.className = 'btn btn-primary';
                        downloadLink.style.marginTop = '10px';
                        downloadLink.style.display = 'inline-block';
                        
                        // Remove existing download link if any
                        const existingLink = document.getElementById('ts-download-link');
                        if (existingLink) {
                            existingLink.remove();
                        }
                        
                        downloadLink.id = 'ts-download-link';
                        
                        // Append to results section or status message area
                        const statusMessage = document.getElementById('statusMessage');
                        if (statusMessage) {
                            statusMessage.appendChild(document.createElement('br'));
                            statusMessage.appendChild(downloadLink);
                        } else if (resultsSection) {
                            resultsSection.style.display = 'block';
                            const resultsContent = document.getElementById('resultsContent');
                            if (resultsContent) {
                                resultsContent.innerHTML = '<p>TypeScript test generated successfully! Download the complete package (includes .spec.ts, package.json, README, and registry files).</p>';
                                resultsContent.appendChild(downloadLink);
                            }
                        }
                    }
                }
            } else {
                let errorMsg = data.error;
                if (!errorMsg && data.errors && data.errors.length > 0) {
                    errorMsg = Array.isArray(data.errors) ? data.errors.join('; ') : data.errors;
                }
                showMessage('TypeScript generation failed: ' + (errorMsg || 'Unknown error'), 'error');
            }
            
        } catch (error) {
            showMessage('TypeScript generation failed: ' + error.message, 'error');
        } finally {
            generateTsBtn.disabled = false;
            const generateTsBtnText = generateTsBtn.querySelector('.btn-text');
            const generateTsBtnLoading = generateTsBtn.querySelector('.btn-loading');
            if (generateTsBtnText) generateTsBtnText.style.display = 'inline';
            if (generateTsBtnLoading) generateTsBtnLoading.style.display = 'none';
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
        
        // Display XPath registry validation details
        if (validation.xpath_validation) {
            const xpathVal = validation.xpath_validation;
            const mismatches = xpathVal.xpath_mismatches || [];
            const totalChecked = xpathVal.total_checked || 0;
            const totalRegistries = xpathVal.total_registries || 0;
            
            if (totalChecked > 0) {
                validationContent.innerHTML += '<h5 style="margin-top: 15px; color: #dc3545;">🔍 XPath Registry Validation:</h5>';
                validationContent.innerHTML += `<p><strong>Total XPaths checked:</strong> ${totalChecked}</p>`;
                validationContent.innerHTML += `<p><strong>Registries searched:</strong> ${totalRegistries}</p>`;
                validationContent.innerHTML += `<p><strong>XPaths not found in registry:</strong> <span style="color: #dc3545; font-weight: 600;">${mismatches.length}</span></p>`;
                
                if (mismatches.length > 0) {
                    validationContent.innerHTML += '<h6 style="margin-top: 10px; color: #dc3545;">⚠️ XPaths not matching registry:</h6>';
                    mismatches.forEach((mismatch, index) => {
                        const step = mismatch.step || 'N/A';
                        const desc = mismatch.element_description || 'N/A';
                        const xpath = mismatch.xpath || 'N/A';
                        validationContent.innerHTML += `
                            <div style="margin: 8px 0; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 4px;">
                                <strong>Step ${step}:</strong> ${desc}<br>
                                <code style="font-size: 0.85em; color: #856404; word-break: break-all;">${xpath}</code>
                            </div>
                        `;
                    });
                } else {
                    validationContent.innerHTML += '<p style="color: #28a745;">✅ All XPaths found in registry!</p>';
                }
            }
        }
    }
    
    // Display validation summary (formatted text summary from backend)
    function displayValidationSummary(summary) {
        if (!validationResults || !validationContent) return;
        validationResults.style.display = 'block';
        
        // Convert summary text to HTML (preserve line breaks and formatting)
        const summaryHtml = summary
            .split('\n')
            .map(line => {
                // Bold headers
                if (line.match(/^(✅|❌|📊|⚠️|🔍)/)) {
                    return `<p style="font-weight: 600; margin: 8px 0;">${line}</p>`;
                }
                // Indented items
                if (line.match(/^\s{2,}[•·]/)) {
                    return `<div style="margin-left: 20px; margin: 4px 0;">${line.trim()}</div>`;
                }
                // Regular lines
                if (line.trim()) {
                    return `<p style="margin: 4px 0;">${line}</p>`;
                }
                return '';
            })
            .join('');
        
        // Append summary to validation content
        if (validationContent.innerHTML) {
            validationContent.innerHTML += '<hr style="margin: 20px 0; border: 1px solid #ddd;">';
            validationContent.innerHTML += '<h5 style="margin-top: 15px;">Detailed Validation Summary:</h5>';
        }
        validationContent.innerHTML += summaryHtml;
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
        console.log('💬 showMessage called:', message, type);
        if (statusMessage) {
            statusMessage.textContent = message;
            statusMessage.className = 'status-message ' + type;
            statusMessage.style.display = 'block';
            console.log('✅ Message displayed in UI');
        } else {
            console.error('❌ statusMessage element not found!');
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

