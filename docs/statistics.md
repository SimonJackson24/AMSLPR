# AMSLPR Statistics Module

## Overview

The Statistics Module is a component of the AMSLPR system that provides insights into vehicle access patterns, parking durations, and system usage. This module helps facility managers and administrators make data-driven decisions about parking management and resource allocation.

## Features

### Daily Traffic Analysis

The Statistics Module tracks and visualizes daily traffic patterns, including:

- Number of vehicle entries per day
- Number of vehicle exits per day
- Total vehicle movements per day
- Weekly trends and patterns

### Hourly Distribution

Understand peak hours and traffic distribution throughout the day:

- Hourly breakdown of vehicle entries and exits
- Identification of peak traffic hours
- Distribution of traffic across a 24-hour period

### Vehicle Statistics

Comprehensive vehicle usage statistics:

- Total number of unique vehicles in the system
- Breakdown of authorized vs. unauthorized vehicles
- Most frequent vehicles (top visitors)
- Average number of accesses per vehicle
- Percentage of authorized vs. unauthorized access events

### Parking Duration Analysis

Insights into how long vehicles typically stay:

- Average parking duration
- Maximum and minimum parking durations
- Distribution of parking durations across different time ranges
- Identification of long-term parkers

## Accessing Statistics

### Web Interface

The statistics are available through the AMSLPR web interface at:

```
http://<raspberry-pi-ip>:5000/statistics
```

The web interface provides an intuitive dashboard with charts and visualizations for all statistics.

### API Access

Statistics data can also be accessed programmatically through the API:

```
GET http://<raspberry-pi-ip>:5000/api/statistics
```

See the [API Documentation](api.md) for more details on the response format and integration examples.

## Implementation Details

### Components

- **StatisticsManager**: Core class that calculates and provides all statistics
- **Database Integration**: Leverages the DatabaseManager to retrieve access logs and vehicle data
- **Web Interface**: Visualizes statistics using Chart.js for an intuitive user experience

### Data Sources

The Statistics Module uses the following data sources:

- Vehicle database (authorized and unauthorized vehicles)
- Access logs (entry and exit events)
- Calculated parking durations (based on entry-exit pairs)

## Configuration

The Statistics Module can be configured through the main AMSLPR configuration file:

```yaml
statistics:
  # Number of days to include in daily traffic analysis
  daily_traffic_days: 7
  
  # Number of days to include in hourly distribution calculation
  hourly_distribution_days: 30
  
  # Number of vehicles to include in "most frequent vehicles" list
  top_vehicles_count: 5
```

## Future Enhancements

Planned enhancements for the Statistics Module include:

- Export functionality (CSV, PDF reports)
- Custom date range selection
- Comparative analysis (this week vs. last week)
- Predictive analytics for traffic patterns
- Automated alerts for unusual patterns

## Troubleshooting

### Common Issues

- **Missing or incomplete statistics**: Ensure that the database contains sufficient access log data
- **Inaccurate parking durations**: Check that vehicles have properly matched entry and exit events
- **Performance issues**: For systems with very large numbers of access logs, consider implementing database indexing or data archiving

### Logging

The Statistics Module logs information and errors to the main AMSLPR log file. Check the logs for any issues related to statistics calculation or database queries.
