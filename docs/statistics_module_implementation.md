# Statistics Module Implementation

## Overview

The Statistics Module is a key component of the AMSLPR system, providing valuable insights into parking facility operations. This document outlines the implementation details, features, and usage of the statistics module.

## Implementation Details

### Core Components

1. **StatisticsManager Class**
   - Located in `/src/utils/statistics.py`
   - Responsible for generating all statistics from the database
   - Uses pandas for data manipulation and analysis

2. **Web Interface Integration**
   - Statistics page at `/statistics` route
   - API endpoint at `/api/statistics` for programmatic access
   - Uses Chart.js for data visualization

3. **Testing**
   - Unit tests in `/tests/test_statistics.py`
   - Tests cover daily traffic, hourly distribution, vehicle statistics, and parking duration statistics

### Key Features

1. **Daily Traffic Statistics**
   - Tracks entry and exit events over time
   - Provides data for the last 7 days by default
   - Ensures data is available for all days in the range, even if no logs exist

2. **Hourly Distribution**
   - Shows traffic patterns throughout the day
   - Helps identify peak hours

3. **Vehicle Statistics**
   - Total vehicle count
   - Authorized vs. unauthorized breakdown
   - Most frequent vehicles
   - Average accesses per vehicle

4. **Parking Duration Statistics**
   - Average, maximum, and minimum parking durations
   - Distribution of parking durations by time ranges

## Implementation Challenges and Solutions

### Challenge 1: Handling Empty Data

**Problem**: The system needed to return structured data even when no logs were available for a given time period.

**Solution**: Implemented the `_empty_daily_stats` method to generate placeholder data with the correct structure. This ensures that the web interface and API endpoints always receive properly formatted data, even when the database is empty or contains no relevant logs.

### Challenge 2: Accurate Duration Calculations

**Problem**: Calculating parking durations required matching entry and exit events for the same vehicle, which could be complex when multiple entries or exits occurred.

**Solution**: Used pandas DataFrame operations to efficiently match entry and exit events, calculating the time difference between them. The implementation handles edge cases such as missing entry or exit events.

### Challenge 3: Consistent Data Types

**Problem**: Tests expected floating-point values for duration statistics, but the implementation was returning integers.

**Solution**: Updated the code to ensure that all duration-related statistics (average, maximum, minimum) are returned as floating-point values for consistency and precision.

## Usage Examples

### Accessing Statistics via Web Interface

The statistics page provides a visual dashboard with charts and summary cards:

1. Navigate to `http://<server-ip>:5000/statistics`
2. View daily traffic chart, hourly distribution, vehicle statistics, and parking duration information

### Accessing Statistics via API

The statistics API endpoint provides JSON data for integration with other systems:

```
GET http://<server-ip>:5000/api/statistics
```

Response format:

```json
{
  "daily_traffic": {
    "dates": ["2025-03-08", "2025-03-09", ...],
    "entry": [37, 37, ...],
    "exit": [35, 33, ...],
    "total": [72, 70, ...]
  },
  "hourly_distribution": {
    "hours": [0, 1, 2, ...],
    "entry": [5, 7, 7, ...],
    "exit": [22, 15, 11, ...],
    "total": [27, 22, 18, ...]
  },
  "vehicle_stats": {
    "total_vehicles": 10,
    "authorized_vehicles": 7,
    "unauthorized_vehicles": 3,
    "most_frequent_vehicles": {
      "DEF456": 17,
      "YZA567": 15,
      "VWX234": 11,
      "MNO345": 10,
      "XYZ789": 10
    },
    "avg_accesses_per_vehicle": 10.0,
    "authorized_access_percentage": 77.0
  },
  "parking_stats": {
    "avg_duration_minutes": 278.08,
    "max_duration_minutes": 1835.12,
    "min_duration_minutes": 0.93,
    "duration_distribution": {
      "<15m": 3,
      "15-30m": 14,
      "30-60m": 20,
      "1-2h": 37,
      "2-4h": 77,
      "4-8h": 94,
      "8-24h": 21,
      ">24h": 4
    }
  }
}
```

## Testing

The statistics module includes comprehensive tests to ensure accuracy and reliability. Run the tests with:

```bash
python -m tests.test_statistics
```

## Sample Data Generation

For testing and demonstration purposes, a sample data generation script is provided:

```bash
python scripts/generate_sample_data.py --days 14 --min-entries 15 --max-entries 40
```

This script creates realistic vehicle access patterns with varying parking durations.

## Future Enhancements

1. **Advanced Analytics**
   - Predictive analytics for parking occupancy
   - Anomaly detection for unusual access patterns

2. **Additional Visualizations**
   - Heatmaps for busy periods
   - Vehicle type distribution charts

3. **Reporting Features**
   - Scheduled email reports
   - PDF export functionality

4. **Integration with External Systems**
   - Export to business intelligence tools
   - Integration with facility management systems
