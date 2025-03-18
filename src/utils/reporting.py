#!/usr/bin/env python3
"""
Reporting module for generating PDF reports from statistics data.

This module provides functionality to generate PDF reports of various statistics
collected by the AMSLPR system, including daily traffic, hourly distribution,
vehicle statistics, and parking duration statistics.
"""

import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
import pandas as pd

class ReportGenerator:
    """
    Class for generating PDF reports from statistics data.
    """
    
    def __init__(self, statistics_manager, output_dir='/home/simon/Projects/AMSLPR/reports'):
        """
        Initialize the ReportGenerator with a StatisticsManager instance.
        
        Args:
            statistics_manager: An instance of StatisticsManager
            output_dir: Directory where reports will be saved
        """
        self.stats_manager = statistics_manager
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_daily_report(self, date=None):
        """
        Generate a daily report for a specific date.
        
        Args:
            date: Date for the report (default: today)
            
        Returns:
            Path to the generated PDF report
        """
        if date is None:
            date = datetime.date.today()
        elif isinstance(date, str):
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        
        # Generate filename
        filename = os.path.join(self.output_dir, f"daily_report_{date.strftime('%Y-%m-%d')}.pdf")
        
        # Get statistics data
        daily_traffic = self.stats_manager.get_daily_traffic(days=1, end_date=date)
        hourly_distribution = self.stats_manager.get_hourly_distribution(days=1, end_date=date)
        vehicle_stats = self.stats_manager.get_vehicle_statistics()
        parking_stats = self.stats_manager.get_parking_duration_statistics()
        
        # Create PDF
        with PdfPages(filename) as pdf:
            # Title page
            fig = Figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis('off')
            ax.text(0.5, 0.8, 'AMSLPR Daily Report', fontsize=24, ha='center')
            ax.text(0.5, 0.7, f"Date: {date.strftime('%Y-%m-%d')}", fontsize=18, ha='center')
            ax.text(0.5, 0.6, 'Automate Systems License Plate Recognition', fontsize=14, ha='center')
            ax.text(0.5, 0.5, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=12, ha='center')
            pdf.savefig(fig)
            plt.close(fig)
            
            # Daily traffic page
            if daily_traffic and daily_traffic['dates']:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                ax.bar(daily_traffic['dates'], daily_traffic['entry'], label='Entry', alpha=0.7, color='blue')
                ax.bar(daily_traffic['dates'], daily_traffic['exit'], label='Exit', alpha=0.7, color='red', bottom=daily_traffic['entry'])
                ax.set_title(f"Traffic for {date.strftime('%Y-%m-%d')}")
                ax.set_ylabel('Number of Vehicles')
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            
            # Hourly distribution page
            if hourly_distribution and hourly_distribution['hours']:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                x = np.arange(len(hourly_distribution['hours']))
                width = 0.35
                ax.bar(x - width/2, hourly_distribution['entry'], width, label='Entry', color='blue', alpha=0.7)
                ax.bar(x + width/2, hourly_distribution['exit'], width, label='Exit', color='red', alpha=0.7)
                ax.set_title(f"Hourly Distribution for {date.strftime('%Y-%m-%d')}")
                ax.set_xlabel('Hour of Day')
                ax.set_ylabel('Number of Vehicles')
                ax.set_xticks(x)
                ax.set_xticklabels([f"{hour}:00" for hour in hourly_distribution['hours']])
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            
            # Vehicle statistics page
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 5))
            
            # Authorized vs Unauthorized pie chart
            labels = ['Authorized', 'Unauthorized']
            sizes = [vehicle_stats['authorized_vehicles'], vehicle_stats['unauthorized_vehicles']]
            colors = ['green', 'red']
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.axis('equal')
            ax1.set_title('Vehicle Authorization')
            
            # Most frequent vehicles bar chart
            if vehicle_stats['most_frequent_vehicles']:
                plates = list(vehicle_stats['most_frequent_vehicles'].keys())
                counts = list(vehicle_stats['most_frequent_vehicles'].values())
                y_pos = np.arange(len(plates))
                ax2.barh(y_pos, counts, align='center', color='blue', alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(plates)
                ax2.invert_yaxis()  # labels read top-to-bottom
                ax2.set_xlabel('Number of Accesses')
                ax2.set_title('Most Frequent Vehicles')
            
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            
            # Parking duration statistics page
            if parking_stats and parking_stats['duration_distribution']:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 5))
                
                # Duration statistics
                stats_text = (
                    f"Average Duration: {parking_stats['avg_duration_minutes'] / 60:.2f} hours\n"
                    f"Maximum Duration: {parking_stats['max_duration_minutes'] / 60:.2f} hours\n"
                    f"Minimum Duration: {parking_stats['min_duration_minutes']:.2f} minutes"
                )
                ax1.text(0.5, 0.5, stats_text, ha='center', va='center', fontsize=12)
                ax1.axis('off')
                ax1.set_title('Parking Duration Statistics')
                
                # Duration distribution bar chart
                categories = list(parking_stats['duration_distribution'].keys())
                values = list(parking_stats['duration_distribution'].values())
                y_pos = np.arange(len(categories))
                ax2.barh(y_pos, values, align='center', color='green', alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(categories)
                ax2.invert_yaxis()  # labels read top-to-bottom
                ax2.set_xlabel('Number of Vehicles')
                ax2.set_title('Parking Duration Distribution')
                
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
        
        return filename
    
    def generate_weekly_report(self, end_date=None):
        """
        Generate a weekly report ending on the specified date.
        
        Args:
            end_date: End date for the report (default: today)
            
        Returns:
            Path to the generated PDF report
        """
        if end_date is None:
            end_date = datetime.date.today()
        elif isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        start_date = end_date - datetime.timedelta(days=6)
        
        # Generate filename
        filename = os.path.join(
            self.output_dir, 
            f"weekly_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.pdf"
        )
        
        # Get statistics data
        daily_traffic = self.stats_manager.get_daily_traffic(days=7, end_date=end_date)
        hourly_distribution = self.stats_manager.get_hourly_distribution(days=7, end_date=end_date)
        vehicle_stats = self.stats_manager.get_vehicle_statistics()
        parking_stats = self.stats_manager.get_parking_duration_statistics()
        
        # Create PDF
        with PdfPages(filename) as pdf:
            # Title page
            fig = Figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis('off')
            ax.text(0.5, 0.8, 'AMSLPR Weekly Report', fontsize=24, ha='center')
            ax.text(0.5, 0.7, f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", 
                   fontsize=18, ha='center')
            ax.text(0.5, 0.6, 'Automate Systems License Plate Recognition', fontsize=14, ha='center')
            ax.text(0.5, 0.5, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                   fontsize=12, ha='center')
            pdf.savefig(fig)
            plt.close(fig)
            
            # Daily traffic page
            if daily_traffic and daily_traffic['dates']:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                x = np.arange(len(daily_traffic['dates']))
                width = 0.35
                ax.bar(x - width/2, daily_traffic['entry'], width, label='Entry', color='blue', alpha=0.7)
                ax.bar(x + width/2, daily_traffic['exit'], width, label='Exit', color='red', alpha=0.7)
                ax.set_title(f"Daily Traffic ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
                ax.set_xlabel('Date')
                ax.set_ylabel('Number of Vehicles')
                ax.set_xticks(x)
                ax.set_xticklabels([date.split('-')[2] + '/' + date.split('-')[1] for date in daily_traffic['dates']])
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
                
                # Daily totals line chart
                fig, ax = plt.subplots(figsize=(8.5, 5))
                ax.plot(daily_traffic['dates'], daily_traffic['total'], 'o-', label='Total Traffic', 
                        color='green', linewidth=2)
                ax.set_title(f"Daily Total Traffic ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
                ax.set_xlabel('Date')
                ax.set_ylabel('Number of Vehicles')
                ax.set_xticks(range(len(daily_traffic['dates'])))
                ax.set_xticklabels([date.split('-')[2] + '/' + date.split('-')[1] for date in daily_traffic['dates']])
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            
            # Hourly distribution page
            if hourly_distribution and hourly_distribution['hours']:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                x = np.arange(len(hourly_distribution['hours']))
                width = 0.35
                ax.bar(x - width/2, hourly_distribution['entry'], width, label='Entry', color='blue', alpha=0.7)
                ax.bar(x + width/2, hourly_distribution['exit'], width, label='Exit', color='red', alpha=0.7)
                ax.set_title(f"Weekly Hourly Distribution ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
                ax.set_xlabel('Hour of Day')
                ax.set_ylabel('Number of Vehicles')
                ax.set_xticks(x)
                ax.set_xticklabels([f"{hour}:00" for hour in hourly_distribution['hours']])
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            
            # Vehicle statistics page
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 5))
            
            # Authorized vs Unauthorized pie chart
            labels = ['Authorized', 'Unauthorized']
            sizes = [vehicle_stats['authorized_vehicles'], vehicle_stats['unauthorized_vehicles']]
            colors = ['green', 'red']
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.axis('equal')
            ax1.set_title('Vehicle Authorization')
            
            # Most frequent vehicles bar chart
            if vehicle_stats['most_frequent_vehicles']:
                plates = list(vehicle_stats['most_frequent_vehicles'].keys())
                counts = list(vehicle_stats['most_frequent_vehicles'].values())
                y_pos = np.arange(len(plates))
                ax2.barh(y_pos, counts, align='center', color='blue', alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(plates)
                ax2.invert_yaxis()  # labels read top-to-bottom
                ax2.set_xlabel('Number of Accesses')
                ax2.set_title('Most Frequent Vehicles')
            
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            
            # Parking duration statistics page
            if parking_stats and parking_stats['duration_distribution']:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 5))
                
                # Duration statistics
                stats_text = (
                    f"Average Duration: {parking_stats['avg_duration_minutes'] / 60:.2f} hours\n"
                    f"Maximum Duration: {parking_stats['max_duration_minutes'] / 60:.2f} hours\n"
                    f"Minimum Duration: {parking_stats['min_duration_minutes']:.2f} minutes"
                )
                ax1.text(0.5, 0.5, stats_text, ha='center', va='center', fontsize=12)
                ax1.axis('off')
                ax1.set_title('Parking Duration Statistics')
                
                # Duration distribution bar chart
                categories = list(parking_stats['duration_distribution'].keys())
                values = list(parking_stats['duration_distribution'].values())
                y_pos = np.arange(len(categories))
                ax2.barh(y_pos, values, align='center', color='green', alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(categories)
                ax2.invert_yaxis()  # labels read top-to-bottom
                ax2.set_xlabel('Number of Vehicles')
                ax2.set_title('Parking Duration Distribution')
                
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
        
        return filename
    
    def generate_monthly_report(self, year=None, month=None):
        """
        Generate a monthly report for the specified year and month.
        
        Args:
            year: Year for the report (default: current year)
            month: Month for the report (default: current month)
            
        Returns:
            Path to the generated PDF report
        """
        today = datetime.date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        
        # Calculate start and end dates
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
        days_in_month = (end_date - start_date).days + 1
        
        # Generate filename
        filename = os.path.join(self.output_dir, f"monthly_report_{year}_{month:02d}.pdf")
        
        # Get statistics data
        daily_traffic = self.stats_manager.get_daily_traffic(days=days_in_month, end_date=end_date)
        hourly_distribution = self.stats_manager.get_hourly_distribution(days=days_in_month, end_date=end_date)
        vehicle_stats = self.stats_manager.get_vehicle_statistics()
        parking_stats = self.stats_manager.get_parking_duration_statistics()
        
        # Create PDF
        with PdfPages(filename) as pdf:
            # Title page
            fig = Figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis('off')
            ax.text(0.5, 0.8, 'AMSLPR Monthly Report', fontsize=24, ha='center')
            ax.text(0.5, 0.7, f"Month: {start_date.strftime('%B %Y')}", fontsize=18, ha='center')
            ax.text(0.5, 0.6, 'Automate Systems License Plate Recognition', fontsize=14, ha='center')
            ax.text(0.5, 0.5, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                   fontsize=12, ha='center')
            pdf.savefig(fig)
            plt.close(fig)
            
            # Monthly summary page
            fig, ax = plt.subplots(figsize=(8.5, 5))
            ax.axis('off')
            
            # Calculate monthly totals
            total_entries = sum(daily_traffic['entry']) if daily_traffic and daily_traffic['entry'] else 0
            total_exits = sum(daily_traffic['exit']) if daily_traffic and daily_traffic['exit'] else 0
            total_traffic = total_entries + total_exits
            
            summary_text = (
                f"Monthly Summary for {start_date.strftime('%B %Y')}\n\n"
                f"Total Traffic: {total_traffic} vehicles\n"
                f"Total Entries: {total_entries} vehicles\n"
                f"Total Exits: {total_exits} vehicles\n\n"
                f"Daily Average: {total_traffic / days_in_month:.1f} vehicles/day\n"
                f"Authorized Vehicles: {vehicle_stats['authorized_vehicles']}\n"
                f"Unauthorized Vehicles: {vehicle_stats['unauthorized_vehicles']}\n"
                f"Authorization Rate: {vehicle_stats['authorized_access_percentage']:.1f}%\n\n"
                f"Average Parking Duration: {parking_stats['avg_duration_minutes'] / 60:.2f} hours\n"
                f"Maximum Parking Duration: {parking_stats['max_duration_minutes'] / 60:.2f} hours\n"
            )
            
            ax.text(0.5, 0.5, summary_text, ha='center', va='center', fontsize=14)
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            
            # Daily traffic page
            if daily_traffic and daily_traffic['dates']:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                x = range(len(daily_traffic['dates']))
                ax.plot(x, daily_traffic['entry'], 'o-', label='Entry', color='blue', alpha=0.7)
                ax.plot(x, daily_traffic['exit'], 'o-', label='Exit', color='red', alpha=0.7)
                ax.plot(x, daily_traffic['total'], 'o-', label='Total', color='green', alpha=0.7)
                ax.set_title(f"Daily Traffic for {start_date.strftime('%B %Y')}")
                ax.set_xlabel('Day of Month')
                ax.set_ylabel('Number of Vehicles')
                
                # Set x-ticks to show every 5 days
                tick_indices = [i for i in range(len(daily_traffic['dates'])) if (i + 1) % 5 == 0 or i == 0 or i == len(daily_traffic['dates']) - 1]
                ax.set_xticks([x[i] for i in tick_indices])
                ax.set_xticklabels([daily_traffic['dates'][i].split('-')[2] for i in tick_indices])
                
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            
            # Hourly distribution page
            if hourly_distribution and hourly_distribution['hours']:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                x = np.arange(len(hourly_distribution['hours']))
                width = 0.35
                ax.bar(x - width/2, hourly_distribution['entry'], width, label='Entry', color='blue', alpha=0.7)
                ax.bar(x + width/2, hourly_distribution['exit'], width, label='Exit', color='red', alpha=0.7)
                ax.set_title(f"Monthly Hourly Distribution ({start_date.strftime('%B %Y')})")
                ax.set_xlabel('Hour of Day')
                ax.set_ylabel('Number of Vehicles')
                ax.set_xticks(x)
                ax.set_xticklabels([f"{hour}:00" for hour in hourly_distribution['hours']])
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            
            # Vehicle statistics page
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 5))
            
            # Authorized vs Unauthorized pie chart
            labels = ['Authorized', 'Unauthorized']
            sizes = [vehicle_stats['authorized_vehicles'], vehicle_stats['unauthorized_vehicles']]
            colors = ['green', 'red']
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.axis('equal')
            ax1.set_title('Vehicle Authorization')
            
            # Most frequent vehicles bar chart
            if vehicle_stats['most_frequent_vehicles']:
                plates = list(vehicle_stats['most_frequent_vehicles'].keys())
                counts = list(vehicle_stats['most_frequent_vehicles'].values())
                y_pos = np.arange(len(plates))
                ax2.barh(y_pos, counts, align='center', color='blue', alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(plates)
                ax2.invert_yaxis()  # labels read top-to-bottom
                ax2.set_xlabel('Number of Accesses')
                ax2.set_title('Most Frequent Vehicles')
            
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            
            # Parking duration statistics page
            if parking_stats and parking_stats['duration_distribution']:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 5))
                
                # Duration statistics
                stats_text = (
                    f"Average Duration: {parking_stats['avg_duration_minutes'] / 60:.2f} hours\n"
                    f"Maximum Duration: {parking_stats['max_duration_minutes'] / 60:.2f} hours\n"
                    f"Minimum Duration: {parking_stats['min_duration_minutes']:.2f} minutes"
                )
                ax1.text(0.5, 0.5, stats_text, ha='center', va='center', fontsize=12)
                ax1.axis('off')
                ax1.set_title('Parking Duration Statistics')
                
                # Duration distribution bar chart
                categories = list(parking_stats['duration_distribution'].keys())
                values = list(parking_stats['duration_distribution'].values())
                y_pos = np.arange(len(categories))
                ax2.barh(y_pos, values, align='center', color='green', alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(categories)
                ax2.invert_yaxis()  # labels read top-to-bottom
                ax2.set_xlabel('Number of Vehicles')
                ax2.set_title('Parking Duration Distribution')
                
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
        
        return filename
