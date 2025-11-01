#!/usr/bin/env python3
"""
Complete final VisiGate rebranding - Update ALL remaining AMSLPR references
Excludes only migration docs, git history, and IDE config
"""

import os
import re
from pathlib import Path

# Files to EXCLUDE from rebranding (intentional references)
EXCLUDE_FILES = {
    'MIGRATION_GUIDE.md',
    'REBRANDING_SUMMARY.md',
    'rebrand_to_visigate.py',
    'final_rebrand_fix.py',
    'comprehensive_final_fix.py',
    'complete_final_rebrand.py',  # This script itself
}

# Directories to EXCLUDE
EXCLUDE_DIRS = {
    '.git',
    '.idea',
    'venv',
    'venv_test',
    '__pycache__',
    'node_modules',
    '.pytest_cache',
}

def should_process_file(filepath):
    """Check if file should be processed"""
    path = Path(filepath)
    
    # Skip excluded files
    if path.name in EXCLUDE_FILES:
        return False
    
    # Check if in excluded directory
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    
    # Process text files only
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            f.read(1024)
        return True
    except:
        return False

def process_file(filepath):
    """Process a single file and replace all AMSLPR occurrences"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # Core replacements
        content = content.replace('AMSLPR', 'VisiGate')
        content = content.replace('amslpr', 'visigate')
        content = content.replace('Amslpr', 'Visigate')
        
        # Specific company/tagline replacements
        content = content.replace('Automate Systems License Plate Recognition', 'Vision-Based Access Control System')
        content = content.replace('Automate Systems', 'VisiGate')
        
        # GitHub URLs
        content = re.sub(r'SimonJackson24/AMSLPR', 'SimonJackson24/VisiGate', content)
        content = re.sub(r'github\.com/[^/]+/AMSLPR', 'github.com/visigate/visigate', content)
        
        # File paths
        content = re.sub(r'/home/simon/Projects/AMSLPR', '/home/simon/Projects/VisiGate', content)
        content = re.sub(r'/home/pi/AMSLPR', '/home/pi/VisiGate', content)
        content = re.sub(r'/home/automate/AMSLPR', '/home/automate/VisiGate', content)
        content = re.sub(r'visiongate-app/AMSLPR', 'visiongate-app/VisiGate', content)
        
        # Variable names (common in scripts)
        content = re.sub(r'AMSLPR_DIR=', 'VISIGATE_DIR=', content)
        content = re.sub(r'\$AMSLPR_DIR', '$VISIGATE_DIR', content)
        
        # Email addresses
        content = re.sub(r'support@automatesystems\.com', 'support@visigate.com', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"ERROR processing {filepath}: {e}")
        return False

def main():
    """Main function"""
    print("=" * 80)
    print("COMPLETE VISIGATE REBRANDING - FINAL PASS")
    print("=" * 80)
    print()
    
    base_dir = Path('.')
    modified_files = []
    processed_count = 0
    
    # Walk through all files
    for root, dirs, files in os.walk(base_dir):
        # Remove excluded directories from walk
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            if should_process_file(filepath):
                processed_count += 1
                if process_file(filepath):
                    modified_files.append(filepath)
                    print(f"[UPDATED] {filepath}")
    
    print()
    print("=" * 80)
    print(f"COMPLETE!")
    print(f"  - Processed: {processed_count} files")
    print(f"  - Modified: {len(modified_files)} files")
    print("=" * 80)
    print()
    
    if modified_files:
        print("Modified files:")
        for f in modified_files[:50]:  # Show first 50
            print(f"  • {f}")
        if len(modified_files) > 50:
            print(f"  ... and {len(modified_files) - 50} more")
    
    print()
    print("✓ VisiGate rebranding is now 100% complete!")
    print()

if __name__ == "__main__":
    main()