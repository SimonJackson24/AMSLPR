
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

'''
Script to update the admin password to 'admin123'
'''

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the user manager
from src.utils.user_management import UserManager

def main():
    # Create user manager instance
    user_manager = UserManager()
    
    # Update admin password
    success = user_manager.update_user('admin', password='admin123')
    
    if success:
        print("✅ Admin password successfully updated to 'admin123'")
    else:
        print("❌ Failed to update admin password")

if __name__ == '__main__':
    main()
