import logging
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session
from functools import wraps
from src.config.settings import save_config
from src.utils.mode_permissions import mode_access_required

logger = logging.getLogger('AMSLPR.web.parking')

parking_bp = Blueprint('parking', __name__, url_prefix='/parking')

# Get user manager from app config
def get_user_manager():
    return current_app.config.get('USER_MANAGER')

@parking_bp.route('/')
@mode_access_required('parking', get_user_manager)
def parking_index():
    """
    Redirect to parking dashboard.
    """
    return redirect(url_for('parking.parking_dashboard'))

@parking_bp.route('/dashboard')
@mode_access_required('parking', get_user_manager)
def parking_dashboard():
    """
    Parking dashboard.
    """
    try:
        db_manager = current_app.config.get('DB_MANAGER')
        config = current_app.config.get('AMSLPR_CONFIG', {})
        
        # If DB_MANAGER is not available, use mock data
        if not db_manager:
            logger.warning("DB_MANAGER not found in app config. Using mock data.")
            stats = {
                'total_sessions': 0,
                'active_sessions': 0,
                'completed_sessions': 0,
                'total_revenue': 0,
                'avg_duration_minutes': 0
            }
            active_sessions = []
            completed_sessions = []
        else:
            # Get parking statistics
            stats = db_manager.get_parking_statistics()
            
            # Get active sessions
            active_sessions = []
            sessions = db_manager.get_parking_sessions(status='pending', limit=10)
            for session in sessions:
                if not session.get('exit_time'):
                    # Calculate current duration
                    entry_time = datetime.strptime(session['entry_time'], '%Y-%m-%d %H:%M:%S')
                    duration = (datetime.now() - entry_time).total_seconds() / 60
                    session['current_duration'] = round(duration, 1)
                    active_sessions.append(session)
            
            # Get recent completed sessions
            completed_sessions = db_manager.get_parking_sessions(status='paid', limit=10)
        
        return render_template(
            'parking/dashboard.html',
            stats=stats,
            active_sessions=active_sessions,
            completed_sessions=completed_sessions,
            config=config
        )
    except Exception as e:
        logger.error(f"Error in parking dashboard: {str(e)}")
        # Fallback to a simple template if there's an error
        return render_template('error.html', 
                              error_title="Parking Dashboard Error",
                              error_message="There was an error loading the parking dashboard. The database may not be configured properly.",
                              back_url="/dashboard")

