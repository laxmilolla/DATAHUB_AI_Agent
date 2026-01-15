"""
Table Verification Utilities
Helper functions for table column verification
"""


def find_column_index(headers, column_name):
    """
    Find column index by header text (exact match first, then partial match)
    
    Args:
        headers: List of header text strings (e.g., ["Name", "Age", "Diagnosis"])
        column_name: String to find (e.g., "Diagnosis")
    
    Returns:
        int: Column index (0-based) if found, -1 if not found
    
    Examples:
        >>> find_column_index(["Name", "Age", "Diagnosis"], "Diagnosis")
        2
        >>> find_column_index(["Name", "Primary Diagnosis"], "Diagnosis")
        1
        >>> find_column_index(["Name", "Age"], "Diagnosis")
        -1
    """
    column_index = -1
    
    # First try exact match (case-insensitive)
    for i, header in enumerate(headers):
        if column_name.lower() == header.lower().strip():
            column_index = i
            break
    
    # If no exact match, try partial match
    if column_index == -1:
        for i, header in enumerate(headers):
            if column_name.lower() in header.lower():
                column_index = i
                break
    
    return column_index
