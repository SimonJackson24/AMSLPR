
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Test runner script for the AMSLPR system.
"""

import os
import sys
import unittest
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_runner')

def discover_tests(test_type=None, test_pattern=None):
    """
    Discover tests to run.
    
    Args:
        test_type (str): Type of tests to run (unit, integration, or None for all)
        test_pattern (str): Pattern to match test files (default: test_*.py)
    
    Returns:
        unittest.TestSuite: Test suite containing discovered tests
    """
    # Get project root directory
    project_root = Path(__file__).resolve().parent
    
    # Set default pattern if not provided
    if test_pattern is None:
        test_pattern = 'test_*.py'
    
    # Discover tests
    if test_type == 'unit':
        start_dir = os.path.join(project_root, 'tests', 'unit')
    elif test_type == 'integration':
        start_dir = os.path.join(project_root, 'tests', 'integration')
    else:
        start_dir = os.path.join(project_root, 'tests')
    
    logger.info(f"Discovering tests in {start_dir} with pattern {test_pattern}")
    
    return unittest.defaultTestLoader.discover(start_dir, pattern=test_pattern)

def run_tests(test_suite):
    """
    Run tests.
    
    Args:
        test_suite (unittest.TestSuite): Test suite to run
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = runner.run(test_suite)
    
    # Return True if all tests passed
    return result.wasSuccessful()

def main():
    """
    Main function.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run tests for the AMSLPR system')
    parser.add_argument('--type', choices=['unit', 'integration'], help='Type of tests to run')
    parser.add_argument('--pattern', help='Pattern to match test files (default: test_*.py)')
    parser.add_argument('--production', action='store_true', help='Run only production-related tests')
    parser.add_argument('--skip-integration', action='store_true', help='Skip integration tests')
    args = parser.parse_args()
    
    # Handle production tests flag
    if args.production:
        if args.pattern:
            logger.warning("--pattern is ignored when --production is specified")
        args.pattern = 'test_*production*.py'
    
    # Discover tests
    test_suite = discover_tests(args.type, args.pattern)
    
    # Skip integration tests if requested
    if args.skip_integration:
        # Create a new test suite without integration tests
        filtered_suite = unittest.TestSuite()
        for test in test_suite:
            if 'integration' not in str(test):
                filtered_suite.addTest(test)
        test_suite = filtered_suite
    
    # Run tests
    success = run_tests(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