@parking_bp.route('/settings', methods=['GET', 'POST'])
@mode_access_required('parking', get_user_manager)
def parking_settings():
    """
    Parking settings.
    """
    try:
        config = current_app.config.get('AMSLPR_CONFIG', {})
        
        # Ensure parking config section exists
        if 'parking' not in config:
            config['parking'] = {}
        if 'rates' not in config['parking']:
            config['parking']['rates'] = {}
        if 'nayax' not in config:
            config['nayax'] = {}
        
        if request.method == 'POST':
            # Update car park operating mode settings
            config['parking']['entry_exit_mode'] = request.form.get('entry_exit_mode', 'single_camera')
            config['parking']['payment_mode'] = request.form.get('payment_mode', 'hourly')
            config['parking']['max_capacity'] = int(request.form.get('max_capacity', 100))
            config['parking']['grace_period'] = int(request.form.get('grace_period', 15))
            config['parking']['require_payment_on_exit'] = 'require_payment_on_exit' in request.form
            
            # Update currency settings
            config['parking']['currency'] = request.form.get('currency', 'USD')
            config['parking']['currency_symbol'] = request.form.get('currency_symbol', '$')
            
            # Update rates based on payment mode
            payment_mode = request.form.get('payment_mode', 'hourly')
            if payment_mode == 'fixed':
                config['parking']['fixed_rate'] = float(request.form.get('fixed_rate', 5.00))
            elif payment_mode == 'hourly':
                config['parking']['hourly_rate'] = float(request.form.get('hourly_rate', 2.00))
            elif payment_mode == 'tiered':
                # Process tiered rates
                tier_hours = request.form.getlist('tier_hours[]')
                tier_rates = request.form.getlist('tier_rates[]')
                tiered_rates = []
                
                for i in range(len(tier_hours)):
                    if i < len(tier_rates):
                        try:
                            tiered_rates.append({
                                'hours': int(tier_hours[i]),
                                'rate': float(tier_rates[i])
                            })
                        except (ValueError, TypeError):
                            pass
                
                config['parking']['tiered_rates'] = tiered_rates
            
            # Update payment integration settings
            config['parking']['payment_enabled'] = 'payment_enabled' in request.form
            config['parking']['payment_methods'] = request.form.getlist('payment_methods[]')
            
            # Update Nayax settings if present in the form
            if 'nayax_enabled' in request.form:
                config['nayax']['enabled'] = True
                config['nayax']['api_key'] = request.form.get('nayax_api_key', '')
                config['nayax']['terminal_id'] = request.form.get('nayax_terminal_id', '')
                
                # If Nayax is enabled, make sure the pricing settings are initialized
                if 'nayax' not in config['parking']:
                    config['parking']['nayax'] = {}
                    
                # Copy the general pricing settings to Nayax pricing settings if they don't exist
                if 'pricing_mode' not in config['parking']['nayax']:
                    config['parking']['nayax']['pricing_mode'] = payment_mode
                    
                    if payment_mode == 'fixed':
                        config['parking']['nayax']['fixed_rate'] = config['parking']['fixed_rate']
                    elif payment_mode == 'hourly':
                        config['parking']['nayax']['hourly_rate'] = config['parking']['hourly_rate']
                    elif payment_mode == 'tiered':
                        if 'tiered_rates' in config['parking']:
                            config['parking']['nayax']['tiers'] = [{'hours': tier['hours'], 'rate': tier['rate']} for tier in config['parking']['tiered_rates']]
            else:
                config['nayax']['enabled'] = False
            
            # Save config
            save_config(config)
            
            flash('Parking settings updated successfully', 'success')
            return redirect(url_for('parking.parking_settings'))
        
        return render_template('parking/settings.html', config=config)
    except Exception as e:
        logger.error(f"Error updating parking settings: {e}")
        flash(f"Error updating parking settings: {str(e)}", 'danger')
        return redirect(url_for('parking.parking_dashboard'))

@parking_bp.route('/nayax-pricing', methods=['GET', 'POST'])
@mode_access_required('parking', get_user_manager)
def nayax_pricing():
    """
    Configure Nayax pricing tiers and free period settings.
    """
    try:
        config = current_app.config.get('AMSLPR_CONFIG', {})
        
        # Ensure the nayax config sections exist
        if 'nayax' not in config:
            config['nayax'] = {'enabled': False}
            
        if 'parking' not in config:
            config['parking'] = {}
            
        if 'nayax' not in config['parking']:
            config['parking']['nayax'] = {}
            
        # If Nayax is not enabled, redirect to parking settings
        if not config['nayax'].get('enabled', False):
            flash('Nayax integration is not enabled. Please enable it in parking settings first.', 'warning')
            return redirect(url_for('parking.parking_settings'))
        
        if request.method == 'POST':
            # Free Period Settings
            config['parking']['nayax']['free_period_enabled'] = 'free_period_enabled' in request.form
            config['parking']['nayax']['free_period_minutes'] = int(request.form.get('free_period_minutes', 30))
            
            # Pricing Mode
            config['parking']['nayax']['pricing_mode'] = request.form.get('pricing_mode', 'hourly')
            
            # Fixed Rate Settings
            if config['parking']['nayax']['pricing_mode'] == 'fixed':
                config['parking']['nayax']['fixed_rate'] = float(request.form.get('fixed_rate', 5.00))
            
            # Hourly Rate Settings
            if config['parking']['nayax']['pricing_mode'] == 'hourly':
                config['parking']['nayax']['hourly_rate'] = float(request.form.get('hourly_rate', 2.00))
                config['parking']['nayax']['daily_max_rate'] = float(request.form.get('daily_max_rate', 20.00))
                config['parking']['nayax']['partial_hour_billing'] = 'partial_hour_billing' in request.form
            
            # Tiered Rate Settings
            if config['parking']['nayax']['pricing_mode'] == 'tiered':
                tier_hours = request.form.getlist('tier_hours[]')
                tier_rates = request.form.getlist('tier_rates[]')
                
                tiers = []
                for i in range(len(tier_hours)):
                    if i < len(tier_rates):
                        tiers.append({
                            'hours': float(tier_hours[i]),
                            'rate': float(tier_rates[i])
                        })
                
                # Sort tiers by hours
                tiers.sort(key=lambda x: x['hours'])
                config['parking']['nayax']['tiers'] = tiers
            
            # Special Rates
            config['parking']['nayax']['weekend_rates_enabled'] = 'weekend_rates_enabled' in request.form
            if config['parking']['nayax']['weekend_rates_enabled']:
                config['parking']['nayax']['weekend_hourly_rate'] = float(request.form.get('weekend_hourly_rate', 1.50))
                config['parking']['nayax']['weekend_daily_max'] = float(request.form.get('weekend_daily_max', 15.00))
            
            config['parking']['nayax']['overnight_rate_enabled'] = 'overnight_rate_enabled' in request.form
            if config['parking']['nayax']['overnight_rate_enabled']:
                config['parking']['nayax']['overnight_rate'] = float(request.form.get('overnight_rate', 10.00))
                config['parking']['nayax']['overnight_start_hour'] = int(request.form.get('overnight_start_hour', 20))
                config['parking']['nayax']['overnight_end_hour'] = int(request.form.get('overnight_end_hour', 8))
            
            # Save config
            save_config(config)
            flash('Nayax pricing settings updated successfully', 'success')
            
        return render_template('parking/nayax_pricing.html', config=config)
    except Exception as e:
        logger.error(f"Error in Nayax pricing settings: {str(e)}")
        flash(f"Error updating Nayax pricing settings: {str(e)}", 'danger')
        return render_template('parking/nayax_pricing.html', config=config)

