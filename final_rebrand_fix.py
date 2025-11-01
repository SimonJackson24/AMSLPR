#!/usr/bin/env python3
"""
Final comprehensive fix for remaining AMSLPR references
"""

import os
from pathlib import Path

# Specific file updates
SPECIFIC_FIXES = {
    'src/utils/notifications.py': [
        ('AMSLPR Alert:', 'VisiGate Alert:'),
    ],
    'src/utils/helpers.py': [
        ("return logging.getLogger('AMSLPR')", "return logging.getLogger('VisiGate')"),
    ],
    'src/web/ssl.py': [
        ('cert.get_subject().O = "AMSLPR"', 'cert.get_subject().O = "VisiGate"'),
    ],
    'src/web/static/css/style.css': [
        ('/* AMSLPR Professional Design System */', '/* VisiGate Professional Design System */'),
        ('/* AMSLPR Custom Styles */', '/* VisiGate Custom Styles */'),
    ],
    'src/web/static/js/main.js': [
        ('// AMSLPR Main JavaScript', '// VisiGate Main JavaScript'),
    ],
    'src/web/static/img/favicon/site.webmanifest': [
        ('"name": "AMSLPR"', '"name": "VisiGate"'),
        ('"short_name": "AMSLPR"', '"short_name": "VisiGate"'),
    ],
    'src/web/system_routes.py': [
        ("config['system_name'] = request.form.get('system_name', 'AMSLPR')", "config['system_name'] = request.form.get('system_name', 'VisiGate')"),
    ],
    'src/web/templates/reports.html': [
        ('Generate and download reports for your AMSLPR system.', 'Generate and download reports for your VisiGate system.'),
    ],
    'src/database/schema.sql': [
        ('-- AMSLPR Database Schema', '-- VisiGate Database Schema'),
    ],
    'run_debug.py': [
        ('logger.info("Starting AMSLPR in debug mode")', 'logger.info("Starting VisiGate in debug mode")'),
    ],
    'run_tests.py': [
        ("description='Run AMSLPR tests with coverage'", "description='Run VisiGate tests with coverage'"),
    ],
    'tests/test_integrations.py': [
        ('print("=== AMSLPR Integration Tests ===")', 'print("=== VisiGate Integration Tests ===")'),
    ],
    'tests/unit/test_ssl_configuration.py': [
        ('x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AMSLPR Test")', 'x509.NameAttribute(NameOID.ORGANIZATION_NAME, "VisiGate Test")'),
    ],
    'parking.html': [
        ('AMSLPR', 'VisiGate'),
    ],
    'dashboard.html': [
        ('AMSLPR', 'VisiGate'),
    ],
    'amslpr.service': [
        ('Description=AMSLPR Camera System', 'Description=VisiGate Camera System'),
    ],
    'docker-entrypoint.sh': [
        ('echo "Starting AMSLPR on port $PORT"', 'echo "Starting VisiGate on port $PORT"'),
    ],
    'apply_camera_fix.sh': [
        ('echo "AMSLPR Camera Routes Emergency Fix"', 'echo "VisiGate Camera Routes Emergency Fix"'),
        ('AMSLPR_DIR=', 'VISIGATE_DIR='),
        ('Could not find AMSLPR installation', 'Could not find VisiGate installation'),
        ('path to your AMSLPR installation', 'path to your VisiGate installation'),
        ('Using AMSLPR installation at', 'Using VisiGate installation at'),
    ],
    'diagnostic_script.py': [
        ('logger.info("Starting AMSLPR diagnostics")', 'logger.info("Starting VisiGate diagnostics")'),
    ],
    'deploy-no-docker.sh': [
        ('Description=VisionGate AMSLPR Service', 'Description=VisionGate Service'),
        ('WorkingDirectory=/home/visiongate/visiongate-app/AMSLPR', 'WorkingDirectory=/home/visiongate/visiongate-app/VisiGate'),
        ('Environment=PYTHONPATH=/home/visiongate/visiongate-app/AMSLPR', 'Environment=PYTHONPATH=/home/visiongate/visiongate-app/VisiGate'),
        ('ExecStart=/usr/bin/python3 /home/visiongate/visiongate-app/AMSLPR/run_server.py', 'ExecStart=/usr/bin/python3 /home/visiongate/visiongate-app/VisiGate/run_server.py'),
    ],
}

def apply_fix(filepath, replacements):
    """Apply replacements to a file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        for old, new in replacements:
            content = content.replace(old, new)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

def main():
    """Main function"""
    print("Applying final AMSLPR -> VisiGate fixes...")
    print("=" * 60)
    
    modified_count = 0
    for filepath, replacements in SPECIFIC_FIXES.items():
        if os.path.exists(filepath):
            if apply_fix(filepath, replacements):
                print(f"[OK] {filepath}")
                modified_count += 1
        else:
            print(f"[SKIP] {filepath} (not found)")
    
    print("=" * 60)
    print(f"Final fix complete! Modified {modified_count} files.")

if __name__ == "__main__":
    main()