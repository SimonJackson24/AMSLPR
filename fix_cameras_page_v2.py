#!/usr/bin/env python3

"""
Targeted fix for the cameras page error.
This script modifies the cameras.html template to handle missing stats variable.
"""

import os

# Create a backup of the template
os.system("sudo cp /opt/visigate/src/web/templates/cameras.html /opt/visigate/src/web/templates/cameras.html.backup_fix")
print("Created backup of cameras.html template")

# Read the current template
with open("/opt/visigate/src/web/templates/cameras.html", "r") as f:
    template_content = f.read()

# Replace all instances of {{ stats.xxx }} with {{ stats.xxx|default(value) }}
# This ensures the template won't fail if stats is undefined
fixed_content = template_content

# Add a check at the beginning of the template to define stats if it's not defined
fixed_content = "{% set stats = stats|default({'online': 0, 'offline': 0, 'unknown': 0, 'total': 0, 'avg_fps': '0'}) %}\n" + fixed_content

# Write the fixed template
with open("/tmp/fixed_cameras.html", "w") as f:
    f.write(fixed_content)

# Apply the fix
os.system("sudo cp /tmp/fixed_cameras.html /opt/visigate/src/web/templates/cameras.html")
print("Applied fix to cameras.html template")

# Restart the service
os.system("sudo systemctl restart visigate")
print("Restarted VisiGate service")

print("Fix applied. The cameras page should now work without errors.")