@parking_bp.route('/sessions', methods=['GET'])
@mode_access_required('parking', get_user_manager)
def parking_sessions():
    """
    View parking sessions.
    """
    try:
        db_manager = current_app.config.get('DB_MANAGER')
        
        # Get filter parameters from request
        plate_number = request.args.get('plate_number', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        status = request.args.get('status', 'all')
        
        if not db_manager:
            # Mock data for development/testing
            sessions = []
        else:
            # Get sessions based on filters
            filter_params = {}
            if plate_number:
                filter_params['license_plate'] = plate_number
            if status and status != 'all':
                filter_params['status'] = status
                
            # Apply date filters if provided
            if start_date or end_date:
                # Date filtering would be implemented in the db_manager
                pass
                
            sessions = db_manager.get_parking_sessions(**filter_params, limit=50)
            
            # Calculate current duration for active sessions
            for session in sessions:
                if not session.get('exit_time') and session.get('entry_time'):
                    entry_time = datetime.strptime(session['entry_time'], '%Y-%m-%d %H:%M:%S')
                    duration = (datetime.now() - entry_time).total_seconds() / 60
                    session['current_duration'] = round(duration, 1)
        
        # Handle export formats
        export_format = request.args.get('format')
        if export_format == 'csv':
            # Generate CSV export
            # Implementation would go here
            pass
        elif export_format == 'pdf':
            # Generate PDF export
            # Implementation would go here
            pass
        
        return render_template('parking/sessions.html', sessions=sessions)
    except Exception as e:
        logger.error(f"Error in parking sessions: {str(e)}")
        return render_template('error.html', 
                              error_title="Parking Sessions Error",
                              error_message="There was an error loading the parking sessions.",
                              back_url="/dashboard")

@parking_bp.route('/session/<session_id>')
@mode_access_required('parking', get_user_manager)
def view_session(session_id):
    """
    View a specific parking session.
    """
    try:
        db_manager = current_app.config.get('DB_MANAGER')
        
        if not db_manager:
            # Mock data for development/testing
            session = {
                'id': session_id,
                'license_plate': 'DEMO123',
                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'exit_time': None,
                'status': 'pending',
                'fee': 0,
                'payment_method': None,
                'notes': 'Demo session'
            }
        else:
            # Get session details
            session = db_manager.get_parking_session(session_id)
            if not session:
                flash('Parking session not found.', 'error')
                return redirect(url_for('parking.parking_sessions'))
        
        return render_template('parking/session_details.html', session=session)
    except Exception as e:
        logger.error(f"Error in view session: {str(e)}")
        return render_template('error.html', 
                              error_title="Session Details Error",
                              error_message=f"There was an error loading the parking session details for ID: {session_id}.",
                              back_url="/parking/sessions")

@parking_bp.route('/reports', methods=['GET'])
@mode_access_required('parking', get_user_manager)
def parking_reports():
    """
    Parking reports.
    """
    try:
        db_manager = current_app.config.get('DB_MANAGER')
        
        # Get date range from request
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # If DB_MANAGER is not available, use mock data
        if not db_manager:
            logger.warning("DB_MANAGER not found in app config. Using mock data.")
            stats = {
                'total_sessions': 0,
                'active_sessions': 0,
                'completed_sessions': 0,
                'total_revenue': 0,
                'avg_fee': 0,
                'avg_duration_minutes': 0,
                'max_fee': 0,
                'max_duration_minutes': 0,
                'free_sessions': 0,
                'card_payments': 0,
                'cash_payments': 0,
                'app_payments': 0,
                'other_payments': 0,
                'card_payments_percentage': 0,
                'cash_payments_percentage': 0,
                'other_payments_percentage': 0
            }
            daily_labels = []
            daily_data = []
        else:
            # Get parking statistics for the date range
            stats = db_manager.get_parking_statistics(start_date=start_date, end_date=end_date)
            
            # Add missing fields required by the template
            payment_methods = stats.get('payment_methods', {})
            total_paid = sum(payment_methods.values()) if payment_methods else 0
            
            # Calculate payment method stats
            stats['card_payments'] = payment_methods.get('card', 0)
            stats['cash_payments'] = payment_methods.get('cash', 0)
            stats['app_payments'] = payment_methods.get('app', 0)
            stats['other_payments'] = sum([v for k, v in payment_methods.items() if k not in ['card', 'cash', 'app']]) if payment_methods else 0
            
            # Calculate percentages
            if total_paid > 0:
                stats['card_payments_percentage'] = round((stats['card_payments'] / total_paid) * 100)
                stats['cash_payments_percentage'] = round((stats['cash_payments'] / total_paid) * 100)
                stats['other_payments_percentage'] = round(((stats['other_payments'] + stats['app_payments']) / total_paid) * 100)
            else:
                stats['card_payments_percentage'] = 0
                stats['cash_payments_percentage'] = 0
                stats['other_payments_percentage'] = 0
            
            # Calculate average fee
            if stats.get('completed_sessions', 0) > 0 and stats.get('total_revenue', 0) > 0:
                stats['avg_fee'] = round(stats['total_revenue'] / stats['completed_sessions'], 2)
            else:
                stats['avg_fee'] = 0
                
            # Set default values for missing fields
            stats['max_fee'] = 0
            stats['max_duration_minutes'] = 0
            stats['free_sessions'] = 0
            
            # Get daily revenue data for chart
            daily_revenue = db_manager.get_daily_revenue(start_date=start_date, end_date=end_date)
            daily_labels = [day['date'] for day in daily_revenue]
            daily_data = [day['revenue'] for day in daily_revenue]
        
        return render_template(
            'parking/reports.html',
            stats=stats,
            daily_labels=daily_labels,
            daily_data=daily_data,
            config=current_app.config.get('AMSLPR_CONFIG', {})
        )
    except Exception as e:
        logger.error(f"Error in parking reports: {str(e)}")
        return render_template('error.html', 
                              error_title="Parking Reports Error",
                              error_message="There was an error loading the parking reports.",
                              back_url="/dashboard")

@parking_bp.route('/api/session/<session_id>', methods=['GET'])
def api_get_session(session_id):
    """
    Get session details via API.
    """
    try:
        db_manager = current_app.config.get('DB_MANAGER')
        
        if not db_manager:
            return jsonify({'error': 'Database not configured'}), 500
        
        session = db_manager.get_parking_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify(session)
    except Exception as e:
        logger.error(f"API error in get session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@parking_bp.route('/api/calculate-fee', methods=['POST'])
def api_calculate_fee():
    """
    Calculate parking fee via API.
    """
    try:
        db_manager = current_app.config.get('DB_MANAGER')
        config = current_app.config.get('AMSLPR_CONFIG', {})
        data = request.json
        
        if not db_manager:
            return jsonify({'error': 'Database not configured'}), 500
        
        if not data or 'session_id' not in data:
            return jsonify({'error': 'Missing session_id'}), 400
        
        session_id = data['session_id']
        session = db_manager.get_parking_session(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Calculate fee based on parking duration
        fee = db_manager.calculate_parking_fee(session_id)
        
        return jsonify({'fee': fee})
    except Exception as e:
        logger.error(f"API error in calculate fee: {str(e)}")
        return jsonify({'error': str(e)}), 500

@parking_bp.route('/api/payment/request', methods=['POST'])
@mode_access_required('parking', get_user_manager)
def api_request_payment():
    """
    Request payment via API.
    """
    db_manager = current_app.config.get('DB_MANAGER')
    nayax_integration = current_app.config.get('NAYAX_INTEGRATION')
    
    try:
        data = request.json
        session_id = data.get('session_id')
        amount = data.get('amount')
        
        if not session_id or not amount:
            return jsonify({'error': 'Session ID and amount are required'}), 400
        
        # Get session
        if not db_manager:
            return jsonify({'error': 'DB_MANAGER not found'}), 500
        
        session = db_manager.get_parking_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if Nayax integration is available
        if not nayax_integration:
            return jsonify({'error': 'Nayax integration not available'}), 500
        
        # Request payment
        result = nayax_integration.request_payment(amount, session_id, session['plate_number'])
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error requesting payment: {e}")
        return jsonify({'error': str(e)}), 500

@parking_bp.route('/api/payment/status', methods=['GET'])
@mode_access_required('parking', get_user_manager)
def api_payment_status():
    """
    Get payment status via API.
    """
    nayax_integration = current_app.config.get('NAYAX_INTEGRATION')
    
    try:
        # Get current transaction
        if not nayax_integration:
            return jsonify({'error': 'Nayax integration not available'}), 500
        
        transaction = nayax_integration.get_current_transaction()
        if not transaction:
            return jsonify({'status': 'none', 'message': 'No active transaction'})
        
        return jsonify(transaction)
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return jsonify({'error': str(e)}), 500

@parking_bp.route('/api/payment/cancel', methods=['POST'])
@mode_access_required('parking', get_user_manager)
def api_cancel_payment():
    """
    Cancel payment via API.
    """
    nayax_integration = current_app.config.get('NAYAX_INTEGRATION')
    
    try:
        # Check if Nayax integration is available
        if not nayax_integration:
            return jsonify({'error': 'Nayax integration not available'}), 500
        
        # Cancel current transaction
        result = nayax_integration.cancel_current_transaction()
        
        return jsonify({'success': result})
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        return jsonify({'error': str(e)}), 500

@parking_bp.route('/api/manual-payment', methods=['POST'])
@mode_access_required('parking', get_user_manager)
def api_manual_payment():
    """
    Record manual payment via API.
    """
    db_manager = current_app.config.get('DB_MANAGER')
    
    try:
        data = request.json
        session_id = data.get('session_id')
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'cash')
        notes = data.get('notes', '')
        
        if not session_id or not amount:
            return jsonify({'error': 'Session ID and amount are required'}), 400
        
        # Get session
        if not db_manager:
            return jsonify({'error': 'DB_MANAGER not found'}), 500
        
        session = db_manager.get_parking_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Record payment
        transaction_id = db_manager.record_payment(
            session_id=session_id,
            amount=float(amount),
            payment_method=payment_method,
            transaction_id=f"MANUAL{int(time.time())}",
            status='completed',
            response_message=notes
        )
        
        return jsonify({'success': True, 'transaction_id': transaction_id})
    except Exception as e:
        logger.error(f"Error recording manual payment: {e}")
        return jsonify({'error': str(e)}), 500
