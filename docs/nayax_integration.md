# Nayax Payment Terminal Integration

## Overview

This document describes the integration between the VisiGate system and Nayax Onyx payment terminals for processing parking payments.

## Features

- Support for both serial and TCP/IP connections to Nayax terminals
- Real-time payment processing
- Transaction status monitoring
- Payment cancellation
- Comprehensive transaction logging
- Flexible car park operating modes

## Car Park Operating Modes

The VisiGate system supports different car park operating modes that affect how the Nayax payment terminal is used:

### Entry/Exit Mode

- **Single Camera**: A single camera automatically detects whether a vehicle is entering or exiting based on whether there's an active session for the license plate.
- **Dual Camera**: Separate cameras are used for entry and exit points, with each camera having a predefined role.

### Payment Requirements

- **Always**: Payment is always required to exit the car park.
- **After Grace Period**: Payment is only required if the vehicle has stayed beyond the configured grace period.
- **Never**: No payment is required (free parking).

### Payment Location

- **At Exit**: Payment is processed at the exit barrier using a Nayax terminal installed there.
- **Pay Station**: Payment is processed at a separate pay station before the vehicle approaches the exit.

## Configuration

The Nayax integration can be configured through the web interface under Parking → Settings or directly in the configuration file. The following settings are available:

### Car Park Settings

- **Operating Mode**: Set to "Parking Management" to enable parking features and Nayax integration
- **Entry/Exit Mode**: Single Camera or Dual Camera
- **Payment Required for Exit**: Always, After Grace Period, or Never
- **Payment Location**: At Exit or Pay Station

### Nayax Terminal Settings

- **Enabled**: Enable or disable Nayax integration
- **Connection Type**: Serial or TCP/IP
- **Serial Port**: Path to the serial port (e.g., `/dev/ttyUSB0`)
- **Baud Rate**: Serial connection baud rate (default: 9600)
- **TCP Host**: IP address of the Nayax terminal for TCP connections
- **TCP Port**: Port number for TCP connections (default: 5000)
- **Merchant ID**: Merchant identifier provided by Nayax
- **Terminal ID**: Terminal identifier provided by Nayax

## Integration Flow

### Payment Process

1. When a vehicle exits, the system calculates the parking fee based on duration and configured rates
2. If a fee is due, the system initiates a payment request to the Nayax terminal
3. The terminal prompts the customer for payment (card, contactless, etc.)
4. The system monitors the transaction status until completion or cancellation
5. Upon successful payment, the barrier opens automatically
6. All transaction details are recorded in the database

### Transaction States

- **Pending**: Payment request has been sent to the terminal
- **Processing**: Terminal is waiting for customer action
- **Completed**: Payment has been successfully processed
- **Failed**: Payment was declined or failed
- **Cancelled**: Transaction was cancelled by the system or customer

## API Endpoints

The following API endpoints are available for interacting with the Nayax integration:

- `POST /parking/api/payment/request`: Request a new payment
- `GET /parking/api/payment/status`: Check the status of the current transaction
- `POST /parking/api/payment/cancel`: Cancel the current transaction
- `POST /parking/api/manual-payment`: Record a manual payment (cash, invoice, etc.)

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check that the terminal is powered on and connected
   - Verify serial port or IP address settings
   - Ensure the terminal is properly configured for external control

2. **Transaction Timeouts**
   - Check network connectivity for TCP connections
   - Verify that the terminal is not in an error state
   - Restart the terminal if it becomes unresponsive

3. **Payment Failures**
   - Check the transaction logs for specific error codes
   - Verify that the merchant account is active
   - Ensure the customer's payment method is valid

### Logs

Detailed logs of all Nayax transactions are available in the system logs. Each transaction includes:

- Transaction ID
- Amount
- Payment method
- Response codes
- Timestamps

## Testing

A test mode is available for verifying the integration without processing actual payments. To enable test mode:

1. Go to Parking → Settings
2. Enable "Test Mode" under Nayax Integration
3. Test transactions will be simulated without contacting the payment terminal

## Support

For issues with the Nayax integration, please contact:

- Technical support: support@visigate.com
- Nayax support: support@nayax.com
