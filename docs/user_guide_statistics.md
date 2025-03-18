# AMSLPR Statistics Module User Guide

## Introduction

The Statistics Module provides valuable insights into your parking facility's operations. This guide will help you understand how to access and interpret the statistics provided by the AMSLPR system.

## Accessing Statistics

### Web Interface

1. Open your web browser and navigate to the AMSLPR web interface:
   ```
   http://<raspberry-pi-ip>:5000
   ```

2. Log in with your administrator credentials.

3. Click on the "Statistics" link in the navigation menu.

### API Access

For programmatic access, you can use the statistics API endpoint:

```
GET http://<raspberry-pi-ip>:5000/api/statistics
```

See the [API Documentation](api.md) for more details on the response format and integration examples.

## Understanding the Statistics Dashboard

### Overview Cards

At the top of the statistics page, you'll find overview cards showing key metrics:

- **Total Vehicles**: The number of unique vehicles in the system.
- **Authorized Vehicles**: The number of vehicles marked as authorized.
- **Average Parking Duration**: The average time vehicles spend parked in your facility.

### Daily Traffic Chart

The daily traffic chart shows vehicle movements over the past week:

- **Blue Line**: Entry events
- **Red Line**: Exit events
- **Green Line**: Total events (entries + exits)

This chart helps you identify patterns in daily usage and spot unusual activity.

### Hourly Distribution Chart

The hourly distribution chart shows when your facility is busiest throughout the day:

- **X-axis**: Hours of the day (0-23)
- **Y-axis**: Number of vehicle movements
- **Blue Bars**: Entry events
- **Red Bars**: Exit events

Use this chart to identify peak hours and optimize staffing or resources accordingly.

### Vehicle Statistics

This section provides detailed information about vehicles using your facility:

- **Total Vehicles**: Number of unique vehicles recorded in the system.
- **Authorized vs. Unauthorized**: Breakdown of vehicles by authorization status.
- **Most Frequent Vehicles**: Top 5 vehicles with the most access events.
- **Average Accesses per Vehicle**: How many times a typical vehicle enters/exits.
- **Authorized Access Percentage**: Percentage of access events from authorized vehicles.

### Parking Duration Statistics

This section shows how long vehicles typically stay in your facility:

- **Average Duration**: The mean parking duration across all vehicles.
- **Maximum Duration**: The longest recorded parking session.
- **Minimum Duration**: The shortest recorded parking session.
- **Duration Distribution**: Breakdown of parking durations by time ranges:
  - Less than 15 minutes
  - 15-30 minutes
  - 30-60 minutes
  - 1-2 hours
  - 2-4 hours
  - 4-8 hours
  - 8-24 hours
  - More than 24 hours

## Practical Applications

### Capacity Planning

Use the daily and hourly statistics to identify when your facility reaches peak capacity. This can help you plan for expansion or implement time-based pricing strategies.

### Security Monitoring

Unusual patterns in the statistics may indicate security issues:

- Sudden increase in unauthorized vehicles
- Vehicles with extremely long parking durations
- Unusual activity during off-hours

### Operational Optimization

Optimize staffing and resources based on usage patterns:

- Schedule maintenance during low-usage periods
- Adjust staffing levels to match peak hours
- Implement special procedures during high-traffic periods

## Troubleshooting

### No Data Showing

If the statistics page shows no data:

1. Ensure the system has been operational for at least a few days to collect data.
2. Check that the database is properly recording access events.
3. Verify that the date range settings are appropriate.

### Inaccurate Parking Durations

If parking durations seem incorrect:

1. Ensure vehicles are properly logging both entry and exit events.
2. Check for any system clock issues that might affect time calculations.
3. Verify that the license plate recognition is accurately identifying the same vehicle at entry and exit.

## Getting Help

If you encounter any issues with the statistics module, please refer to the main [AMSLPR Documentation](README.md) or contact technical support.
