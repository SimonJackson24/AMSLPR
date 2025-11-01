#!/bin/bash

# Script to add license notices to all Python files

LICENSE_NOTICE="""
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.
"""

find /home/simon/Projects/VisiGate -name "*.py" | while read file; do
    # Skip files in venv directories
    if [[ $file == *"/venv/"* || $file == *"/venv_test/"* ]]; then
        continue
    fi
    
    # Check if file already has a license notice
    if grep -q "Copyright (c) 2025 VisiGate. All rights reserved." "$file"; then
        echo "License notice already exists in $file"
        continue
    fi
    
    echo "Adding license notice to $file"
    
    # Create a temporary file
    temp_file=$(mktemp)
    
    # Add license notice and original content to temporary file
    echo "$LICENSE_NOTICE" > "$temp_file"
    cat "$file" >> "$temp_file"
    
    # Replace original file with temporary file
    mv "$temp_file" "$file"
done

echo "License notices added to all Python files"
