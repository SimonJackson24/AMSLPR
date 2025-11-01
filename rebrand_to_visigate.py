#!/usr/bin/env python3
"""
Comprehensive rebranding script: AMSLPR -> VisiGate
This script updates all occurrences of VisiGate branding throughout the codebase.
"""

import os
import re
from pathlib import Path

# Define replacement mappings
REPLACEMENTS = [
    # Copyright headers
    ("VisiGate - Vision-Based Access Control System", "VisiGate - Vision-Based Access Control System"),
    ("Copyright (c) 2025 VisiGate. All rights reserved.", "Copyright (c) 2025 VisiGate. All rights reserved."),
    ("Copyright (c) 2025 VisiGate. All rights reserved.", "Copyright (c) 2025 VisiGate. All rights reserved."),
    
    # Logger names
    ("'VisiGate.", "'VisiGate."),
    ('logger = logging.getLogger("VisiGate', 'logger = logging.getLogger("VisiGate'),
    
    # Environment variables
    ("VISIGATE_CONFIG", "VISIGATE_CONFIG"),
    ("VISIGATE_DATA_DIR", "VISIGATE_DATA_DIR"),
    ("VISIGATE_LOG_DIR", "VISIGATE_LOG_DIR"),
    ("VISIGATE_CONFIG_DIR", "VISIGATE_CONFIG_DIR"),
    ("VISIGATE_SALT_VALUE", "VISIGATE_SALT_VALUE"),
    
    # File paths
    ("/opt/visigate", "/opt/visigate"),
    ("/var/lib/visigate", "/var/lib/visigate"),
    ("/var/log/visigate", "/var/log/visigate"),
    ("/etc/visigate", "/etc/visigate"),
    ("/home/pi/VisiGate", "/home/pi/VisiGate"),
    ("/home/simon/Projects/VisiGate", "/home/simon/Projects/VisiGate"),
    ("/home/automate/VisiGate", "/home/automate/VisiGate"),
    
    # Service names
    ("visigate.service", "visigate.service"),
    ("systemctl restart visigate", "systemctl restart visigate"),
    ("systemctl start visigate", "systemctl start visigate"),
    ("systemctl stop visigate", "systemctl stop visigate"),
    ("systemctl status visigate", "systemctl status visigate"),
    
    # Package names
    ("name='visigate'", "name='visigate'"),
    
    # General branding (be careful with these - only in comments/strings)
    ("VisiGate System", "VisiGate System"),
    ("VisiGate API", "VisiGate API"),
    ("VisiGate application", "VisiGate application"),
    ("VisiGate web", "VisiGate web"),
    ("VisiGate project", "VisiGate project"),
    ("VisiGate service", "VisiGate service"),
    
    # Documentation
    ("# VisiGate", "# VisiGate"),
    ("## VisiGate", "## VisiGate"),
    ("the VisiGate", "the VisiGate"),
    ("The VisiGate", "The VisiGate"),
    
    # Template/HTML specific
    ("VisiGate - ", "VisiGate - "),
    ("- VisiGate", "- VisiGate"),
    (" VisiGate<", " VisiGate<"),
    (">VisiGate<", ">VisiGate<"),
    ("VisiGate Logo", "VisiGate Logo"),
    ("alt=\"AMSLPR", "alt=\"VisiGate"),
    ("title=\"AMSLPR", "title=\"VisiGate"),
    
    # Comments
    ("VisiGate - ", "VisiGate - "),
    ("for VisiGate", "for VisiGate"),
    ("for the VisiGate", "for the VisiGate"),
    ("in VisiGate", "in VisiGate"),
    ("of VisiGate", "of VisiGate"),
]

# Directories and file patterns to process
INCLUDE_PATTERNS = [
    "*.py",
    "*.md",
    "*.html",
    "*.js",
    "*.css",
    "*.sh",
    "*.service",
    "*.json",
    "*.txt",
    "*.yml",
    "*.yaml",
]

EXCLUDE_DIRS = [
    "venv",
    "venv_test",
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
]

def should_process_file(file_path):
    """Check if file should be processed."""
    # Exclude certain directories
    for exclude_dir in EXCLUDE_DIRS:
        if exclude_dir in file_path.parts:
            return False
    
    # Check if file matches include patterns
    for pattern in INCLUDE_PATTERNS:
        if file_path.match(pattern):
            return True
    
    return False

def apply_replacements(content, file_path):
    """Apply all replacements to content."""
    original_content = content
    
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    
    # Return modified flag along with content
    return content, content != original_content

def process_file(file_path):
    """Process a single file."""
    try:
        # Read file with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Apply replacements
        new_content, modified = apply_replacements(content, file_path)
        
        if modified:
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all files."""
    base_dir = Path(".")
    modified_files = []
    
    print("Starting VisiGate rebranding...")
    print("=" * 60)
    
    # Walk through all files
    for file_path in base_dir.rglob("*"):
        if file_path.is_file() and should_process_file(file_path):
            if process_file(file_path):
                modified_files.append(str(file_path))
                print(f"[OK] {file_path}")
    
    print("=" * 60)
    print(f"\nRebranding complete! Modified {len(modified_files)} files.")
    
    if modified_files:
        print("\nModified files:")
        for f in modified_files[:20]:  # Show first 20
            print(f"  - {f}")
        if len(modified_files) > 20:
            print(f"  ... and {len(modified_files) - 20} more")

if __name__ == "__main__":
    main()