"""
File Upload Handler - Handle file upload operations
Similar to TOTP handler, but for file uploads
"""
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class FileUploadHandler:
    """Handle file upload operations"""
    
    def __init__(self):
        """Initialize file upload handler"""
        pass
    
    def is_file_upload_step(self, step_text: str, functions: str = None) -> bool:
        """
        Detect if step is file upload-related
        Args:
            step_text: Step text description
            functions: Functions column value from Excel
        Returns: True if this is a file upload step
        """
        if functions and 'file' in str(functions).lower() and 'upload' in str(functions).lower():
            return True
        
        file_upload_keywords = ["file upload", "upload file", "choose file", "select file", "browse file"]
        step_has_upload = any(keyword in step_text.lower() for keyword in file_upload_keywords)
        return step_has_upload
    
    def parse_file_upload_params(self, functions: str = None, text_value: str = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse location and filename from Functions or Text Value
        Supports formats:
        - Functions: "File Upload:location:filename" or "File Upload|location|filename"
        - Text Value: "location|filename" or "location:filename"
        - Functions: "File Upload" with Text Value containing path
        
        Args:
            functions: Functions column value
            text_value: Text Value column value
        Returns: (location, filename) tuple
        """
        location = None
        filename = None
        
        # Try parsing from Functions column: "File Upload:location:filename" or "File Upload|location|filename"
        if functions:
            func_str = str(functions).strip()
            if 'file upload' in func_str.lower():
                # Check for colon or pipe separator
                if ':' in func_str:
                    parts = func_str.split(':')
                    if len(parts) >= 3:
                        location = parts[1].strip()
                        filename = parts[2].strip()
                elif '|' in func_str:
                    parts = func_str.split('|')
                    if len(parts) >= 3:
                        location = parts[1].strip()
                        filename = parts[2].strip()
        
        # If not found in Functions, try Text Value: "location|filename" or "location:filename"
        if not location and not filename and text_value:
            text_str = str(text_value).strip()
            # Remove ${} wrapper if present
            text_str = text_str.replace('${', '').replace('}', '')
            
            if '|' in text_str:
                parts = text_str.split('|')
                if len(parts) >= 2:
                    location = parts[0].strip()
                    filename = parts[1].strip()
            elif ':' in text_str:
                parts = text_str.split(':')
                if len(parts) >= 2:
                    location = parts[0].strip()
                    filename = parts[1].strip()
            elif '/' in text_str or '\\' in text_str:
                # Full path provided - extract location and filename
                from pathlib import Path
                path = Path(text_str)
                filename = path.name
                location = str(path.parent)
        
        return location, filename
    
    def get_file_path(self, location: str, filename: str, project_root: Optional[Path] = None) -> Path:
        """
        Get full file path from location and filename
        Args:
            location: Directory location (relative to project root or absolute)
            filename: Name of file to upload
            project_root: Project root directory (optional, defaults to current working directory)
        Returns: Full Path object to the file
        """
        if not location:
            raise ValueError("Location is required for file upload")
        
        # If location is absolute, use it directly
        if os.path.isabs(location):
            folder_path = Path(location)
        else:
            # Relative path - resolve from project root or current directory
            if project_root:
                folder_path = project_root / location
            else:
                # Default to current working directory
                folder_path = Path(location)
        
        # Resolve to absolute path
        folder_path = folder_path.resolve()
        
        # If filename is empty, "*", or "all", upload all files in folder
        if not filename or filename.strip() in ['*', 'all', 'ALL']:
            # Return folder path - caller will handle getting all files
            if not folder_path.exists():
                raise FileNotFoundError(f"Folder does not exist: {folder_path}")
            if not folder_path.is_dir():
                raise ValueError(f"Path is not a directory: {folder_path}")
            return folder_path
        
        # Single file upload
        file_path = folder_path / filename
        
        # Verify file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"  [FILE_UPLOAD] Resolved file path: {file_path}")
        return file_path
    
    def get_all_files_in_folder(self, folder_path: Path, extensions: Optional[list] = None) -> List[Path]:
        """
        Get all files in a folder, optionally filtered by extensions
        Args:
            folder_path: Path to folder
            extensions: Optional list of extensions to filter (e.g., ['.xlsx', '.csv'])
        Returns: List of file paths
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")
        
        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
        
        all_files = []
        for item in folder_path.iterdir():
            if item.is_file():
                if extensions:
                    if item.suffix.lower() in [ext.lower() for ext in extensions]:
                        all_files.append(item)
                else:
                    all_files.append(item)
        
        # Sort files by name for consistent ordering
        all_files.sort(key=lambda x: x.name)
        
        logger.info(f"  [FILE_UPLOAD] Found {len(all_files)} files in folder: {folder_path}")
        return all_files
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate that file exists and is readable
        Args:
            file_path: Path to file
        Returns: (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        if not os.access(file_path, os.R_OK):
            return False, f"File is not readable: {file_path}"
        
        return True, ""
