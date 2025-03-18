# AMSLPR Reports and Notifications User Guide

This guide provides instructions on how to use the reporting and notification features of the AMSLPR system.

## Reports

The AMSLPR system can generate comprehensive PDF reports that provide insights into your parking system's usage patterns and statistics. These reports are useful for analyzing trends, planning capacity, and making data-driven decisions about your parking facility.

### Accessing Reports

1. Log in to the AMSLPR web interface
2. Click on the "Reports" link in the main navigation menu
3. The reports page displays options for generating different types of reports

### Types of Reports

#### Daily Reports

Daily reports provide a detailed view of parking activity for a specific day, including:

- Traffic patterns throughout the day
- Vehicle entry and exit counts
- Authorized vs. unauthorized vehicle statistics
- Parking duration statistics

To generate a daily report:

1. In the "Daily Report" card, select the desired date
2. Click the "Generate Report" button
3. The system will process the data and create a PDF report
4. Once complete, the report will appear in the "Previous Reports" section

#### Weekly Reports

Weekly reports aggregate data over a 7-day period, showing:

- Daily traffic trends over the week
- Peak usage days and times
- Weekly vehicle statistics
- Average parking durations by day

To generate a weekly report:

1. In the "Weekly Report" card, select the end date for the 7-day period
2. Click the "Generate Report" button
3. The system will create a PDF report covering the 7 days ending on the selected date

#### Monthly Reports

Monthly reports provide a comprehensive overview of an entire month, including:

- Monthly traffic patterns
- Day-of-week analysis
- Detailed vehicle statistics
- Long-term parking trends

To generate a monthly report:

1. In the "Monthly Report" card, select the year and month
2. Click the "Generate Report" button
3. The system will create a PDF report for the entire month

### Viewing and Downloading Reports

All generated reports are listed in the "Previous Reports" section of the reports page. To view or download a report:

1. Find the desired report in the list
2. Click on the report name to download the PDF file
3. Open the downloaded file with any PDF viewer

## Notifications

The AMSLPR system can send notifications when unauthorized vehicles attempt to access your parking facility. This feature helps you respond quickly to potential security issues.

### Notification Channels

The system supports three notification channels:

1. **Email**: Sends detailed notifications to specified email addresses
2. **SMS**: Sends text message alerts to specified phone numbers
3. **Webhook**: Sends JSON data to external systems for integration

### Configuring Notifications

1. Log in to the AMSLPR web interface
2. Click on your username in the top-right corner
3. Select "Notification Settings" from the dropdown menu
4. Configure each notification channel as needed

#### Email Notifications

To configure email notifications:

1. Enable the "Email Notifications" toggle
2. Enter the sender email address
3. Enter the recipient email address
4. Configure the SMTP server settings:
   - SMTP server address
   - SMTP port (typically 587 for TLS)
   - SMTP username and password
   - Enable TLS if required
5. Click the "Test Email" button to verify your configuration
6. Click "Save Settings" to apply changes

#### SMS Notifications

The system supports two SMS providers:

**Twilio**:

1. Enable the "SMS Notifications" toggle
2. Select "Twilio" as the SMS provider
3. Enter your Twilio Account SID and Auth Token
4. Enter the Twilio phone number to send from
5. Enter the recipient phone number
6. Click the "Test SMS" button to verify your configuration
7. Click "Save Settings" to apply changes

**HTTP API**:

1. Enable the "SMS Notifications" toggle
2. Select "HTTP API" as the SMS provider
3. Enter the API URL
4. Configure the parameter names for phone number and message
5. Add any required headers in JSON format
6. Select whether to send as JSON or form data
7. Click the "Test SMS" button to verify your configuration
8. Click "Save Settings" to apply changes

#### Webhook Notifications

To configure webhook notifications:

1. Enable the "Webhook Notifications" toggle
2. Enter the webhook URL
3. Add any required headers in JSON format
4. Enter a location name to identify this installation
5. Optionally, enter a public image base URL if your images are accessible externally
6. Click the "Test Webhook" button to verify your configuration
7. Click "Save Settings" to apply changes

### Notification Content

Notifications include the following information:

- License plate number of the unauthorized vehicle
- Date and time of the access attempt
- Location name (as configured in settings)
- Image of the vehicle (if available and configured)

### Testing Notifications

You can test each notification channel without triggering an actual unauthorized access event:

1. Go to the Notification Settings page
2. Click the "Test" button for the desired notification channel
3. Enter a test license plate number or use the default
4. Click "Send Test"
5. Check for the test notification through the selected channel

## Troubleshooting

### Reports

- If a report fails to generate, check the system logs for error details
- Ensure that there is sufficient data for the selected time period
- Verify that the reports directory is writable by the application

### Notifications

- For email issues, verify your SMTP settings and credentials
- For SMS issues, check your provider credentials and account balance
- For webhook issues, ensure the receiving endpoint is accessible and properly configured
- Use the test functionality to diagnose specific channel problems
- Check system logs for detailed error messages
