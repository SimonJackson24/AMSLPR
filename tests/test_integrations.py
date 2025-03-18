#!/usr/bin/env python3

"""
Test script for Paxton and Nayax integrations.

This script tests the Paxton and Nayax integrations by simulating API requests
to the integration endpoints.
"""

import argparse
import json
import requests
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import load_config


def test_paxton_integration(base_url, api_key, plate_number):
    """
    Test Paxton integration by sending a license plate to the Paxton API endpoint.
    
    Args:
        base_url (str): Base URL of the API
        api_key (str): API key for authentication
        plate_number (str): License plate number to test
    """
    print(f"\nTesting Paxton integration with plate number: {plate_number}")
    
    # Set up request headers and data
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key
    }
    data = {
        'plate_number': plate_number
    }
    
    # Send request to Paxton API endpoint
    url = f"{base_url}/api/paxton/process-plate"
    print(f"Sending request to: {url}")
    try:
        response = requests.post(url, headers=headers, json=data, verify=False)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Paxton integration test successful")
        else:
            print("❌ Paxton integration test failed")
    except Exception as e:
        print(f"❌ Error testing Paxton integration: {e}")


def test_nayax_payment(base_url, api_key, plate_number, amount, session_id):
    """
    Test Nayax payment integration by requesting a payment.
    
    Args:
        base_url (str): Base URL of the API
        api_key (str): API key for authentication
        plate_number (str): License plate number to test
        amount (float): Payment amount
        session_id (int): Parking session ID
    """
    print(f"\nTesting Nayax payment with plate number: {plate_number}, amount: {amount}")
    
    # Set up request headers and data
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key
    }
    data = {
        'plate_number': plate_number,
        'amount': amount,
        'session_id': session_id,
        'payment_location': 'exit'
    }
    
    # Send request to Nayax payment API endpoint
    url = f"{base_url}/api/nayax/request-payment"
    print(f"Sending request to: {url}")
    try:
        response = requests.post(url, headers=headers, json=data, verify=False)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Nayax payment request successful")
            
            # Check transaction status
            transaction_status_url = f"{base_url}/api/nayax/transaction-status"
            print(f"\nChecking transaction status at: {transaction_status_url}")
            status_response = requests.get(transaction_status_url, headers=headers, verify=False)
            print(f"Status response: {json.dumps(status_response.json(), indent=2)}")
            
            # Cancel transaction
            cancel_url = f"{base_url}/api/nayax/cancel-transaction"
            print(f"\nCancelling transaction at: {cancel_url}")
            cancel_response = requests.post(cancel_url, headers=headers, verify=False)
            print(f"Cancel response: {json.dumps(cancel_response.json(), indent=2)}")
        else:
            print("❌ Nayax payment request failed")
    except Exception as e:
        print(f"❌ Error testing Nayax payment: {e}")


def main():
    """
    Main entry point for the test script.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test Paxton and Nayax integrations')
    parser.add_argument('--config', help='Path to configuration file', default='config/config.json')
    parser.add_argument('--url', help='Base URL of the API', default='http://localhost:5000')
    parser.add_argument('--plate', help='License plate number to test', default='ABC123')
    parser.add_argument('--amount', help='Payment amount for Nayax test', type=float, default=10.50)
    parser.add_argument('--session', help='Session ID for Nayax test', type=int, default=123)
    parser.add_argument('--paxton', help='Test Paxton integration', action='store_true')
    parser.add_argument('--nayax', help='Test Nayax integration', action='store_true')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Get API key from configuration
    api_key = config.get('api', {}).get('key', 'test_api_key')
    
    print("=== AMSLPR Integration Tests ===")
    print(f"Base URL: {args.url}")
    print(f"API Key: {api_key}")
    
    # Test Paxton integration if requested
    if args.paxton:
        test_paxton_integration(args.url, api_key, args.plate)
    
    # Test Nayax integration if requested
    if args.nayax:
        test_nayax_payment(args.url, api_key, args.plate, args.amount, args.session)
    
    # If no specific test was requested, run all tests
    if not args.paxton and not args.nayax:
        test_paxton_integration(args.url, api_key, args.plate)
        test_nayax_payment(args.url, api_key, args.plate, args.amount, args.session)


if __name__ == '__main__':
    main()
