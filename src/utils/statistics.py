import logging
import datetime
import sqlite3
import pandas as pd
import numpy as np
from collections import Counter

# Configure logging
logger = logging.getLogger('AMSLPR.statistics')

class StatisticsManager:
    """
    Manages statistics and analytics for the AMSLPR system.
    """
    
    def __init__(self, db_manager):
        """
        Initialize the statistics manager.
        
        Args:
            db_manager (DatabaseManager): Database manager instance
        """
        self.db_manager = db_manager
        logger.info("Statistics manager initialized")
    
    def get_daily_traffic(self, days=7):
        """
        Get daily traffic statistics for the specified number of days.
        
        Args:
            days (int): Number of days to include in the statistics
            
        Returns:
            dict: Daily traffic statistics
        """
        try:
            # Calculate the start date
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=days)
            
            # Get access logs for the period
            logs = self.db_manager.get_access_logs_by_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            # If no logs, return empty stats
            if not logs:
                return self._empty_daily_stats(days)
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(logs)
            
            # If DataFrame is empty, return empty stats
            if df.empty:
                return self._empty_daily_stats(days)
            
            # Convert access_time to datetime
            df['access_time'] = pd.to_datetime(df['access_time'])
            
            # Extract date from access_time
            df['date'] = df['access_time'].dt.date
            
            # Group by date and direction
            daily_counts = df.groupby(['date', 'direction']).size().unstack(fill_value=0)
            
            # Ensure both entry and exit columns exist
            if 'entry' not in daily_counts.columns:
                daily_counts['entry'] = 0
            if 'exit' not in daily_counts.columns:
                daily_counts['exit'] = 0
            
            # Calculate total
            daily_counts['total'] = daily_counts['entry'] + daily_counts['exit']
            
            # Ensure we have data for all days in the range
            date_range = [start_date.date() + datetime.timedelta(days=i) for i in range(days)]
            daily_counts = daily_counts.reindex(date_range, fill_value=0)
            
            # Convert to dictionary format
            result = {
                'dates': [d.strftime('%Y-%m-%d') for d in daily_counts.index],
                'entry': daily_counts['entry'].tolist(),
                'exit': daily_counts['exit'].tolist(),
                'total': daily_counts['total'].tolist()
            }
            
            return result
        except Exception as e:
            logger.error(f"Error getting daily traffic: {e}")
            return self._empty_daily_stats(days)
    
    def _empty_daily_stats(self, days):
        """
        Create empty daily statistics.
        
        Args:
            days (int): Number of days
            
        Returns:
            dict: Empty daily statistics
        """
        # Generate date strings for the last 'days' days
        end_date = datetime.datetime.now()
        dates = [(end_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range(days-1, -1, -1)]
        
        return {
            'dates': dates,
            'entry': [0] * days,
            'exit': [0] * days,
            'total': [0] * days
        }
    
    def get_hourly_distribution(self, days=30):
        """
        Get hourly distribution of traffic.
        
        Args:
            days (int): Number of days to include in the statistics
            
        Returns:
            dict: Hourly distribution statistics
        """
        try:
            # Calculate the start date
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=days)
            
            # Get access logs for the period
            logs = self.db_manager.get_access_logs_by_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(logs)
            
            # If no logs, return empty stats
            if df.empty:
                return self._empty_hourly_stats()
            
            # Convert access_time to datetime
            df['access_time'] = pd.to_datetime(df['access_time'])
            
            # Extract hour from access_time
            df['hour'] = df['access_time'].dt.hour
            
            # Group by hour and direction
            hourly_counts = df.groupby(['hour', 'direction']).size().unstack(fill_value=0)
            
            # Ensure both entry and exit columns exist
            if 'entry' not in hourly_counts.columns:
                hourly_counts['entry'] = 0
            if 'exit' not in hourly_counts.columns:
                hourly_counts['exit'] = 0
            
            # Calculate total
            hourly_counts['total'] = hourly_counts['entry'] + hourly_counts['exit']
            
            # Ensure all hours are represented
            all_hours = pd.DataFrame(index=range(24))
            hourly_counts = all_hours.join(hourly_counts).fillna(0)
            
            # Convert to dictionary format
            result = {
                'hours': list(range(24)),
                'entry': hourly_counts['entry'].astype(int).tolist(),
                'exit': hourly_counts['exit'].astype(int).tolist(),
                'total': hourly_counts['total'].astype(int).tolist()
            }
            
            return result
        except Exception as e:
            logger.error(f"Error getting hourly distribution: {e}")
            return self._empty_hourly_stats()
    
    def _empty_hourly_stats(self):
        """
        Create empty hourly statistics.
        
        Returns:
            dict: Empty hourly statistics
        """
        return {
            'hours': list(range(24)),
            'entry': [0] * 24,
            'exit': [0] * 24,
            'total': [0] * 24
        }
    
    def get_vehicle_statistics(self):
        """
        Get vehicle statistics.
        
        Returns:
            dict: Vehicle statistics
        """
        try:
            # Get all vehicles
            vehicles = self.db_manager.get_vehicles()
            
            # Get all access logs
            logs = self.db_manager.get_access_logs()
            
            # Convert to DataFrames
            vehicles_df = pd.DataFrame(vehicles)
            logs_df = pd.DataFrame(logs)
            
            # Calculate statistics
            total_vehicles = len(vehicles_df)
            authorized_vehicles = len(vehicles_df[vehicles_df['authorized'] == True])
            unauthorized_vehicles = total_vehicles - authorized_vehicles
            
            # Calculate access frequency if logs exist
            if not logs_df.empty:
                # Count accesses by plate number
                access_counts = logs_df['plate_number'].value_counts()
                
                # Most frequent vehicles
                most_frequent = access_counts.head(5).to_dict()
                
                # Calculate average accesses per vehicle
                avg_accesses = access_counts.mean()
                
                # Calculate percentage of authorized accesses
                if 'authorized' in logs_df.columns:
                    authorized_accesses = logs_df[logs_df['authorized'] == True].shape[0]
                    total_accesses = logs_df.shape[0]
                    auth_percentage = (authorized_accesses / total_accesses * 100) if total_accesses > 0 else 0
                else:
                    auth_percentage = 0
            else:
                most_frequent = {}
                avg_accesses = 0
                auth_percentage = 0
            
            return {
                'total_vehicles': total_vehicles,
                'authorized_vehicles': authorized_vehicles,
                'unauthorized_vehicles': unauthorized_vehicles,
                'most_frequent_vehicles': most_frequent,
                'avg_accesses_per_vehicle': round(avg_accesses, 2),
                'authorized_access_percentage': round(auth_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting vehicle statistics: {e}")
            return {
                'total_vehicles': 0,
                'authorized_vehicles': 0,
                'unauthorized_vehicles': 0,
                'most_frequent_vehicles': {},
                'avg_accesses_per_vehicle': 0,
                'authorized_access_percentage': 0
            }
    
    def get_parking_duration_statistics(self):
        """
        Get parking duration statistics.
        
        Returns:
            dict: Parking duration statistics
        """
        try:
            # Get all parking durations
            durations = self.db_manager.get_all_parking_durations()
            
            # If no durations, return empty stats
            if not durations:
                return {
                    'avg_duration_minutes': 0.0,
                    'max_duration_minutes': 0.0,
                    'min_duration_minutes': 0.0,
                    'duration_distribution': {}
                }
            
            # Convert durations to minutes
            duration_minutes = [d.total_seconds() / 60 for d in durations if d]
            
            # If still no valid durations, return empty stats
            if not duration_minutes:
                return {
                    'avg_duration_minutes': 0.0,
                    'max_duration_minutes': 0.0,
                    'min_duration_minutes': 0.0,
                    'duration_distribution': {}
                }
            
            # Calculate statistics
            avg_duration = float(np.mean(duration_minutes))
            max_duration = float(np.max(duration_minutes))
            min_duration = float(np.min(duration_minutes))
            
            # Create duration distribution
            bins = [0, 15, 30, 60, 120, 240, 480, 1440, float('inf')]
            bin_labels = ['<15m', '15-30m', '30-60m', '1-2h', '2-4h', '4-8h', '8-24h', '>24h']
            
            # Count durations in each bin
            counts = [0] * len(bin_labels)
            for duration in duration_minutes:
                for i, upper_bound in enumerate(bins[1:]):
                    if duration < upper_bound:
                        counts[i] += 1
                        break
            
            # Create distribution dictionary
            distribution = dict(zip(bin_labels, counts))
            
            return {
                'avg_duration_minutes': round(avg_duration, 2),
                'max_duration_minutes': round(max_duration, 2),
                'min_duration_minutes': round(min_duration, 2),
                'duration_distribution': distribution
            }
        except Exception as e:
            logger.error(f"Error getting parking duration statistics: {e}")
            return {
                'avg_duration_minutes': 0.0,
                'max_duration_minutes': 0.0,
                'min_duration_minutes': 0.0,
                'duration_distribution': {}
            }
