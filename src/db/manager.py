"""Database manager for AMSLPR."""
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.ext.declarative import declarative_base
from loguru import logger

Base = declarative_base()

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file. If not provided,
                    will use the default path in the instance directory.
        """
        if not db_path:
            # Default to instance directory
            instance_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance')
            os.makedirs(instance_dir, exist_ok=True)
            db_path = os.path.join(instance_dir, 'amslpr.db')
        
        self.db_path = db_path
        self._engine: Optional[Engine] = None
        self._session_factory = None
        self._scoped_session = None
    
    def init_db(self) -> None:
        """Initialize the database by creating all tables."""
        if not self._engine:
            self._engine = create_engine(f'sqlite:///{self.db_path}')
            self._session_factory = sessionmaker(bind=self._engine)
            self._scoped_session = scoped_session(self._session_factory)
            Base.query = self._scoped_session.query_property()
        
        # Import all models to ensure they are registered with Base
        from src.db.models import Vehicle, AccessLog, ApiKey, User, ParkingSession
        
        # Create all tables
        Base.metadata.create_all(bind=self._engine)
        logger.info(f"Database initialized at: {self.db_path}")
    
    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            A new SQLAlchemy session.
        
        Raises:
            RuntimeError: If the database has not been initialized.
        """
        if not self._scoped_session:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._scoped_session()
    
    def remove_session(self) -> None:
        """Remove the current session."""
        if self._scoped_session:
            self._scoped_session.remove()
    
    def close(self) -> None:
        """Close all database connections."""
        if self._scoped_session:
            self._scoped_session.remove()
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")
    
    def get_access_logs(self, limit=None, vehicle_id=None, plate_number=None, start_date=None, end_date=None):
        """Get access logs with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            vehicle_id: Filter by vehicle ID
            plate_number: Filter by plate number (alternative to vehicle_id)
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            
        Returns:
            List of AccessLog objects
        """
        try:
            from src.db.models import AccessLog, Vehicle
            
            session = self.get_session()
            query = session.query(AccessLog).join(Vehicle)
            
            if vehicle_id:
                query = query.filter(AccessLog.vehicle_id == vehicle_id)
            elif plate_number:
                query = query.filter(Vehicle.plate_number == plate_number)
                
            if start_date:
                query = query.filter(AccessLog.timestamp >= start_date)
                
            if end_date:
                query = query.filter(AccessLog.timestamp <= end_date)
            
            # Order by most recent first
            query = query.order_by(AccessLog.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
                
            return query.all()
        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return []
    
    def get_access_log_count(self, today_only=False):
        """Get count of access logs.
        
        Args:
            today_only: If True, only count logs from today
            
        Returns:
            Integer count of logs
        """
        try:
            from src.db.models import AccessLog
            import datetime
            
            session = self.get_session()
            query = session.query(AccessLog)
            
            if today_only:
                today = datetime.datetime.now().date()
                tomorrow = today + datetime.timedelta(days=1)
                query = query.filter(
                    AccessLog.timestamp >= datetime.datetime.combine(today, datetime.time.min),
                    AccessLog.timestamp < datetime.datetime.combine(tomorrow, datetime.time.min)
                )
                
            return query.count()
        except Exception as e:
            logger.error(f"Error getting access log count: {e}")
            return 0
    
    def get_vehicle_count(self, authorized=None):
        """Get count of vehicles.
        
        Args:
            authorized: If provided, filter by authorization status
            
        Returns:
            Integer count of vehicles
        """
        try:
            from src.db.models import Vehicle
            
            session = self.get_session()
            query = session.query(Vehicle)
            
            if authorized is not None:
                query = query.filter(Vehicle.is_authorized == authorized)
                
            return query.count()
        except Exception as e:
            logger.error(f"Error getting vehicle count: {e}")
            return 0
    
    def get_vehicles(self, limit=None, offset=None, authorized=None):
        """Get vehicles with optional filtering.
        
        Args:
            limit: Maximum number of vehicles to return
            offset: Number of vehicles to skip
            authorized: If provided, filter by authorization status
            
        Returns:
            List of Vehicle objects
        """
        try:
            from src.db.models import Vehicle
            
            session = self.get_session()
            query = session.query(Vehicle)
            
            if authorized is not None:
                query = query.filter(Vehicle.is_authorized == authorized)
            
            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
                
            if limit is not None:
                query = query.limit(limit)
                
            return query.all()
        except Exception as e:
            logger.error(f"Error getting vehicles: {e}")
            return []
    
    def get_parking_sessions(self, limit=None, offset=None, plate_number=None, status=None, start_time=None, end_time=None):
        """Get parking sessions with optional filtering.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            plate_number: Filter by plate number
            status: Filter by status ('active', 'completed', 'all')
            start_time: Filter by start time (sessions after this time)
            end_time: Filter by end time (sessions before this time)
            
        Returns:
            List of ParkingSession objects
        """
        try:
            from src.db.models import ParkingSession, Vehicle
            
            session = self.get_session()
            query = session.query(ParkingSession).join(Vehicle)
            
            # Apply filters
            if plate_number:
                query = query.filter(Vehicle.plate_number == plate_number)
                
            if status:
                if status == 'active':
                    query = query.filter(ParkingSession.exit_time == None)
                elif status == 'completed':
                    query = query.filter(ParkingSession.exit_time != None)
            
            if start_time:
                query = query.filter(ParkingSession.entry_time >= start_time)
                
            if end_time:
                query = query.filter(ParkingSession.entry_time <= end_time)
            
            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
                
            if limit is not None:
                query = query.limit(limit)
                
            return query.all()
        except Exception as e:
            logger.error(f"Error getting parking sessions: {e}")
            return []
    
    def get_parking_statistics(self, start_date=None, end_date=None):
        """Get parking statistics for reporting.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dictionary with statistics
        """
        try:
            from src.db.models import ParkingSession
            from sqlalchemy import func
            import datetime
            
            session = self.get_session()
            query = session.query(ParkingSession)
            
            # Apply date filters if provided
            if start_date:
                query = query.filter(ParkingSession.entry_time >= start_date)
            if end_date:
                query = query.filter(ParkingSession.entry_time <= end_date)
            
            # Get all sessions for the period
            sessions = query.all()
            
            # Calculate statistics
            total_sessions = len(sessions)
            active_sessions = sum(1 for s in sessions if s.exit_time is None)
            completed_sessions = sum(1 for s in sessions if s.exit_time is not None)
            
            # Revenue statistics
            total_revenue = sum(s.fee for s in sessions if s.fee is not None)
            paid_sessions = [s for s in sessions if s.paid]
            free_sessions = sum(1 for s in sessions if s.fee == 0)
            
            # Duration statistics
            durations = [s.duration for s in sessions if s.duration is not None]
            avg_duration_minutes = sum(durations) / len(durations) if durations else 0
            max_duration_minutes = max(durations) if durations else 0
            
            # Fee statistics
            fees = [s.fee for s in sessions if s.fee is not None]
            avg_fee = sum(fees) / len(fees) if fees else 0
            max_fee = max(fees) if fees else 0
            
            # Payment method statistics
            payment_methods = {
                'card': 0,
                'cash': 0,
                'app': 0,
                'other': 0
            }
            
            # Return statistics
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'completed_sessions': completed_sessions,
                'total_revenue': total_revenue,
                'avg_fee': avg_fee,
                'avg_duration_minutes': avg_duration_minutes,
                'max_fee': max_fee,
                'max_duration_minutes': max_duration_minutes,
                'free_sessions': free_sessions,
                'payment_methods': payment_methods
            }
        except Exception as e:
            logger.error(f"Error getting parking statistics: {e}")
            return {
                'total_sessions': 0,
                'active_sessions': 0,
                'completed_sessions': 0,
                'total_revenue': 0,
                'avg_fee': 0,
                'avg_duration_minutes': 0,
                'max_fee': 0,
                'max_duration_minutes': 0,
                'free_sessions': 0,
                'payment_methods': {}
            }
    
    def get_daily_revenue(self, start_date=None, end_date=None):
        """Get daily revenue data for reporting.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            List of dictionaries with date and revenue
        """
        try:
            from src.db.models import ParkingSession
            from sqlalchemy import func
            import datetime
            from datetime import timedelta
            
            # Parse dates if they are strings
            if isinstance(start_date, str) and start_date:
                start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            if isinstance(end_date, str) and end_date:
                end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            
            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = datetime.datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.datetime.now()
                
            # Make sure end_date is at the end of the day
            end_date = datetime.datetime.combine(end_date.date(), datetime.time.max)
            
            # Initialize result with all dates in range
            result = []
            current_date = start_date.date()
            while current_date <= end_date.date():
                result.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'revenue': 0
                })
                current_date += timedelta(days=1)
            
            # Get session data from database
            session = self.get_session()
            
            # Query to get sum of fees grouped by date
            query = session.query(
                func.date(ParkingSession.entry_time).label('date'),
                func.sum(ParkingSession.fee).label('revenue')
            ).filter(
                ParkingSession.entry_time >= start_date,
                ParkingSession.entry_time <= end_date,
                ParkingSession.fee != None
            ).group_by(
                func.date(ParkingSession.entry_time)
            )
            
            # Update result with actual revenue data
            revenue_data = query.all()
            date_to_revenue = {row.date.strftime('%Y-%m-%d'): float(row.revenue) for row in revenue_data}
            
            for day in result:
                if day['date'] in date_to_revenue:
                    day['revenue'] = date_to_revenue[day['date']]
            
            return result
        except Exception as e:
            logger.error(f"Error getting daily revenue: {e}")
            return []
