#!/usr/bin/env python3
"""
Test runner script with comprehensive coverage reporting.
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)

    start_time = time.time()
    result = subprocess.run(cmd, cwd=os.getcwd())
    end_time = time.time()

    duration = end_time - start_time
    print(".2f")

    if result.returncode == 0:
        print("✓ PASSED")
    else:
        print("✗ FAILED")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Run VisiGate tests with coverage')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--performance', action='store_true', help='Run only performance tests')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--html', action='store_true', help='Generate HTML coverage report')
    parser.add_argument('--xml', action='store_true', help='Generate XML coverage report')
    parser.add_argument('--fail-under', type=int, default=95, help='Coverage failure threshold')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--parallel', '-n', type=int, help='Number of parallel workers')

    args = parser.parse_args()

    # Default to running all tests
    if not any([args.unit, args.integration, args.performance]):
        args.all = True

    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest']

    # Add test paths
    if args.unit or args.all:
        cmd.extend(['tests/unit/'])
    if args.integration or args.all:
        cmd.extend(['tests/integration/'])
    if args.performance:
        cmd.extend(['tests/performance/'])

    # Add coverage options
    if args.coverage or args.html or args.xml:
        cmd.extend(['--cov=src', f'--cov-fail-under={args.fail_under}'])

        if args.html:
            cmd.append('--cov-report=html:htmlcov')
        if args.xml:
            cmd.append('--cov-report=xml')
        if not (args.html or args.xml):
            cmd.append('--cov-report=term-missing')

    # Add other options
    if args.verbose:
        cmd.append('-v')
    if args.parallel:
        cmd.extend(['-n', str(args.parallel)])

    # Add markers for specific test types
    if args.unit:
        cmd.extend(['-m', 'unit'])
    elif args.integration:
        cmd.extend(['-m', 'integration'])
    elif args.performance:
        cmd.extend(['-m', 'performance'])

    # Run tests
    success = run_command(cmd, "Running tests with coverage")

    if success and (args.coverage or args.html or args.xml):
        print(f"\n{'='*60}")
        print("COVERAGE REPORT GENERATED")
        print('='*60)

        if args.html:
            htmlcov_path = Path('htmlcov/index.html')
            if htmlcov_path.exists():
                print(f"HTML report: file://{htmlcov_path.absolute()}")

        if args.xml:
            xml_path = Path('coverage.xml')
            if xml_path.exists():
                print(f"XML report: {xml_path.absolute()}")

    # Additional reporting
    if success:
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)

        # Count test files
        test_dirs = ['tests/unit', 'tests/integration', 'tests/performance']
        total_files = 0
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                files = list(Path(test_dir).glob('test_*.py'))
                total_files += len(files)
                print(f"{test_dir}: {len(files)} test files")

        print(f"Total test files: {total_files}")

        # Check for coverage files
        if Path('htmlcov').exists():
            print("✓ HTML coverage report generated")
        if Path('coverage.xml').exists():
            print("✓ XML coverage report generated")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
