#!/usr/bin/env python3
"""
Comprehensive final fix for ALL remaining AMSLPR references
Handles all 584 occurrences found by VSCode
"""

import os
import re
from pathlib import Path

# Directories to EXCLUDE (should never be modified)
EXCLUDE_DIRS = {
    '.git',
    '.idea',
    'venv',
    'venv_test',
    '__pycache__',
    'node_modules',
    '.pytest_cache',
}

# File extensions to process
INCLUDE_EXTENSIONS = {
    '.py', '.md', '.html', '.js', '.css', '.sh', '.service', 
    '.json', '.txt', '.yml', '.yaml', '.sql', '.xml', '.cfg',
    '.webmanifest', '.ts', '.tsx', '.jsx', '.ini', '.conf',
    '', # Files without extension
}

def should_process_file(filepath):
    """Check if file should be processed"""
    path = Path(filepath)
    
    # Check if in excluded directory
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    
    # Check extension
    if path.suffix in INCLUDE_EXTENSIONS or path.suffix == '':
        # Skip binary files
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                f.read(1024)
            return True
        except:
            return False
    
    return False

def process_file(filepath):
    """Process a single file and replace all AMSLPR occurrences"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all replacements
        # Keep migration docs references for context
        if 'MIGRATION_GUIDE' not in str(filepath) and 'REBRANDING_SUMMARY' not in str(filepath):
            # Basic replacements
            content = content.replace('AMSLPR', 'VisiGate')
            content = content.replace('amslpr', 'visigate')
            
            # Service-specific
            content = content.replace('Amslpr', 'Visigate')
            
            # URLs and repos
            content = re.sub(r'SimonJackson24/AMSLPR', 'SimonJackson24/VisiGate', content)
            content = re.sub(r'automatesystems/amslpr', 'visigate/visigate', content)
            
            # Paths
            content = re.sub(r'/home/simon/Projects/AMSLPR', '/home/simon/Projects/VisiGate', content)
            content = re.sub(r'/home/pi/AMSLPR', '/home/pi/VisiGate', content)
            content = re.sub(r'/home/automate/AMSLPR', '/home/automate/VisiGate', content)
            content = re.sub(r'visiongate-app/AMSLPR', 'visiongate-app/VisiGate', content)
            
            # Comments and strings
            content = re.sub(r'Automate Systems License Plate Recognition', 'Vision-Based Access Control System', content)
            content = re.sub(r'Automate Systems', 'VisiGate', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function"""
    print("=" * 70)
    print("COMPREHENSIVE VISIGATE REBRANDING - FINAL PASS")
    print("=" * 70)
    print()
    
    base_dir = Path('.')
    modified_files = []
    
    # Walk through all files
    for root, dirs, files in os.walk(base_dir):
        # Remove excluded directories from walk
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            if should_process_file(filepath):
                if process_file(filepath):
                    modified_files.append(filepath)
                    print(f"[UPDATED] {filepath}")
    
    print()
    print("=" * 70)
    print(f"COMPLETE! Modified {len(modified_files)} files.")
    print("=" * 70)
    print()
    print("Run a search for 'AMSLPR' to verify remaining occurrences.")
    print("Remaining occurrences should only be in:")
    print("  - Migration documentation (intentional)")
    print("  - Git history (.git directory)")
    print("  - IDE config (.idea directory)")

if __name__ == "__main__":
    main()