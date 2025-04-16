# Add this to the top of camera_routes.py
try:
    from src.database.db_manager import DatabaseManager
except ImportError:
    try:
        from src.db.manager import DatabaseManager
    except ImportError:
        DatabaseManager = None
        print("Warning: Could not import DatabaseManager")
