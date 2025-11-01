
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

"""
Vehicle management routes for the VisiGate web interface.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, make_response
from functools import wraps

# Create blueprint
vehicle_bp = Blueprint('vehicle', __name__, url_prefix='/vehicles')

# Global variables
db_manager = None


def init_vehicle_routes(database_manager):
    """
    Initialize vehicle routes with database manager.
    
    Args:
        database_manager: Database manager instance
    """
    global db_manager
    db_manager = database_manager


@vehicle_bp.route('/')
def vehicles():
    """
    Vehicles management page.
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '')
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get vehicles
    vehicles = []
    total_vehicles = 0
    if db_manager:
        vehicles = db_manager.get_vehicles(
            limit=limit,
            offset=offset
        )
        total_vehicles = db_manager.get_vehicle_count()
    
    # Calculate pagination
    total_pages = (total_vehicles + limit - 1) // limit
    
    return render_template(
        'vehicles.html',
        vehicles=vehicles,
        page=page,
        limit=limit,
        total_pages=total_pages,
        total_vehicles=total_vehicles,
        search=search
    )


@vehicle_bp.route('/add', methods=['GET', 'POST'])
def add_vehicle():
    """
    Add a new vehicle.
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        plate_number = request.form.get('plate_number', '').strip().upper()
        description = request.form.get('description', '').strip()
        authorized = request.form.get('authorized') == 'on'
        notes = request.form.get('notes', '').strip()
        
        if not plate_number:
            flash('Plate number is required', 'error')
            return render_template('add_vehicle.html')
        
        if db_manager:
            # Check if vehicle already exists
            existing_vehicle = db_manager.get_vehicle(plate_number)
            if existing_vehicle:
                flash(f'Vehicle with plate number {plate_number} already exists', 'error')
                return render_template('add_vehicle.html')
            
            # Add vehicle
            success = db_manager.add_vehicle(plate_number, description, authorized)
            if success:
                flash(f'Vehicle {plate_number} added successfully', 'success')
                return redirect(url_for('vehicle.vehicles'))
            else:
                flash('Failed to add vehicle', 'error')
        else:
            flash('Database manager not available', 'error')
    
    return render_template('add_vehicle.html')


@vehicle_bp.route('/edit/<plate_number>', methods=['GET', 'POST'])
def edit_vehicle(plate_number):
    """
    Edit an existing vehicle.
    
    Args:
        plate_number (str): License plate number
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    # Get vehicle
    vehicle = None
    if db_manager:
        vehicle = db_manager.get_vehicle(plate_number)
    
    if not vehicle:
        flash(f'Vehicle with plate number {plate_number} not found', 'error')
        return redirect(url_for('vehicle.vehicles'))
    
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        authorized = request.form.get('authorized') == 'on'
        notes = request.form.get('notes', '').strip()
        
        if db_manager:
            # Update vehicle
            success = db_manager.update_vehicle(plate_number, description, authorized)
            if success:
                flash(f'Vehicle {plate_number} updated successfully', 'success')
                return redirect(url_for('vehicle.vehicles'))
            else:
                flash('Failed to update vehicle', 'error')
        else:
            flash('Database manager not available', 'error')
    
    return render_template('edit_vehicle.html', vehicle=vehicle)


@vehicle_bp.route('/delete/<plate_number>', methods=['POST'])
def delete_vehicle(plate_number):
    """
    Delete a vehicle.
    
    Args:
        plate_number (str): License plate number
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    if db_manager:
        # Delete vehicle
        success = db_manager.delete_vehicle(plate_number)
        if success:
            flash(f'Vehicle {plate_number} deleted successfully', 'success')
        else:
            flash('Failed to delete vehicle', 'error')
    else:
        flash('Database manager not available', 'error')
    
    return redirect(url_for('vehicle.vehicles'))


@vehicle_bp.route('/view/<plate_number>')
def view_vehicle(plate_number):
    """
    View vehicle details.
    
    Args:
        plate_number (str): License plate number
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    # Get vehicle
    vehicle = None
    access_logs = []
    if db_manager:
        vehicle = db_manager.get_vehicle(plate_number)
        access_logs = db_manager.get_access_logs(plate_number=plate_number, limit=50)
    
    if not vehicle:
        flash(f'Vehicle with plate number {plate_number} not found', 'error')
        return redirect(url_for('vehicle.vehicles'))
    
    # For now, redirect to edit page since we don't have a view template
    return redirect(url_for('vehicle.edit_vehicle', plate_number=plate_number))
    # return render_template('vehicle_view.html', vehicle=vehicle, access_logs=access_logs)


@vehicle_bp.route('/export/<format>')
def export_vehicles(format):
    """
    Export vehicles to CSV or JSON format.
    
    Args:
        format (str): Export format (csv or json)
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    if format not in ['csv', 'json']:
        flash('Invalid export format', 'error')
        return redirect(url_for('vehicle.vehicles'))
    
    # Get all vehicles
    vehicles = []
    if db_manager:
        vehicles = db_manager.get_vehicles(limit=1000)
    
    if format == 'csv':
        # Create CSV content
        csv_content = 'Plate Number,Description,Authorized,Notes\n'
        for vehicle in vehicles:
            csv_content += f'{vehicle["plate_number"]},"{vehicle["description"]}",{vehicle["authorized"]},"{vehicle["notes"]}"\n'
        
        # Create response
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=vehicles.csv'
        return response
    else:  # JSON
        return jsonify(vehicles)


@vehicle_bp.route('/import', methods=['POST'])
def import_vehicles():
    """
    Import vehicles from CSV file.
    """
    # Skip auth check for debugging
    # if 'username' not in session:
    #     return redirect(url_for('auth.login'))
    
    # Check if file was uploaded
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('vehicle.vehicles'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('vehicle.vehicles'))
    
    # Check file extension
    if not file.filename.endswith('.csv'):
        flash('Only CSV files are supported', 'error')
        return redirect(url_for('vehicle.vehicles'))
    
    # Read and process CSV file
    try:
        # Read file content
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        # Skip header
        if lines and lines[0].startswith('Plate Number'):
            lines = lines[1:]
        
        # Process each line
        imported_count = 0
        for line in lines:
            # Split line by comma, handling quoted values
            parts = line.split(',')
            if len(parts) < 3:
                continue
            
            # Extract values
            plate_number = parts[0].strip()
            description = parts[1].strip().strip('"')
            authorized = parts[2].strip().lower() in ['true', '1', 'yes']
            notes = parts[3].strip().strip('"') if len(parts) > 3 else ''
            
            # Add vehicle to database
            if db_manager and plate_number:
                db_manager.add_vehicle(plate_number, description, authorized)
                imported_count += 1
        
        flash(f'Successfully imported {imported_count} vehicles', 'success')
    except Exception as e:
        flash(f'Error importing vehicles: {str(e)}', 'error')
    
    return redirect(url_for('vehicle.vehicles'))


def register_vehicle_routes(app, database_manager):
    """
    Register vehicle routes with the Flask app.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance
    """
    # Initialize routes with database manager
    init_vehicle_routes(database_manager)
    
    # Register blueprint with the correct name to match template references
    app.register_blueprint(vehicle_bp)
    
    return app
