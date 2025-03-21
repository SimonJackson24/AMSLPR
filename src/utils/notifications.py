
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Notification module for sending alerts about unauthorized access attempts.

This module provides functionality to send notifications via various channels
when unauthorized vehicles attempt to access the facility.
"""

import os
import datetime
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import requests

class NotificationManager:
    """
    Class for managing and sending notifications about unauthorized access attempts.
    """
    
    def __init__(self, config):
        """
        Initialize the NotificationManager with configuration.
        
        Args:
            config: Dictionary containing notification configuration
        """
        self.config = config
        self.logger = logging.getLogger('amslpr.notifications')
    
    def send_email_notification(self, plate_number, access_time, image_path=None):
        """
        Send an email notification about an unauthorized access attempt.
        
        Args:
            plate_number: The license plate number of the unauthorized vehicle
            access_time: The time of the access attempt
            image_path: Optional path to the image of the license plate
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if not self.config.get('email_enabled', False):
            self.logger.info("Email notifications are disabled")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.get('email_from')
            msg['To'] = self.config.get('email_to')
            msg['Subject'] = f"AMSLPR Alert: Unauthorized Access Attempt - {plate_number}"
            
            # Format the time
            if isinstance(access_time, str):
                formatted_time = access_time
            else:
                formatted_time = access_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Create the message body
            body = f"""Unauthorized Access Attempt Detected

License Plate: {plate_number}
Time: {formatted_time}
Location: {self.config.get('location_name', 'Main Entrance')}

This vehicle is not authorized to access the facility.

Please review the attached image (if available) and take appropriate action.

--
AMSLPR System
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach image if available
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as img_file:
                    img = MIMEImage(img_file.read())
                    img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                    msg.attach(img)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.config.get('smtp_server'), self.config.get('smtp_port', 587)) as server:
                if self.config.get('smtp_use_tls', True):
                    server.starttls()
                
                if self.config.get('smtp_username') and self.config.get('smtp_password'):
                    server.login(self.config.get('smtp_username'), self.config.get('smtp_password'))
                
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for unauthorized access by {plate_number}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def send_sms_notification(self, plate_number, access_time):
        """
        Send an SMS notification about an unauthorized access attempt.
        
        Args:
            plate_number: The license plate number of the unauthorized vehicle
            access_time: The time of the access attempt
            
        Returns:
            bool: True if the SMS was sent successfully, False otherwise
        """
        if not self.config.get('sms_enabled', False):
            self.logger.info("SMS notifications are disabled")
            return False
        
        try:
            # Format the time
            if isinstance(access_time, str):
                formatted_time = access_time
            else:
                formatted_time = access_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Create the message
            message = f"AMSLPR Alert: Unauthorized vehicle {plate_number} detected at {formatted_time}"
            
            # Use Twilio if configured
            if self.config.get('sms_provider') == 'twilio':
                from twilio.rest import Client
                
                client = Client(self.config.get('twilio_account_sid'), self.config.get('twilio_auth_token'))
                client.messages.create(
                    body=message,
                    from_=self.config.get('twilio_from_number'),
                    to=self.config.get('sms_to_number')
                )
                
                self.logger.info(f"Twilio SMS notification sent for unauthorized access by {plate_number}")
                return True
            
            # Generic HTTP API for SMS
            elif self.config.get('sms_provider') == 'http_api':
                # Prepare the payload according to the API requirements
                payload = {
                    self.config.get('sms_api_number_param', 'to'): self.config.get('sms_to_number'),
                    self.config.get('sms_api_message_param', 'message'): message
                }
                
                # Add any additional parameters from config
                if self.config.get('sms_api_additional_params'):
                    payload.update(self.config.get('sms_api_additional_params'))
                
                # Send the request
                headers = self.config.get('sms_api_headers', {})
                response = requests.post(
                    self.config.get('sms_api_url'),
                    json=payload if self.config.get('sms_api_json', True) else None,
                    data=payload if not self.config.get('sms_api_json', True) else None,
                    headers=headers
                )
                
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                self.logger.info(f"HTTP API SMS notification sent for unauthorized access by {plate_number}")
                return True
            
            else:
                self.logger.error("Unsupported SMS provider")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to send SMS notification: {str(e)}")
            return False
    
    def send_webhook_notification(self, plate_number, access_time, image_path=None):
        """
        Send a webhook notification about an unauthorized access attempt.
        
        Args:
            plate_number: The license plate number of the unauthorized vehicle
            access_time: The time of the access attempt
            image_path: Optional path to the image of the license plate
            
        Returns:
            bool: True if the webhook was sent successfully, False otherwise
        """
        if not self.config.get('webhook_enabled', False):
            self.logger.info("Webhook notifications are disabled")
            return False
        
        try:
            # Format the time
            if isinstance(access_time, str):
                formatted_time = access_time
            else:
                formatted_time = access_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare the payload
            payload = {
                'event_type': 'unauthorized_access',
                'plate_number': plate_number,
                'access_time': formatted_time,
                'location': self.config.get('location_name', 'Main Entrance'),
                'system_time': datetime.datetime.now().isoformat()
            }
            
            # Add image URL if available
            if image_path and os.path.exists(image_path):
                if self.config.get('public_image_base_url'):
                    # Calculate the relative path and convert to URL
                    rel_path = os.path.relpath(image_path, self.config.get('image_base_path', 'data/images'))
                    image_url = f"{self.config.get('public_image_base_url')}/{rel_path}"
                    payload['image_url'] = image_url
            
            # Send the webhook
            headers = self.config.get('webhook_headers', {'Content-Type': 'application/json'})
            response = requests.post(
                self.config.get('webhook_url'),
                json=payload,
                headers=headers
            )
            
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            self.logger.info(f"Webhook notification sent for unauthorized access by {plate_number}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {str(e)}")
            return False
    
    def notify_unauthorized_access(self, plate_number, access_time, image_path=None):
        """
        Send notifications about an unauthorized access attempt through all enabled channels.
        
        Args:
            plate_number: The license plate number of the unauthorized vehicle
            access_time: The time of the access attempt
            image_path: Optional path to the image of the license plate
            
        Returns:
            dict: Dictionary with results for each notification channel
        """
        results = {}
        
        # Send email notification
        if self.config.get('email_enabled', False):
            results['email'] = self.send_email_notification(plate_number, access_time, image_path)
        
        # Send SMS notification
        if self.config.get('sms_enabled', False):
            results['sms'] = self.send_sms_notification(plate_number, access_time)
        
        # Send webhook notification
        if self.config.get('webhook_enabled', False):
            results['webhook'] = self.send_webhook_notification(plate_number, access_time, image_path)
        
        return results
