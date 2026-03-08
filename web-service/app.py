import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
import json
from functools import wraps
import logging
import random
from datetime import datetime, timedelta
import csv
from io import StringIO
import requests

# Cargar variables de entorno al inicio
load_dotenv()

app = Flask(__name__)
# Configurar CORS para permitir peticiones del bot y otros orígenes
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
# Increase max content length to handle large JSON files (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Health check endpoint for Render
@app.route('/health')
def health_check():
    """Health check endpoint for Render deployment verification"""
    try:
        # Basic health check
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'pythontutor-web',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Global error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions"""
    logger.error(f"Uncaught exception: {e}", exc_info=True)
    return jsonify({'error': 'An unexpected error occurred'}), 500

# Root route - landing page
@app.route('/')
def index():
    """Landing page - show public index"""
    logger.info("=== ACCESSING ROOT ROUTE ===")
    logger.info(f"Request path: {request.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"User authenticated: {current_user.is_authenticated}")
    logger.info("Serving landing page...")
    return render_template('public/index.html')

@app.route('/admin')
def admin():
    """Admin login redirect"""
    logger.info("Accessing /admin route - redirecting to login")
    return redirect(url_for('login'))

# Verificar variables de entorno críticas
required_env_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")

# Supabase initialization
try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if supabase_url and supabase_key:
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase connected successfully")
    else:
        supabase = None
        logger.error("Supabase credentials not found")
except Exception as e:
    logger.error(f"Supabase connection error: {e}")
    supabase = None

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder al panel administrativo'
login_manager.login_message_category = 'warning'

class AdminUser(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Global user cache for invalidation
user_cache = {}

@login_manager.user_loader
def load_user(user_id):
    if not supabase:
        return None
    
    # Verificar si el usuario está en la lista de invalidados
    if str(user_id) in user_cache.get('invalidated', set()):
        return None
    
    try:
        response = supabase.table('admin_users').select('*').eq('id', user_id).execute()
        if response.data:
            user_data = response.data[0]
            return AdminUser(user_data['id'], user_data['username'])
    except Exception as e:
        logger.error(f"Error loading user: {e}")
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not current_user.is_authenticated:
                logger.info("Admin_required: User not authenticated")
                return redirect(url_for('login'))
            
            if not hasattr(current_user, 'id') or not current_user.id:
                logger.info("Admin_required: User has no valid ID")
                return redirect(url_for('login'))
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Admin_required error: {e}")
            return redirect(url_for('login'))
    return decorated_function

def admin_required_api(f):
    """Admin required decorator for API endpoints - returns JSON errors instead of redirects"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not current_user.is_authenticated:
                logger.warning("API Admin_required: User not authenticated")
                return jsonify({'error': 'Authentication required', 'error_type': 'AuthError'}), 401
            
            if not hasattr(current_user, 'id') or not current_user.id:
                logger.warning("API Admin_required: User has no valid ID")
                return jsonify({'error': 'Invalid user session', 'error_type': 'AuthError'}), 401
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API Admin_required error: {e}", exc_info=True)
            return jsonify({'error': 'Authentication error', 'error_type': 'AuthError', 'details': str(e)}), 500
    return decorated_function

# Custom Jinja filters
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except:
        return []

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('public/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template('public/500.html'), 500

# Routes - Public pages
@app.route('/features')
def features():
    return render_template('public/features.html')

@app.route('/about')
def about():
    """About page"""
    logger.info("=== ACCESSING ABOUT PAGE ===")
    return render_template('public/about.html')

@app.route('/contact')
def contact():
    """Contact page"""
    logger.info("=== ACCESSING CONTACT PAGE ===")
    return render_template('public/contact.html')

@app.route('/pricing')
def pricing():
    """Pricing page"""
    logger.info("=== ACCESSING PRICING PAGE ===")
    return render_template('public/pricing.html')

@app.route('/documentation')
def documentation():
    """Documentation page"""
    logger.info("=== ACCESSING DOCUMENTATION PAGE ===")
    return render_template('public/documentation.html')

@app.route('/tutorial')
def tutorial():
    """Tutorial page"""
    logger.info("=== ACCESSING TUTORIAL PAGE ===")
    return render_template('public/tutorial.html')

@app.route('/faq')
def faq():
    """FAQ page"""
    logger.info("=== ACCESSING FAQ PAGE ===")
    return render_template('public/faq.html')

@app.route('/blog')
def blog():
    """Blog page"""
    logger.info("=== ACCESSING BLOG PAGE ===")
    return render_template('public/blog.html')

@app.route('/support')
def support():
    """Support page"""
    logger.info("=== ACCESSING SUPPORT PAGE ===")
    return render_template('public/support.html')

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    logger.info("=== ACCESSING PRIVACY PAGE ===")
    return render_template('public/privacy.html')

@app.route('/terms')
def terms():
    """Terms of service page"""
    logger.info("=== ACCESSING TERMS PAGE ===")
    return render_template('public/terms.html')

@app.route('/admin/stats')
@admin_required
def admin_stats():
    """Admin statistics page"""
    try:
        return render_template('admin/stats.html')
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        flash('Error al cargar la página de estadísticas', 'error')
        return render_template('admin/stats.html')

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """Admin logs page"""
    try:
        return render_template('admin/logs.html')
    except Exception as e:
        logger.error(f"Admin logs error: {e}")
        flash('Error al cargar la página de logs', 'error')
        return render_template('admin/logs.html')

@app.route('/admin/settings')
@admin_required
def admin_settings():
    """Admin settings page"""
    try:
        return render_template('admin/settings.html')
    except Exception as e:
        logger.error(f"Admin settings error: {e}")
        flash('Error al cargar la página de configuración', 'error')
        return render_template('admin/settings.html')

@app.route('/admin/database')
@admin_required
def admin_database():
    """Admin database management page"""
    try:
        return render_template('admin/database.html')
    except Exception as e:
        logger.error(f"Admin database error: {e}")
        flash('Error al cargar la página de base de datos', 'error')
        return render_template('admin/database.html')

@app.route('/admin/backup')
@admin_required
def admin_backup():
    """Admin backup page"""
    try:
        return render_template('admin/backup.html')
    except Exception as e:
        logger.error(f"Admin backup error: {e}")
        flash('Error al cargar la página de backup', 'error')
        return render_template('admin/backup.html')

# Routes - Authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"Accessing login route - Method: {request.method}")
    
    if current_user.is_authenticated:
        logger.info(f"User already authenticated: {current_user.username} - redirecting to dashboard")
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"Login attempt: {username}")
        
        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('public/login.html')
        
        try:
            if not supabase:
                flash('Error de conexión con la base de datos', 'error')
                return render_template('public/login.html')
                
            response = supabase.table('admin_users').select('*').eq('username', username).execute()
            
            if response.data and check_password_hash(response.data[0]['password_hash'], password):
                user = AdminUser(response.data[0]['id'], response.data[0]['username'])
                
                # Limpiar cache de invalidación si existe
                if str(user.id) in user_cache.get('invalidated', set()):
                    user_cache['invalidated'].remove(str(user.id))
                    logger.info(f"User {user.id} removed from invalidation cache")
                
                login_user(user, remember=request.form.get('remember') == 'on')
                
                logger.info(f"Login successful: {username}")
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            
            flash('Credenciales inválidas', 'error')
            logger.warning(f"Login failed: {username}")
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Error al conectar con la base de datos', 'error')
    
    logger.info("Rendering login template for unauthenticated user")
    return render_template('public/login.html')

@app.route('/admin/logout')
def admin_logout():
    """Complete logout with cookie cleanup and user cache invalidation"""
    try:
        # 1. Invalidar usuario actual en el cache
        if current_user.is_authenticated:
            user_cache.setdefault('invalidated', set()).add(str(current_user.id))
        
        # 2. Forzar logout de Flask-Login
        from flask_login import logout_user
        logout_user()
        
        # 3. Limpiar sesión completamente
        from flask import session
        session.clear()
        session.modified = True
        
        # 4. Eliminar cookies específicas de Flask-Login
        from flask import make_response, redirect, url_for
        response = make_response(redirect(url_for('index')))
        response.delete_cookie('remember_token')
        response.delete_cookie('session')
        response.delete_cookie('_user_id')
        
        # 5. Mensaje de éxito
        try:
            flash('Has cerrado sesión exitosamente', 'success')
        except:
            pass  # Continuar sin flash si hay problemas
        
        return response
        
    except Exception as e:
        # Fallback completo con limpieza forzada
        try:
            from flask import session, redirect, url_for
            session.clear()
            session.modified = True
            return redirect(url_for('index'))
        except Exception as e2:
            # Último recurso: redirección manual
            from flask import Response
            return Response('', status=302, headers={'Location': '/'})

# Routes - Admin Panel
@app.route('/admin/dashboard')
@admin_required
def dashboard():
    try:
        # Get counts for dashboard
        total_exercises = 0
        recent_exercises = 0
        security_logs = []
        
        if supabase:
            # Get total exercises
            exercises_response = supabase.table('exercises').select('*', count='exact').execute()
            total_exercises = exercises_response.count if hasattr(exercises_response, 'count') else 0
            
            # Get recent exercises (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_response = supabase.table('exercises').select('*', count='exact').gte('created_at', week_ago).execute()
            recent_exercises = recent_response.count if hasattr(recent_response, 'count') else 0
            
            # Get recent security logs (if table exists)
            try:
                logs_response = supabase.table('security_logs').select('*').order('created_at', desc=True).limit(5).execute()
                security_logs = logs_response.data or []
            except:
                # Mock data if table doesn't exist
                security_logs = [
                    {'action': 'Login exitoso', 'created_at': datetime.now() - timedelta(hours=2)},
                    {'action': 'Usuario modificado', 'created_at': datetime.now() - timedelta(hours=5)},
                    {'action': 'Backup realizado', 'created_at': datetime.now() - timedelta(days=1)},
                    {'action': 'Contraseña cambiada', 'created_at': datetime.now() - timedelta(days=2)},
                    {'action': 'Ejercicio agregado', 'created_at': datetime.now() - timedelta(days=3)}
                ]
        
        return render_template('admin/dashboard.html', 
                             total_exercises=total_exercises,
                             recent_exercises=recent_exercises,
                             security_logs=security_logs)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error al cargar el dashboard', 'error')
        return render_template('admin/dashboard.html', 
                             total_exercises=0,
                             recent_exercises=0,
                             security_logs=[])

@app.route('/admin/bot-control')
@admin_required
def admin_bot_control():
    """Admin bot control page"""
    logger.info("=== ACCESSING BOT CONTROL ROUTE ===")
    logger.info(f"Request path: {request.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"User authenticated: {current_user.is_authenticated}")
    
    try:
        # Check if Supabase is available for bot operations
        db_connected = supabase is not None
        logger.info(f"Database connected: {db_connected}")
        
        if db_connected:
            logger.info("Bot control page loaded successfully with database connection")
        else:
            logger.warning("Bot control page loaded without database connection")
        
        logger.info("Rendering bot_control template...")
        
        # Try rendering the test template first
        try:
            return render_template('admin/bot_control_test.html', db_connected=db_connected)
        except Exception as template_error:
            logger.error(f"Error rendering test template: {template_error}")
            logger.error(f"Template error type: {type(template_error).__name__}")
            logger.error(f"Template error message: {str(template_error)}")
            
            # If test template fails, try the original
            return render_template('admin/bot_control.html', db_connected=db_connected)
        
    except Exception as e:
        logger.error(f"Admin bot control error: {e}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        
        # Don't flash error to user, just render the page with db_connected=False
        logger.info("Rendering bot_control template with db_connected=False")
        return render_template('admin/bot_control.html', db_connected=False)

@app.route('/admin/notifications')
@admin_required
def admin_notifications():
    """Admin notifications page"""
    try:
        return render_template('admin/notifications.html', db_connected=(supabase is not None))
    except Exception as e:
        logger.error(f"Admin notifications error: {e}")
        flash('Error al cargar la página de notificaciones', 'error')
        return render_template('admin/notifications.html', db_connected=False)

@app.route('/admin/exercises/debug')
@admin_required
def debug_exercises():
    """Debug endpoint para diagnosticar problemas con ejercicios"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase not connected'}), 500
        
        logger.info("🔍 Debug: Fetching exercises from Supabase...")
        exercises_response = supabase.table('exercises').select('*').order('created_at', desc=True).execute()
        exercises = exercises_response.data or []
        
        debug_info = {
            'supabase_connected': True,
            'raw_exercises_count': len(exercises),
            'exercises_sample': exercises[:3] if exercises else [],
            'template_data_count': len(exercises),
            'timestamp': datetime.now().isoformat()
        }
        
        # Verificar estructura de datos
        if exercises:
            sample_exercise = exercises[0]
            debug_info['sample_structure'] = {
                'id': sample_exercise.get('id'),
                'question_length': len(sample_exercise.get('question', '')),
                'question_preview': sample_exercise.get('question', '')[:100] + '...' if len(sample_exercise.get('question', '')) > 100 else sample_exercise.get('question', ''),
                'level': sample_exercise.get('level'),
                'options_type': type(sample_exercise.get('options')),
                'options_length': len(sample_exercise.get('options', [])),
                'correct_answer': sample_exercise.get('correct_answer'),
                'correct_answer_type': type(sample_exercise.get('correct_answer')),
                'has_explanation': bool(sample_exercise.get('explanation')),
                'created_at': sample_exercise.get('created_at')
            }
        
        logger.info(f"🔍 Debug info: {debug_info}")
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"🔍 Debug endpoint error: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/admin/exercises')
@admin_required
def admin_exercises():
    """Admin exercises management page - MEJORADO"""
    try:
        if not supabase:
            logger.warning("Admin exercises page loaded without database connection")
            return render_template('admin/exercises.html', exercises=[])
        
        # Get all exercises from Supabase
        logger.info("Fetching exercises from Supabase...")
        exercises_response = supabase.table('exercises').select('*').order('created_at', desc=True).execute()
        exercises = exercises_response.data or []
        
        logger.info(f"Raw response from Supabase: {len(exercises)} exercises")
        
        # Process exercises to ensure correct format
        processed_exercises = []
        for i, exercise in enumerate(exercises):
            logger.debug(f"Processing exercise {i+1}: ID={exercise.get('id')}, question={exercise.get('question', '')[:50]}...")
            
            # Parse options if they're stored as JSON string
            if isinstance(exercise.get('options'), str):
                try:
                    exercise['options'] = json.loads(exercise['options'])
                    logger.debug(f"Exercise {i+1}: Parsed JSON options successfully")
                except Exception as e:
                    exercise['options'] = ['', '', '', '']
                    logger.error(f"Exercise {i+1}: Failed to parse JSON options: {e}")
            else:
                logger.debug(f"Exercise {i+1}: Options already in correct format")
            
            # Ensure options is always a list
            if not isinstance(exercise.get('options'), list):
                exercise['options'] = ['', '', '', '']
                logger.warning(f"Exercise {i+1}: Options not a list, setting empty array")
            
            # Ensure correct_answer is integer
            if 'correct_answer' in exercise:
                try:
                    exercise['correct_answer'] = int(exercise['correct_answer'])
                    logger.debug(f"Exercise {i+1}: Set correct_answer to {exercise['correct_answer']}")
                except (ValueError, TypeError) as e:
                    exercise['correct_answer'] = 1
                    logger.error(f"Exercise {i+1}: Invalid correct_answer type: {e}")
            
            processed_exercises.append(exercise)
        
        logger.info(f"Processed {len(processed_exercises)} exercises for template")
        logger.debug(f"Sample exercise data for template: {processed_exercises[0] if processed_exercises else 'None'}")
        
        return render_template('admin/exercises.html', exercises=processed_exercises)
    except Exception as e:
        logger.error(f"Admin exercises error: {e}", exc_info=True)
        # Don't flash error to user, just return empty exercises list
        return render_template('admin/exercises.html', exercises=[])

# API Endpoints for Bot

@app.route('/api/test', methods=['GET'])
def api_test():
    """Test endpoint for bot connectivity verification"""
    try:
        return jsonify({
            'status': 'ok',
            'message': 'API is working correctly',
            'timestamp': datetime.now().isoformat(),
            'service': 'pythontutor-web',
            'database_connected': supabase is not None
        }), 200
    except Exception as e:
        logger.error(f"API test error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'API test failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/user/<int:telegram_id>', methods=['GET'])
def get_user(telegram_id):
    """Get user by telegram_id for bot"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        
        if response.data:
            return jsonify(response.data[0]), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"API get user error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user', methods=['POST'])
def create_user():
    """Create new user for bot with enhanced error handling"""
    try:
        if not supabase:
            logger.error("Database not connected for user creation")
            return jsonify({'error': 'Database not connected', 'details': 'No se puede conectar a la base de datos'}), 500
        
        user_data = request.get_json()
        logger.info(f"Creating user with data: {user_data}")
        
        # Validate required fields
        required_fields = ['telegram_id', 'username', 'first_name']
        for field in required_fields:
            if field not in user_data:
                logger.error(f"Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}', 'details': f'El campo {field} es requerido'}), 400
        
        # Validate telegram_id is a positive integer
        try:
            telegram_id = int(user_data['telegram_id'])
            if telegram_id <= 0:
                raise ValueError("telegram_id must be positive")
        except (ValueError, TypeError):
            logger.error(f"Invalid telegram_id: {user_data['telegram_id']}")
            return jsonify({'error': 'Invalid telegram_id', 'details': 'El ID de Telegram debe ser un número positivo'}), 400
        
        # Check if user already exists
        try:
            existing_user = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            if existing_user.data:
                logger.info(f"User {telegram_id} already exists")
                return jsonify(existing_user.data[0]), 200
        except Exception as e:
            logger.error(f"Error checking existing user: {e}")
            return jsonify({'error': 'Database error', 'details': 'Error al verificar usuario existente'}), 500
        
        # Create new user with proper timestamp handling
        try:
            user_record = {
                'telegram_id': telegram_id,
                'username': user_data.get('username', '')[:255],  # Limit length
                'first_name': user_data.get('first_name', '')[:255],
                'last_name': user_data.get('last_name', '')[:255],
                'current_level': user_data.get('current_level', 'principiante'),
                'level_progress': max(0, min(100, user_data.get('level_progress', 0))),  # Validate range
                'total_exercises_completed': max(0, user_data.get('total_exercises_completed', 0)),
                'current_streak': max(0, user_data.get('current_streak', 0)),
                'longest_streak': max(0, user_data.get('longest_streak', 0)),
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            
            response = supabase.table('users').insert(user_record).execute()
            
            if response.data:
                logger.info(f"Successfully created user {telegram_id}")
                return jsonify(response.data[0]), 201
            else:
                logger.error(f"Failed to create user: No data returned")
                return jsonify({'error': 'Failed to create user', 'details': 'No se pudo crear el usuario'}), 500
                
        except Exception as e:
            logger.error(f"Error creating user record: {e}")
            return jsonify({'error': 'Database error', 'details': f'Error al crear registro: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in create_user: {e}")
        return jsonify({'error': 'Internal server error', 'details': f'Error interno: {str(e)}'}), 500

@app.route('/api/exercises/<level>', methods=['GET'])
def get_exercises(level):
    """Get exercises by level for bot"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Validate level
        valid_levels = ['principiante', 'intermedio', 'avanzado', 'experto']
        if level not in valid_levels:
            return jsonify({'error': 'Invalid level'}), 400
        
        response = supabase.table('exercises').select('*').eq('level', level).execute()
        
        if response.data:
            # Process exercises for bot
            exercises = []
            for ex in response.data:
                # Parse options if stored as string
                if isinstance(ex.get('options'), str):
                    try:
                        ex['options'] = json.loads(ex['options'])
                    except:
                        ex['options'] = ['', '', '', '']
                exercises.append(ex)
            return jsonify(exercises), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        logger.error(f"API get exercises error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/progress', methods=['POST'])
def update_progress():
    """Update user progress for bot"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        progress_data = request.get_json()
        
        # Validate required fields
        required_fields = ['telegram_id', 'exercise_id', 'completed']
        for field in required_fields:
            if field not in progress_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get current user
        user_response = supabase.table('users').select('*').eq('telegram_id', progress_data['telegram_id']).execute()
        if not user_response.data:
            return jsonify({'error': 'User not found'}), 404
        
        user = user_response.data[0]
        
        # Update user progress
        if progress_data['completed']:
            new_progress = user.get('level_progress', 0) + 1
            new_total = user.get('total_exercises_completed', 0) + 1
        else:
            new_progress = user.get('level_progress', 0)
            new_total = user.get('total_exercises_completed', 0)
        
        response = supabase.table('users').update({
            'level_progress': new_progress,
            'total_exercises_completed': new_total,
            'last_activity': 'now()'
        }).eq('telegram_id', progress_data['telegram_id']).execute()
        
        if response.data:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to update progress'}), 500
            
    except Exception as e:
        logger.error(f"API update progress error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/progress/<int:telegram_id>/<level>', methods=['GET'])
def get_level_progress(telegram_id, level):
    """Get user progress for specific level for bot"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get user
        user_response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        if not user_response.data:
            return jsonify({'completed_count': 0, 'total_count': 300}), 200
        
        user = user_response.data[0]
        
        # Get completed exercises for this level
        completed_count = user.get('level_progress', 0) if user.get('current_level') == level else 0
        
        return jsonify({
            'completed_count': completed_count,
            'total_count': 300
        }), 200
            
    except Exception as e:
        logger.error(f"API get level progress error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/stats/<int:telegram_id>', methods=['GET'])
def get_user_stats(telegram_id):
    """Get user statistics for bot"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get user
        user_response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        if not user_response.data:
            return jsonify({
                'current_streak': 0,
                'total_completed': 0
            }), 200
        
        user = user_response.data[0]
        
        return jsonify({
            'current_streak': 1,  # Simplified - would calculate from activity
            'total_completed': user.get('total_exercises_completed', 0)
        }), 200
            
    except Exception as e:
        logger.error(f"API get user stats error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/notify-bot-changes', methods=['POST'])
def notify_bot_changes():
    """Notify bot that exercises have changed"""
    try:
        # Aquí podrías agregar lógica para notificar al bot
        # Por ahora, solo registramos la notificación
        logger.info("Bot notified of exercise changes")
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error notifying bot: {e}")
        return jsonify({'error': str(e)}), 500

# API Endpoints for Exercises Management
@app.route('/api/admin/exercises', methods=['GET'])
@admin_required
def api_get_exercises():
    """Get all exercises - MEJORADO"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        level = request.args.get('level')
        search = request.args.get('search')
        
        query = supabase.table('exercises').select('*')
        
        if level and level != 'todos':
            query = query.eq('level', level)
        
        if search:
            query = query.ilike('question', f'%{search}%')
        
        response = query.order('created_at', desc=True).execute()
        exercises = response.data or []
        
        logger.info(f"📊 Retrieved {len(exercises)} exercises from database")
        
        # Process options for each exercise
        for exercise in exercises:
            if isinstance(exercise.get('options'), str):
                try:
                    exercise['options'] = json.loads(exercise['options'])
                except:
                    exercise['options'] = ['', '', '', '']
        
        logger.info(f"📊 Returning {len(exercises)} exercises to frontend")
        return jsonify(exercises)
    except Exception as e:
        logger.error(f"API get exercises error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/exercises', methods=['POST'])
@admin_required
def api_create_exercise():
    """Create new exercise - MEJORADO"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        
        # Validate required fields
        required_fields = ['question', 'level', 'options', 'correct_answer']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate options
        if not isinstance(data['options'], list) or len(data['options']) != 4:
            return jsonify({'error': 'Options must be an array with 4 items'}), 400
        
        # Validate correct_answer
        try:
            correct_answer = int(data['correct_answer'])
            if correct_answer < 1 or correct_answer > 4:
                return jsonify({'error': 'correct_answer must be between 1 and 4'}), 400
        except:
            return jsonify({'error': 'correct_answer must be an integer'}), 400
        
        # Create exercise
        exercise_data = {
            'question': data['question'].strip(),
            'level': data['level'],
            'options': json.dumps(data['options']),  # Store as JSON string
            'correct_answer': correct_answer,
            'explanation': data.get('explanation', '').strip(),
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('exercises').insert(exercise_data).execute()
        
        if response.data:
            # Parse options back for response
            new_exercise = response.data[0]
            if isinstance(new_exercise.get('options'), str):
                try:
                    new_exercise['options'] = json.loads(new_exercise['options'])
                except:
                    new_exercise['options'] = ['', '', '', '']
            return jsonify(new_exercise), 201
        else:
            return jsonify({'error': 'Failed to create exercise'}), 400
    except Exception as e:
        logger.error(f"API create exercise error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/admin/exercises/<int:exercise_id>', methods=['PUT'])
@admin_required
def api_update_exercise(exercise_id):
    """Update exercise - MEJORADO"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        
        # Validate required fields
        if 'question' not in data or 'level' not in data or 'options' not in data or 'correct_answer' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate options
        if not isinstance(data['options'], list) or len(data['options']) != 4:
            return jsonify({'error': 'Options must be an array with 4 items'}), 400
        
        # Validate correct_answer
        try:
            correct_answer = int(data['correct_answer'])
            if correct_answer < 1 or correct_answer > 4:
                return jsonify({'error': 'correct_answer must be between 1 and 4'}), 400
        except:
            return jsonify({'error': 'correct_answer must be an integer'}), 400
        
        # Update exercise
        update_data = {
            'question': data['question'].strip(),
            'level': data['level'],
            'options': json.dumps(data['options']),  # Store as JSON string
            'correct_answer': correct_answer,
            'explanation': data.get('explanation', '').strip(),
            'updated_at': datetime.now().isoformat()
        }
        
        response = supabase.table('exercises').update(update_data).eq('id', exercise_id).execute()
        
        if response.data:
            # Parse options back for response
            updated_exercise = response.data[0]
            if isinstance(updated_exercise.get('options'), str):
                try:
                    updated_exercise['options'] = json.loads(updated_exercise['options'])
                except:
                    updated_exercise['options'] = ['', '', '', '']
            return jsonify(updated_exercise)
        else:
            return jsonify({'error': 'Exercise not found'}), 404
    except Exception as e:
        logger.error(f"API update exercise error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/admin/exercises/<int:exercise_id>', methods=['DELETE'])
@admin_required
def api_delete_exercise(exercise_id):
    """Delete exercise - MEJORADO"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Check if exercise exists
        check_response = supabase.table('exercises').select('id').eq('id', exercise_id).execute()
        if not check_response.data:
            return jsonify({'error': 'Exercise not found'}), 404
        
        # Delete exercise
        response = supabase.table('exercises').delete().eq('id', exercise_id).execute()
        
        if response.data:
            logger.info(f"Exercise {exercise_id} deleted by admin {current_user.username}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete exercise'}), 500
    except Exception as e:
        logger.error(f"API delete exercise error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/admin/exercises/import/test', methods=['POST'])
@admin_required_api
def api_test_import_exercises():
    """Endpoint de diagnóstico para probar importación con datos de prueba"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Datos de prueba basados en tu JSON
        test_exercises = [
            {
                "level": "principiante",
                "question": "¿Qué devuelve el siguiente código?\n\nnumero = \"18\"\nresultado = int(numero)",
                "options": [
                    "18",
                    "17",
                    "19",
                    "36"
                ],
                "correct_answer": 1,
                "explanation": "int() convierte el string \"18\" al número entero 18"
            },
            {
                "level": "principiante",
                "question": "¿Qué valor tendrá \"resultado\" después de ejecutar este código?\n\nresultado = []\nfor i in range(8):\n    resultado.append(i * 2)",
                "options": [
                    "[0, 2, 4, 6, 8, 10, 12, 14]",
                    "KeyError",
                    "None",
                    "1"
                ],
                "correct_answer": 1,
                "explanation": "Lista de números pares desde 0 hasta 14"
            },
            {
                "level": "principiante",
                "question": "¿Qué valor tendrá la variable \"resultado\" después de ejecutar este código?\n\na = 31\nb = 30\nresultado = a >= b",
                "options": [
                    "True",
                    "Opción 4",
                    "False",
                    "Opción 3"
                ],
                "correct_answer": 1,
                "explanation": "La operación a >= b resulta en True"
            }
        ]
        
        logger.info(f"Starting test import with {len(test_exercises)} exercises")
        
        # Probar cada paso del proceso
        diagnostic_results = []
        
        for index, exercise in enumerate(test_exercises):
            result = {
                'exercise_index': index + 1,
                'original_data': exercise,
                'steps': []
            }
            
            try:
                # Paso 1: Normalización
                result['steps'].append({
                    'step': 'normalization',
                    'status': 'starting',
                    'message': f'Processing: {exercise.get("question", "")[:50]}...'
                })
                
                normalized_exercise = normalize_exercise_data(exercise)
                
                result['steps'].append({
                    'step': 'normalization',
                    'status': 'completed',
                    'normalized_data': normalized_exercise,
                    'message': f'Normalized: level={normalized_exercise["level"]}, correct_answer={normalized_exercise["correct_answer"]}'
                })
                
                # Paso 2: Validación
                result['steps'].append({
                    'step': 'validation',
                    'status': 'starting',
                    'message': 'Validating structure...'
                })
                
                validation_result = validate_exercise_structure(normalized_exercise)
                
                result['steps'].append({
                    'step': 'validation',
                    'status': 'completed' if validation_result['valid'] else 'failed',
                    'validation_result': validation_result,
                    'message': f'Validation: {"PASSED" if validation_result["valid"] else "FAILED"} - {validation_result.get("error", "")}'
                })
                
                if not validation_result['valid']:
                    result['final_status'] = 'failed'
                    result['error'] = validation_result['error']
                    diagnostic_results.append(result)
                    continue
                
                # Paso 3: Detección de duplicados
                result['steps'].append({
                    'step': 'duplicate_check',
                    'status': 'starting',
                    'message': 'Checking for duplicates...'
                })
                
                is_duplicate = is_duplicate_exercise(normalized_exercise['question'])
                
                result['steps'].append({
                    'step': 'duplicate_check',
                    'status': 'completed',
                    'is_duplicate': is_duplicate,
                    'message': f'Duplicate check: {"DUPLICATE" if is_duplicate else "UNIQUE"}'
                })
                
                if is_duplicate:
                    result['final_status'] = 'skipped'
                    result['error'] = 'Duplicate exercise'
                    diagnostic_results.append(result)
                    continue
                
                # Paso 4: Inserción (solo si no es modo dry-run)
                dry_run = request.json.get('dry_run', True) if request.json else True
                
                if not dry_run:
                    result['steps'].append({
                        'step': 'insertion',
                        'status': 'starting',
                        'message': 'Inserting into database...'
                    })
                    
                    exercise_data = {
                        'question': normalized_exercise['question'],
                        'level': normalized_exercise['level'],
                        'options': json.dumps(normalized_exercise['options']),
                        'correct_answer': normalized_exercise['correct_answer'],
                        'explanation': normalized_exercise.get('explanation', ''),
                        'created_at': datetime.now().isoformat()
                    }
                    
                    insert_result = supabase.table('exercises').insert(exercise_data).execute()
                    
                    if insert_result.data:
                        result['steps'].append({
                            'step': 'insertion',
                            'status': 'completed',
                            'inserted_id': insert_result.data[0].get('id'),
                            'message': f'Successfully inserted with ID {insert_result.data[0].get("id")}'
                        })
                        result['final_status'] = 'success'
                    else:
                        result['steps'].append({
                            'step': 'insertion',
                            'status': 'failed',
                            'message': 'Database insertion failed - no data returned'
                        })
                        result['final_status'] = 'failed'
                        result['error'] = 'Database insertion failed'
                else:
                    result['steps'].append({
                        'step': 'insertion',
                        'status': 'skipped',
                        'message': 'Dry run mode - insertion skipped'
                    })
                    result['final_status'] = 'dry_run_success'
                
            except Exception as e:
                result['final_status'] = 'error'
                result['error'] = str(e)
                result['steps'].append({
                    'step': 'error',
                    'status': 'error',
                    'message': f'Exception: {str(e)}'
                })
                logger.error(f"Test import error for exercise {index + 1}: {e}", exc_info=True)
            
            diagnostic_results.append(result)
        
        # Resumen de resultados
        summary = {
            'total': len(test_exercises),
            'success': len([r for r in diagnostic_results if r.get('final_status') == 'success']),
            'dry_run_success': len([r for r in diagnostic_results if r.get('final_status') == 'dry_run_success']),
            'failed': len([r for r in diagnostic_results if r.get('final_status') == 'failed']),
            'skipped': len([r for r in diagnostic_results if r.get('final_status') == 'skipped']),
            'error': len([r for r in diagnostic_results if r.get('final_status') == 'error'])
        }
        
        logger.info(f"Test import completed: {summary}")
        
        return jsonify({
            'mode': 'dry_run' if (request.json.get('dry_run', True) if request.json else True) else 'live',
            'summary': summary,
            'diagnostic_results': diagnostic_results
        })
        
    except Exception as e:
        logger.error(f"Test import endpoint error: {e}", exc_info=True)
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

@app.route('/api/admin/exercises/import/simple', methods=['POST'])
@admin_required
def api_simple_import_test():
    """Simple import test with minimal data"""
    try:
        logger.info("=== SIMPLE IMPORT TEST START ===")
        
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Datos de prueba simples
        test_exercise = {
            'question': 'Test question - ¿Cuánto es 2+2?',
            'level': 'principiante',
            'options': ['3', '4', '5', '6'],
            'correct_answer': 2,
            'explanation': '2+2=4'
        }
        
        logger.info(f"Inserting test exercise: {test_exercise['question']}")
        
        # Insertar directamente
        result = supabase.table('exercises').insert({
            'question': test_exercise['question'],
            'level': test_exercise['level'],
            'options': json.dumps(test_exercise['options']),
            'correct_answer': test_exercise['correct_answer'],
            'explanation': test_exercise['explanation'],
            'created_at': datetime.now().isoformat()
        }).execute()
        
        if result.data:
            exercise_id = result.data[0].get('id')
            logger.info(f"✅ Simple test successful: Exercise ID {exercise_id}")
            return jsonify({
                'success': True,
                'imported': 1,
                'exercise_id': exercise_id,
                'message': 'Test exercise inserted successfully'
            })
        else:
            logger.error("❌ Simple test failed: No data returned")
            return jsonify({'error': 'No data returned from insert'}), 500
            
    except Exception as e:
        logger.error(f"Simple test error: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__,
            'message': 'Simple test failed'
        }), 500

@app.route('/api/admin/exercises/import', methods=['POST'])
@admin_required_api
def api_import_exercises():
    """Import exercises from JSON - MEJORADO PARA 300+ EJERCICIOS"""
    import traceback
    
    # EARLY DEBUG LOGGING - This should execute even if everything else fails
    logger.info("=== IMPORT START ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request content type: {request.content_type}")
    logger.info(f"Request content length: {request.content_length}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"User: {getattr(current_user, 'username', 'unknown')}")
    logger.info(f"User authenticated: {current_user.is_authenticated}")
    
    try:
        logger.info("Starting import function...")
        
        if not supabase:
            logger.error("Import failed: Supabase not connected")
            return jsonify({'error': 'Database connection error'}), 500
        
        # Obtener datos del request con metadata
        try:
            logger.info("Attempting to parse JSON from request...")
            logger.info(f"Request stream length: {len(request.get_data()) if request.get_data() else 'No data'}")
            
            data = request.json
            if not data:
                logger.error("No JSON data in request")
                return jsonify({'error': 'No JSON data provided'}), 400
                
            logger.info(f"JSON parsed successfully. Data keys: {list(data.keys())}")
            
            exercises = data.get('exercises', [])
            metadata = data.get('metadata', {})
            
            logger.info(f"Import request received: {len(exercises)} exercises, metadata: {metadata}")
            
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            logger.error(f"Request body preview: {request.get_data()[:500] if request.get_data() else 'No body'}")
            return jsonify({'error': f'Invalid JSON: {str(json_error)}'}), 400
        
        if not isinstance(exercises, list):
            logger.error(f"Import failed: exercises is not a list, got {type(exercises)}")
            return jsonify({'error': 'Exercises must be an array'}), 400
        
        # Validar límite de ejercicios (reducido para testing)
        if len(exercises) > 500:
            logger.error(f"Import failed: Too many exercises ({len(exercises)} > 500)")
            return jsonify({'error': f'Too many exercises. Maximum allowed: 500 (got {len(exercises)})'}), 400
        
        if len(exercises) == 0:
            logger.warning("Import failed: No exercises provided")
            return jsonify({'error': 'No exercises provided'}), 400
        
        logger.info(f"Starting import process: {len(exercises)} exercises to process")
        
        # Validar primeros 5 ejercicios para detectar problemas temprano
        logger.info("Validating first 5 exercises...")
        for i, exercise in enumerate(exercises[:5]):
            try:
                required_fields = ['question', 'level', 'options', 'correct_answer']
                missing_fields = [field for field in required_fields if field not in exercise]
                if missing_fields:
                    error_msg = f"Exercise {i+1} missing required fields: {missing_fields}"
                    logger.error(error_msg)
                    return jsonify({'error': error_msg, 'exercise_index': i}), 400
                    
                # Validar nivel
                valid_levels = ['principiante', 'intermedio', 'avanzado', 'experto']
                if exercise['level'] not in valid_levels:
                    error_msg = f"Exercise {i+1} has invalid level: {exercise['level']}"
                    logger.error(error_msg)
                    return jsonify({'error': error_msg, 'exercise_index': i}), 400
                    
                # Validar opciones
                if not isinstance(exercise['options'], list) or len(exercise['options']) != 4:
                    error_msg = f"Exercise {i+1} must have exactly 4 options"
                    logger.error(error_msg)
                    return jsonify({'error': error_msg, 'exercise_index': i}), 400
                    
            except Exception as validation_error:
                error_msg = f"Exercise {i+1} validation error: {str(validation_error)}"
                logger.error(error_msg)
                return jsonify({'error': error_msg, 'exercise_index': i}), 400
        
        logger.info("✅ First 5 exercises validation passed")
        
        # Preparar contadores
        imported_count = 0
        errors = []
        skipped_duplicates = 0
        validation_errors = 0
        batch_errors = 0
        
        # Procesar en lotes más pequeños para mejor rendimiento
        batch_size = 25  # Reducido de 50 a 25
        total_batches = (len(exercises) + batch_size - 1) // batch_size
        
        logger.info(f"Processing in {total_batches} batches of {batch_size} exercises each")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(exercises))
            batch_exercises = exercises[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches}: exercises {start_idx + 1}-{end_idx}")
            
            # Preparar ejercicios del lote
            batch_data = []
            batch_duplicate_questions = set()
            
            for i, exercise in enumerate(batch_exercises):
                exercise_index = start_idx + i + 1
                
                try:
                    logger.debug(f"Processing exercise {exercise_index}: {exercise.get('question', 'NO QUESTION')[:50]}...")
                    
                    # Normalize exercise data
                    normalized_exercise = normalize_exercise_data(exercise)
                    logger.debug(f"Normalized exercise {exercise_index}: level={normalized_exercise['level']}, correct_answer={normalized_exercise['correct_answer']}")
                    
                    # Validate structure
                    validation_result = validate_exercise_structure(normalized_exercise)
                    if not validation_result['valid']:
                        error_msg = f"Ejercicio {exercise_index}: {validation_result['error']}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        validation_errors += 1
                        continue
                    
                    # Check for duplicates en este lote
                    question = normalized_exercise['question'].strip().lower()
                    if question in batch_duplicate_questions:
                        error_msg = f"Ejercicio {exercise_index}: Pregunta duplicada en el mismo lote - omitido"
                        logger.info(error_msg)
                        skipped_duplicates += 1
                        continue
                    
                    batch_duplicate_questions.add(question)
                    
                    # Check for duplicates en base de datos (temporarily disabled for testing)
                    if False and is_duplicate_exercise(normalized_exercise['question']):
                        error_msg = f"Ejercicio {exercise_index}: Pregunta duplicada en base de datos - omitido"
                        logger.info(error_msg)
                        skipped_duplicates += 1
                        continue
                    
                    # Preparar datos para inserción
                    created_time = datetime.now()
                    
                    exercise_data = {
                        'question': normalized_exercise['question'],
                        'level': normalized_exercise['level'],
                        'options': json.dumps(normalized_exercise['options']),
                        'correct_answer': normalized_exercise['correct_answer'],
                        'explanation': normalized_exercise.get('explanation', ''),
                        'created_at': created_time.isoformat()
                    }
                    
                    batch_data.append(exercise_data)
                    logger.debug(f"Prepared exercise {exercise_index} for insertion")
                    
                except Exception as e:
                    error_msg = f"Ejercicio {exercise_index}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    continue
            
            # Insertar lote en base de datos
            if batch_data:
                try:
                    logger.info(f"Inserting batch {batch_num + 1}: {len(batch_data)} exercises")
                    result = supabase.table('exercises').insert(batch_data).execute()
                    
                    if result.data:
                        batch_imported = len(result.data)
                        imported_count += batch_imported
                        logger.info(f"Batch {batch_num + 1} completed: {batch_imported} exercises imported")
                        
                        # Log IDs de ejercicios importados
                        imported_ids = [ex.get('id') for ex in result.data if ex.get('id')]
                        if imported_ids:
                            logger.debug(f"Imported IDs in batch {batch_num + 1}: {imported_ids}")
                    else:
                        error_msg = f"Lote {batch_num + 1}: Error al insertar en base de datos - no data returned"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        batch_errors += 1
                        
                except Exception as batch_error:
                    error_msg = f"Lote {batch_num + 1}: Error en inserción por lotes: {str(batch_error)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    batch_errors += 1
                    
                    # Intentar inserción individual si falla el lote
                    logger.warning(f"Batch {batch_num + 1} failed, trying individual insertions")
                    for j, exercise_data in enumerate(batch_data):
                        try:
                            individual_result = supabase.table('exercises').insert(exercise_data).execute()
                            if individual_result.data:
                                imported_count += 1
                                logger.debug(f"Individual insertion successful for exercise {start_idx + j + 1}")
                            else:
                                error_msg = f"Ejercicio {start_idx + j + 1}: Error en inserción individual"
                                errors.append(error_msg)
                        except Exception as individual_error:
                            error_msg = f"Ejercicio {start_idx + j + 1}: Error en inserción individual: {str(individual_error)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
            else:
                logger.info(f"Batch {batch_num + 1}: No valid exercises to insert")
        
        # Resumen final
        logger.info(f"Import completed: {imported_count} imported, {skipped_duplicates} duplicates skipped, {validation_errors} validation errors, {batch_errors} batch errors, {len(errors)} total errors out of {len(exercises)} total")
        
        # Preparar respuesta detallada
        response_data = {
            'imported': imported_count,
            'skipped_duplicates': skipped_duplicates,
            'validation_errors': validation_errors,
            'batch_errors': batch_errors,
            'total': len(exercises),
            'errors': errors[-10:] if len(errors) > 10 else errors,  # Últimos 10 errores
            'total_errors': len(errors),
            'metadata': metadata,
            'processing_stats': {
                'total_batches': total_batches,
                'batch_size': batch_size,
                'success_rate': round((imported_count / len(exercises)) * 100, 2) if exercises else 0
            }
        }
        
        # Log del resultado final
        if imported_count == len(exercises):
            logger.info("✅ All exercises imported successfully!")
        elif imported_count > 0:
            logger.warning(f"⚠️ Partial import: {imported_count}/{len(exercises)} exercises imported")
        else:
            logger.error("❌ No exercises imported successfully")
        
        return jsonify(response_data)
        
    except Exception as e:
        # Capturar CUALQUIER excepción para asegurar respuesta JSON
        error_type = type(e).__name__
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        
        logger.error(f"=== IMPORT ERROR ===")
        logger.error(f"Error type: {error_type}")
        logger.error(f"Error message: {error_msg}")
        logger.error(f"Traceback: {traceback_str}")
        logger.error(f"User: {getattr(current_user, 'username', 'unknown')}")
        logger.error("=== END ERROR ===")
        
        # SIEMPRE retornar JSON, nunca HTML
        error_response = {
            'error': error_msg,
            'error_type': error_type,
            'imported': 0,
            'skipped_duplicates': 0,
            'validation_errors': 0,
            'batch_errors': 1,
            'total': 0,
            'total_errors': 1,
            'errors': [f"Server error: {error_msg}"],
            'traceback': traceback_str if app.debug else None,
            'debug_info': {
                'user': getattr(current_user, 'username', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'endpoint': '/api/admin/exercises/import'
            }
        }
        
        # Asegurar respuesta JSON válida
        try:
            return jsonify(error_response), 500
        except Exception as json_error:
            # ULTIMO fallback - si incluso jsonify falla
            logger.error(f"CRITICAL: Even jsonify failed: {json_error}")
            return '{"error": "Critical server error", "error_type": "JsonifyError"}', 500, {'Content-Type': 'application/json'}

@app.route('/api/admin/exercises/export/json', methods=['GET'])
@admin_required
def api_export_exercises_json():
    """Export exercises as JSON - MEJORADO"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get all exercises
        response = supabase.table('exercises').select('*').order('created_at', desc=True).execute()
        exercises = response.data or []
        
        # Process exercises for export
        export_data = []
        for exercise in exercises:
            # Parse options if stored as string
            if isinstance(exercise.get('options'), str):
                try:
                    exercise['options'] = json.loads(exercise['options'])
                except:
                    exercise['options'] = ['', '', '', '']
            
            # Create clean export object
            export_data.append({
                'id': exercise.get('id'),
                'question': exercise.get('question'),
                'level': exercise.get('level'),
                'options': exercise.get('options'),
                'correct_answer': exercise.get('correct_answer'),
                'explanation': exercise.get('explanation', ''),
                'created_at': exercise.get('created_at')
            })
        
        # Create JSON response with download
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        response = Response(json_str, mimetype='application/json')
        response.headers['Content-Disposition'] = f'attachment; filename=ejercicios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting exercises to JSON: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/exercises/import/csv', methods=['POST'])
@admin_required
def api_import_exercises_csv():
    """Import exercises from CSV file"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        logger.info(f"CSV import started: {file.filename}")
        
        # Read and parse CSV
        exercises, csv_errors = parse_csv_exercises(file)
        
        if not exercises:
            return jsonify({
                'error': 'No valid exercises found in CSV',
                'errors': csv_errors,
                'imported': 0,
                'total': 0
            }), 400
        
        # Use existing import logic
        import_result = process_exercises_import(exercises)
        
        # Combine CSV errors with import errors
        all_errors = csv_errors + import_result.get('errors', [])
        
        return jsonify({
            'imported': import_result['imported'],
            'skipped_duplicates': import_result['skipped_duplicates'],
            'validation_errors': import_result['validation_errors'],
            'total_errors': import_result['total_errors'] + len(csv_errors),
            'errors': all_errors[-10:] if len(all_errors) > 10 else all_errors,
            'total': len(exercises),
            'csv_errors': csv_errors,
            'format': 'csv'
        })
        
    except Exception as e:
        logger.error(f"CSV import error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def parse_csv_exercises(csv_file):
    """Parse CSV file and extract exercises"""
    exercises = []
    errors = []
    
    try:
        # Read CSV content
        stream = StringIO(csv_file.read().decode('utf-8-sig'))  # Handle BOM
        reader = csv.DictReader(stream)
        
        # Validate headers
        required_headers = ['question', 'level', 'option1', 'option2', 'option3', 'option4', 'correct_answer']
        headers = reader.fieldnames or []
        
        missing_headers = [h for h in required_headers if h.lower() not in [f.lower() for f in headers]]
        if missing_headers:
            errors.append(f"Missing required columns: {', '.join(missing_headers)}")
            return exercises, errors
        
        logger.info(f"CSV headers validated: {headers}")
        
        # Process each row
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
            try:
                exercise = validate_and_normalize_csv_row(row, row_num)
                if exercise:
                    exercises.append(exercise)
            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        logger.info(f"CSV parsing completed: {len(exercises)} exercises, {len(errors)} errors")
        
    except Exception as e:
        error_msg = f"CSV parsing error: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
    
    return exercises, errors

def validate_and_normalize_csv_row(row, row_num):
    """Validate and normalize a single CSV row"""
    
    # Extract and validate required fields
    question = row.get('question', '').strip()
    level = row.get('level', '').strip().lower()
    
    if not question:
        raise ValueError("Question cannot be empty")
    
    valid_levels = ['principiante', 'intermedio', 'avanzado', 'experto']
    if not level or level not in valid_levels:
        raise ValueError(f"Invalid level: {level}. Valid levels: {', '.join(valid_levels)}")
    
    # Extract options (handle different column names)
    options = [
        row.get('option1', '').strip() or row.get('opcion1', '').strip() or row.get('a', '').strip(),
        row.get('option2', '').strip() or row.get('opcion2', '').strip() or row.get('b', '').strip(),
        row.get('option3', '').strip() or row.get('opcion3', '').strip() or row.get('c', '').strip(),
        row.get('option4', '').strip() or row.get('opcion4', '').strip() or row.get('d', '').strip()
    ]
    
    if any(not opt for opt in options):
        raise ValueError("All options must be provided")
    
    # Validate correct answer
    correct_answer_str = row.get('correct_answer', '').strip()
    try:
        correct_answer = int(correct_answer_str)
        if correct_answer < 1 or correct_answer > 4:
            raise ValueError("Correct answer must be between 1 and 4")
    except ValueError:
        raise ValueError(f"Invalid correct answer: {correct_answer_str}")
    
    # Get optional explanation
    explanation = row.get('explanation', '').strip() or row.get('explicacion', '').strip()
    
    return {
        'question': question,
        'level': level,
        'options': options,
        'correct_answer': correct_answer,
        'explanation': explanation,
        'created_at': datetime.now().isoformat()
    }

def process_exercises_import(exercises):
    """Process exercises import using existing logic"""
    try:
        # Use existing import logic but with our pre-validated exercises
        imported_count = 0
        errors = []
        skipped_duplicates = 0
        validation_errors = 0
        
        # Process in batches
        batch_size = 50
        total_batches = (len(exercises) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(exercises)} exercises in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(exercises))
            batch_exercises = exercises[start_idx:end_idx]
            
            # Normalize exercises for database
            batch_data = []
            for exercise in batch_exercises:
                try:
                    normalized = normalize_exercise_data(exercise)
                    if normalized:
                        batch_data.append(normalized)
                except Exception as e:
                    errors.append(f"Exercise normalization error: {str(e)}")
                    validation_errors += 1
            
            # Insert batch
            if batch_data:
                try:
                    result = supabase.table('exercises').insert(batch_data).execute()
                    if result.data:
                        batch_imported = len(result.data)
                        imported_count += batch_imported
                        logger.info(f"Batch {batch_num + 1}: {batch_imported} exercises imported")
                    else:
                        errors.append(f"Batch {batch_num + 1}: No data returned from insert")
                except Exception as e:
                    errors.append(f"Batch {batch_num + 1} insert error: {str(e)}")
        
        return {
            'imported': imported_count,
            'skipped_duplicates': skipped_duplicates,
            'validation_errors': validation_errors,
            'total_errors': len(errors),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Process import error: {e}")
        return {
            'imported': 0,
            'skipped_duplicates': 0,
            'validation_errors': 0,
            'total_errors': 1,
            'errors': [str(e)]
        }

@app.route('/api/admin/exercises/export/csv', methods=['GET'])
@admin_required
def api_export_exercises_csv():
    """Export exercises as CSV - MEJORADO"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get all exercises
        response = supabase.table('exercises').select('*').order('created_at', desc=True).execute()
        exercises = response.data or []
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Nivel', 'Pregunta', 'Opción 1', 'Opción 2', 'Opción 3', 'Opción 4', 'Respuesta Correcta', 'Explicación'])
        
        # Write data
        for exercise in exercises:
            # Parse options
            options = exercise.get('options', '["","","",""]')
            if isinstance(options, str):
                try:
                    options = json.loads(options)
                except:
                    options = ['', '', '', '']
            
            # Ensure options is a list
            if not isinstance(options, list):
                options = ['', '', '', '']
            
            # Pad options to 4 items
            while len(options) < 4:
                options.append('')
            
            writer.writerow([
                exercise.get('id', ''),
                exercise.get('level', ''),
                exercise.get('question', ''),
                options[0] if len(options) > 0 else '',
                options[1] if len(options) > 1 else '',
                options[2] if len(options) > 2 else '',
                options[3] if len(options) > 3 else '',
                exercise.get('correct_answer', 1),
                exercise.get('explanation', '')
            ])
        
        # Prepare response
        output.seek(0)
        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=ejercicios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting exercises to CSV: {e}")
        return jsonify({'error': str(e)}), 500

def normalize_exercise_data(exercise):
    """Normaliza los datos del ejercicio al formato esperado"""
    normalized = {}
    
    # Mapear level/difficulty
    if 'level' in exercise:
        normalized['level'] = exercise['level']
    elif 'difficulty' in exercise:
        normalized['level'] = map_difficulty_to_level(exercise['difficulty'])
    else:
        normalized['level'] = 'principiante'  # Default
    
    # Copiar campos directos
    normalized['question'] = exercise.get('question', '').strip()
    normalized['explanation'] = exercise.get('explanation', '').strip()
    
    # Procesar opciones
    options = exercise.get('options', [])
    if isinstance(options, list) and len(options) >= 4:
        normalized['options'] = options[:4]  # Tomar solo las primeras 4
    else:
        # Generar opciones si no existen
        answer = exercise.get('answer', '1')
        normalized['options'] = generate_fallback_options(answer)
    
    # Procesar correct_answer - CRITICAL FIX
    correct_answer = exercise.get('correct_answer')
    
    # Si correct_answer es string numérico, convertir a int
    if isinstance(correct_answer, str) and correct_answer.isdigit():
        correct_answer = int(correct_answer)
    
    # Si no es int, intentar obtener del campo 'answer'
    elif not isinstance(correct_answer, int):
        answer = exercise.get('answer', str(normalized['options'][0]))
        correct_answer = find_correct_answer_index(normalized['options'], answer)
    
    # Asegurar que correct_answer esté en rango válido (1-4 para base-1)
    if isinstance(correct_answer, int):
        if correct_answer < 1 or correct_answer > 4:
            logger.warning(f"correct_answer {correct_answer} out of range [1-4], defaulting to 1")
            correct_answer = 1
    else:
        logger.warning(f"Invalid correct_answer type: {type(correct_answer)}, defaulting to 1")
        correct_answer = 1
    
    normalized['correct_answer'] = correct_answer
    
    logger.debug(f"Normalized exercise: question='{normalized['question'][:30]}...', level={normalized['level']}, correct_answer={normalized['correct_answer']}, options_count={len(normalized['options'])}")
    
    return normalized

def map_difficulty_to_level(difficulty):
    """Convierte difficulty numérico a level string"""
    if isinstance(difficulty, str):
        if difficulty.isdigit():
            difficulty = int(difficulty)
        else:
            return difficulty.lower()  # Asumir que ya es un level
    
    level_mapping = {
        1: 'principiante',
        2: 'intermedio', 
        3: 'avanzado',
        4: 'experto'
    }
    return level_mapping.get(difficulty, 'principiante')

def validate_exercise_structure(exercise):
    """Valida la estructura del ejercicio"""
    required_fields = ['question', 'level', 'options', 'correct_answer']
    
    # Verificar campos requeridos
    for field in required_fields:
        if field not in exercise or not exercise[field]:
            return {'valid': False, 'error': f'Campo requerido faltante: {field}'}
    
    # Validar level
    valid_levels = ['principiante', 'intermedio', 'avanzado', 'experto']
    if exercise['level'] not in valid_levels:
        return {'valid': False, 'error': f'Level inválido: {exercise["level"]}'}
    
    # Validar opciones
    if not isinstance(exercise['options'], list) or len(exercise['options']) != 4:
        return {'valid': False, 'error': 'Debe tener exactamente 4 opciones'}
    
    # Validar que las opciones no estén vacías (más flexible)
    for i, option in enumerate(exercise['options']):
        if not option or str(option).strip() == '':
            return {'valid': False, 'error': f'Opción {i+1} está vacía'}
        
        # Validar que la opción tenga longitud mínima razonable
        if len(str(option).strip()) < 1:
            return {'valid': False, 'error': f'Opción {i+1} es demasiado corta'}
    
    # Validar correct_answer (base-1 index)
    if not isinstance(exercise['correct_answer'], int) or not (1 <= exercise['correct_answer'] <= 4):
        return {'valid': False, 'error': 'correct_answer debe ser un número entre 1 y 4'}
    
    # Validar longitud de la pregunta
    if len(exercise['question'].strip()) < 5:
        return {'valid': False, 'error': 'La pregunta es demasiado corta (mínimo 5 caracteres)'}
    
    # Validar que la respuesta correcta corresponda a una opción existente
    correct_index = exercise['correct_answer'] - 1  # Convertir a base-0
    if correct_index >= len(exercise['options']):
        return {'valid': False, 'error': f'correct_answer {exercise["correct_answer"]} no corresponde a ninguna opción'}
    
    # Validar que la opción correcta no esté vacía
    if not exercise['options'][correct_index] or str(exercise['options'][correct_index]).strip() == '':
        return {'valid': False, 'error': f'La opción correcta ({exercise["correct_answer"]}) está vacía'}
    
    return {'valid': True, 'error': None}

def is_duplicate_exercise(question):
    """Verifica si ya existe un ejercicio con la misma pregunta"""
    try:
        if not supabase:
            logger.warning("Cannot check duplicates: Supabase not connected")
            return False
        
        # Limpiar y normalizar la pregunta para comparación
        normalized_question = question.strip().lower()
        
        # Buscar coincidencias exactas primero (case-insensitive)
        result = supabase.table('exercises').select('id', 'question').ilike('question', question.strip()).execute()
        
        if result.data and len(result.data) > 0:
            # Verificación adicional para evitar falsos positivos
            for existing_exercise in result.data:
                existing_question = existing_exercise.get('question', '').strip().lower()
                # Comparación más estricta: eliminar espacios extras y normalizar
                if normalized_question == existing_question:
                    logger.info(f"Duplicate found: '{question[:30]}...' matches existing exercise ID {existing_exercise.get('id')}")
                    return True
                # Comparación de similitud (opcional, para casos muy similares)
                elif calculate_similarity(normalized_question, existing_question) > 0.9:
                    logger.info(f"Near duplicate found: '{question[:30]}...' is very similar to existing exercise ID {existing_exercise.get('id')}")
                    return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return False  # En caso de error, permitir la inserción

def calculate_similarity(str1, str2):
    """Calcula la similitud entre dos strings (implementación simple)"""
    try:
        # Implementación simple de similitud de Jaccard
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    except:
        return 0.0

def generate_fallback_options(answer):
    """Genera opciones de respaldo cuando no se proporcionan"""
    answer_str = str(answer)
    options = [answer_str]
    
    # Generar 3 opciones incorrectas
    incorrect_options = ['0', '1', 'Error', 'None', 'True', 'False', 'SyntaxError']
    
    while len(options) < 4:
        opt = random.choice(incorrect_options)
        if opt not in options:
            options.append(opt)
    
    random.shuffle(options)
    return options

def find_correct_answer_index(options, answer):
    """Encuentra el índice de la respuesta correcta"""
    answer_str = str(answer).strip().lower()
    
    for i, option in enumerate(options):
        if str(option).strip().lower() == answer_str:
            return i + 1  # Índice base 1
    
    return 1  # Default a primera opción

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin users management page"""
    try:
        if not supabase:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('admin/users.html', users=[], stats={})
        
        # Get user statistics
        try:
            total_users_response = supabase.table('users').select('*', count='exact').execute()
            active_users_response = supabase.table('users').select('*', count='exact').eq('is_active', True).execute()
            
            # Get recent users (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_response = supabase.table('users').select('*', count='exact').gte('created_at', week_ago).execute()
            
            stats = {
                'total': total_users_response.count if hasattr(total_users_response, 'count') else 0,
                'active': active_users_response.count if hasattr(active_users_response, 'count') else 0,
                'inactive': (total_users_response.count if hasattr(total_users_response, 'count') else 0) - 
                            (active_users_response.count if hasattr(active_users_response, 'count') else 0),
                'recent': recent_response.count if hasattr(recent_response, 'count') else 0
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            stats = {'total': 0, 'active': 0, 'inactive': 0, 'recent': 0}
        
        # Get recent users (last 50)
        try:
            users_response = supabase.table('users').select('*').order('created_at', desc=True).limit(50).execute()
            users = users_response.data or []
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            users = []
        
        return render_template('admin/users.html', users=users, stats=stats)
    except Exception as e:
        logger.error(f"Admin users error: {e}")
        flash('Error al cargar la página de usuarios', 'danger')
        return render_template('admin/users.html', users=[], stats={})

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_get_users():
    """Get all users with filters"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get query parameters
        search = request.args.get('search', '')
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Build query
        query = supabase.table('users').select('*', count='exact')
        
        # Apply filters
        if search:
            query = query.or_(f"username.ilike.%{search}%,first_name.ilike.%{search}%,last_name.ilike.%{search}%")
        
        if status == 'active':
            query = query.eq('is_active', True)
        elif status == 'inactive':
            query = query.eq('is_active', False)
        
        # Get total count
        count_response = query.execute()
        total = count_response.count if hasattr(count_response, 'count') else 0
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.order('created_at', desc=True).range(offset, offset + per_page - 1)
        
        response = query.execute()
        users = response.data or []
        
        return jsonify({
            'users': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if total > 0 else 1
            }
        })
    except Exception as e:
        logger.error(f"API get users error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def api_update_user(user_id):
    """Update user status (activate/deactivate)"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        is_active = data.get('is_active')
        
        if is_active is None:
            return jsonify({'error': 'Missing is_active field'}), 400
        
        # Update user
        response = supabase.table('users').update({
            'is_active': is_active,
            'updated_at': 'now()'
        }).eq('id', user_id).execute()
        
        if response.data:
            action = 'activado' if is_active else 'desactivado'
            logger.info(f"User {user_id} {action} by admin {current_user.username}")
            return jsonify(response.data[0])
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"API update user error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id):
    """Delete user"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get user info for logging
        user_response = supabase.table('users').select('username, telegram_id').eq('id', user_id).execute()
        
        # Delete user
        response = supabase.table('users').delete().eq('id', user_id).execute()
        
        if response.data:
            user_info = user_response.data[0] if user_response.data else {}
            logger.info(f"User {user_id} ({user_info.get('username', 'Unknown')}) deleted by admin {current_user.username}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"API delete user error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/admin/users/stats', methods=['GET'])
@admin_required
def api_get_user_stats():
    """Get user statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get basic stats
        total_response = supabase.table('users').select('*', count='exact').execute()
        active_response = supabase.table('users').select('*', count='exact').eq('is_active', True).execute()
        
        # Get recent users (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_response = supabase.table('users').select('*', count='exact').gte('created_at', week_ago).execute()
        
        stats = {
            'total': total_response.count if hasattr(total_response, 'count') else 0,
            'active': active_response.count if hasattr(active_response, 'count') else 0,
            'inactive': (total_response.count if hasattr(total_response, 'count') else 0) - 
                        (active_response.count if hasattr(active_response, 'count') else 0),
            'recent': recent_response.count if hasattr(recent_response, 'count') else 0
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"API get user stats error: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def change_password():
    """Change admin user password"""
    if not supabase:
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        return render_template('admin/change_password.html')
    
    # Logging detallado para debugging
    logger.info(f"Change password attempt for user: {current_user}")
    
    # Verificar que el ID de usuario sea válido
    try:
        user_id = int(current_user.id)
        logger.info(f"Valid user ID: {user_id}")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID: {current_user.id} (type: {type(current_user.id)})")
        flash('Error de autenticación', 'error')
        return render_template('admin/change_password.html')
    
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate form inputs
        if not all([current_password, new_password, confirm_password]):
            logger.warning("Missing required fields in password change")
            flash('Todos los campos son requeridos', 'error')
            return render_template('admin/change_password.html')
        
        # Check if new passwords match
        if new_password != confirm_password:
            logger.warning("New passwords do not match")
            flash('Las contraseñas nuevas no coinciden', 'error')
            return render_template('admin/change_password.html')
        
        # Check password length
        if len(new_password) < 8:
            logger.warning("New password too short")
            flash('La nueva contraseña debe tener al menos 8 caracteres', 'error')
            return render_template('admin/change_password.html')
        
        # Get current user data
        logger.info(f"Fetching user data for ID: {user_id}")
        response = supabase.table('admin_users').select('*').eq('id', user_id).execute()
        
        if not response.data:
            logger.error("No user data returned from database")
            flash('Error al obtener datos del usuario', 'error')
            return render_template('admin/change_password.html')
        
        user_data = response.data[0]
        
        # Verificar que el campo password_hash exista
        if 'password_hash' not in user_data:
            logger.error(f"password_hash field not found. Available fields: {list(user_data.keys())}")
            flash('Error en la estructura de datos del usuario', 'error')
            return render_template('admin/change_password.html')
        
        # Verify current password
        if not check_password_hash(user_data['password_hash'], current_password):
            logger.warning("Current password verification failed")
            flash('La contraseña actual es incorrecta', 'error')
            return render_template('admin/change_password.html')
        
        # Check if new password is same as current
        if check_password_hash(user_data['password_hash'], new_password):
            logger.warning("New password is same as current password")
            flash('La nueva contraseña debe ser diferente a la contraseña actual', 'error')
            return render_template('admin/change_password.html')
        
        # Hash new password
        new_password_hash = generate_password_hash(new_password)
        
        # Update password in database
        update_response = supabase.table('admin_users').update({
            'password_hash': new_password_hash,
            'updated_at': 'now()'
        }).eq('id', user_id).execute()
        
        if update_response.data:
            logger.info(f"Password updated successfully for user: {current_user.username}")
            flash('Contraseña actualizada exitosamente', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.error("Database update returned no data")
            flash('Error al actualizar la contraseña', 'error')
            return render_template('admin/change_password.html')
            
    except Exception as e:
        logger.error(f"Unexpected error in change_password: {e}")
        flash('Error al procesar la solicitud', 'error')
        return render_template('admin/change_password.html')

@app.route('/admin/profile')
@admin_required
def admin_profile():
    """Admin profile page"""
    try:
        return render_template('admin/profile.html')
    except Exception as e:
        logger.error(f"Admin profile error: {e}")
        flash('Error al cargar la página de perfil', 'error')
        return render_template('admin/profile.html')

@app.route('/admin/help')
@admin_required
def admin_help():
    """Admin help page"""
    try:
        return render_template('admin/help.html')
    except Exception as e:
        logger.error(f"Admin help error: {e}")
        flash('Error al cargar la página de ayuda', 'error')
        return render_template('admin/help.html')

# Bot Control API Endpoints

def check_bot_service_health():
    """Check if bot service is actually running"""
    try:
        bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
        logger.info(f"[HEALTH-CHECK] Starting health check for: {bot_service_url}")
        logger.info(f"[HEALTH-CHECK] Environment variable BOT_SERVICE_URL: {os.getenv('BOT_SERVICE_URL')}")
        
        response = requests.get(f"{bot_service_url}/health", timeout=10)
        logger.info(f"[HEALTH-CHECK] Response status: {response.status_code}")
        logger.info(f"[HEALTH-CHECK] Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"[HEALTH-CHECK] Response data: {data}")
            
            bot_running = data.get('bot_running', False)
            status_ok = data.get('status') == 'ok'
            
            logger.info(f"[HEALTH-CHECK] Bot running: {bot_running}, Status OK: {status_ok}")
            logger.info(f"[HEALTH-CHECK] Final result: {bot_running and status_ok}")
            
            return bot_running and status_ok
        else:
            logger.warning(f"[HEALTH-CHECK] Failed with status: {response.status_code}")
            logger.warning(f"[HEALTH-CHECK] Response text: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"[HEALTH-CHECK] Exception occurred: {type(e).__name__}: {e}")
        logger.error(f"[HEALTH-CHECK] Exception details: {str(e)}")
        return False

def get_database_bot_status():
    """Get bot status from database"""
    try:
        response = supabase.table('bot_status').select('*').order('last_updated', desc=True).limit(1).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting database bot status: {e}")
        return None

def create_initial_bot_status():
    """Create initial bot status record if none exists"""
    try:
        service_healthy = check_bot_service_health()
        initial_status = {
            'status': 'active' if service_healthy else 'inactive',
            'message': 'Bot status initialized' if service_healthy else 'Bot service not responding',
            'updated_by': 'system',
            'last_updated': datetime.now().isoformat()
        }
        
        response = supabase.table('bot_status').insert(initial_status).execute()
        if response.data:
            logger.info(f"Initial bot status created: {initial_status['status']}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error creating initial bot status: {e}")
        return False

def update_bot_status_in_db(status, message, updated_by):
    """Update bot status in database"""
    try:
        status_data = {
            'status': status,
            'message': message,
            'updated_by': updated_by,
            'last_updated': datetime.now().isoformat()
        }
        
        response = supabase.table('bot_status').insert(status_data).execute()
        return response.data is not None
    except Exception as e:
        logger.error(f"Error updating bot status in database: {e}")
        return False

@app.route('/api/admin/bot/status', methods=['GET'])
@admin_required
def get_bot_status():
    """Get bot status with health check priority"""
    try:
        if not supabase:
            return jsonify({
                'status': 'error',
                'message': 'Database not connected',
                'bot_status': 'unknown',
                'connection_status': 'error'
            }), 500
        
        # Check actual service health FIRST (priority over database)
        service_healthy = check_bot_service_health()
        logger.info(f"Service healthy: {service_healthy}")
        
        # Get database status (secondary, for reference)
        db_status = get_database_bot_status()
        logger.info(f"Database status: {db_status['status'] if db_status else 'None'}")
        
        # Determine status based on ACTUAL health, not database
        if service_healthy:
            actual_status = 'active'  # Bot is running, regardless of database
            connection_status = 'connected'
            
            # Update database if it's wrong or missing
            if not db_status or db_status['status'] != 'active':
                logger.info("Updating database to 'active' - bot is running")
                update_bot_status_in_db('active', 'Bot is running (auto-detected)', 'system')
                db_status = get_database_bot_status()  # Refresh after update
        else:
            actual_status = 'stopped'
            connection_status = 'disconnected'
            
            # Update database if needed
            if not db_status or db_status['status'] != 'stopped':
                logger.info("Updating database to 'stopped' - bot not responding")
                update_bot_status_in_db('stopped', 'Bot is not responding', 'system')
                db_status = get_database_bot_status()  # Refresh after update
        
        return jsonify({
            'status': 'success',
            'bot_status': actual_status,
            'connection_status': connection_status,
            'service_healthy': service_healthy,
            'message': db_status.get('message', '') if db_status else '',
            'updated_by': db_status.get('updated_by', 'system') if db_status else 'system'
        }), 200
            
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get bot status',
            'bot_status': 'unknown',
            'connection_status': 'error'
        }), 500

@app.route('/api/admin/bot/stats', methods=['GET'])
@admin_required
def get_bot_stats():
    """Get detailed bot statistics including daily activity"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        stats = {}
        
        # Get basic user stats
        try:
            total_response = supabase.table('users').select('*', count='exact').execute()
            active_response = supabase.table('users').select('*', count='exact').eq('is_active', True).execute()
            
            stats['active_users'] = active_response.count if hasattr(active_response, 'count') else 0
            stats['total_users'] = total_response.count if hasattr(total_response, 'count') else 0
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            stats['active_users'] = 0
            stats['total_users'] = 0
        
        # Get today's activity
        try:
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time()).isoformat()
            today_end = datetime.combine(today, datetime.max.time()).isoformat()
            
            # For messages today - we would need a message logs table
            # For now, we'll estimate based on user activity
            recent_users_response = supabase.table('users').select('*', count='exact').gte('last_activity', today_start).execute()
            stats['messages_today'] = recent_users_response.count if hasattr(recent_users_response, 'count') else 0
            
            # For exercises completed - sum from users table
            users_response = supabase.table('users').select('total_questions_answered').execute()
            if users_response.data:
                total_exercises = sum(user.get('total_questions_answered', 0) for user in users_response.data)
                stats['exercises_completed'] = total_exercises
            else:
                stats['exercises_completed'] = 0
                
        except Exception as e:
            logger.error(f"Error getting activity stats: {e}")
            stats['messages_today'] = 0
            stats['exercises_completed'] = 0
        
        # Calculate uptime (simplified - based on bot status)
        try:
            bot_status_response = supabase.table('bot_status').select('*').order('last_updated', desc=True).limit(1).execute()
            if bot_status_response.data:
                last_status = bot_status_response.data[0]
                if last_status['status'] in ['active', 'maintenance']:
                    # Calculate uptime from last status change
                    last_update = datetime.fromisoformat(last_status['last_updated'].replace('Z', '+00:00'))
                    uptime = datetime.now() - last_update
                    days = uptime.days
                    hours = uptime.seconds // 3600
                    minutes = (uptime.seconds % 3600) // 60
                    stats['uptime'] = f"{days}d {hours}h {minutes}m"
                else:
                    stats['uptime'] = "0d 0h 0m"
            else:
                stats['uptime'] = "0d 0h 0m"
        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            stats['uptime'] = "0d 0h 0m"
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting bot stats: {e}")
        return jsonify({'error': 'Failed to get bot stats'}), 500

@app.route('/api/admin/debug/config', methods=['GET'])
@admin_required
def debug_config():
    """Debug endpoint to check configuration"""
    try:
        bot_service_url = os.getenv('BOT_SERVICE_URL')
        
        # Test health check
        health_result = check_bot_service_health()
        
        return jsonify({
            'BOT_SERVICE_URL': bot_service_url if bot_service_url else 'NOT_SET (using default)',
            'default_url': 'https://pythontutor-bot.onrender.com',
            'supabase_connected': supabase is not None,
            'health_check_result': health_result,
            'current_time': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Debug config error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/bot/refresh-status', methods=['POST'])
@admin_required
def refresh_bot_status():
    """Force refresh bot status"""
    try:
        service_healthy = check_bot_service_health()
        
        if service_healthy:
            update_bot_status_in_db('active', 'Bot status refreshed - service is running', 'system')
            return jsonify({
                'status': 'success',
                'message': 'Bot is running and connected',
                'service_healthy': True,
                'bot_status': 'active'
            }), 200
        else:
            update_bot_status_in_db('inactive', 'Bot status refreshed - service not responding', 'system')
            return jsonify({
                'status': 'error',
                'message': 'Bot service not responding',
                'service_healthy': False,
                'bot_status': 'inactive'
            }), 500
    except Exception as e:
        logger.error(f"Refresh bot status error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'service_healthy': False
        }), 500

@app.route('/api/admin/registration/status', methods=['GET'])
@admin_required
def get_registration_status():
    """Get user registration status (independent of bot status)"""
    try:
        # Registration should be enabled unless explicitly disabled
        # This could be a separate setting in the future
        return jsonify({
            'registration_enabled': True,
            'message': 'User registration is enabled'
        }), 200
    except Exception as e:
        logger.error(f"Error getting registration status: {e}")
        return jsonify({
            'registration_enabled': True,
            'message': 'Default: registration enabled'
        }), 200

@app.route('/api/admin/debug/health', methods=['GET'])
@admin_required
def debug_health_check():
    """Debug endpoint to test health check manually"""
    try:
        bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
        
        result = {
            'bot_service_url': bot_service_url,
            'env_var_set': os.getenv('BOT_SERVICE_URL') is not None,
            'default_url': 'https://pythontutor-bot.onrender.com',
            'timestamp': datetime.now().isoformat()
        }
        
        # Test actual health check
        try:
            logger.info(f"[DEBUG-HEALTH] Testing URL: {bot_service_url}")
            response = requests.get(f"{bot_service_url}/health", timeout=10)
            result['health_check_status'] = response.status_code
            result['health_check_response'] = response.json()
            result['health_check_success'] = True
            logger.info(f"[DEBUG-HEALTH] Response: {response.json()}")
        except Exception as e:
            result['health_check_error'] = str(e)
            result['health_check_success'] = False
            logger.error(f"[DEBUG-HEALTH] Error: {e}")
        
        # Test check_bot_service_health function
        try:
            service_healthy = check_bot_service_health()
            result['check_function_result'] = service_healthy
            logger.info(f"[DEBUG-HEALTH] Function result: {service_healthy}")
        except Exception as e:
            result['check_function_error'] = str(e)
            logger.error(f"[DEBUG-HEALTH] Function error: {e}")
        
        # Check database status
        try:
            db_status = get_database_bot_status()
            result['database_status'] = db_status
            logger.info(f"[DEBUG-HEALTH] DB status: {db_status}")
        except Exception as e:
            result['database_error'] = str(e)
            logger.error(f"[DEBUG-HEALTH] DB error: {e}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"[DEBUG-HEALTH] General error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/bot/force-active', methods=['POST'])
@admin_required
def force_bot_active():
    """Force bot status to active regardless of health check"""
    try:
        logger.info(f"[FORCE-ACTIVE] Forcing bot to active by {current_user.username}")
        success = update_bot_status_in_db('active', 'Force set to active by admin', current_user.username)
        if success:
            logger.info("[FORCE-ACTIVE] Database updated successfully")
            return jsonify({
                'status': 'success',
                'message': 'Bot status forced to ACTIVE'
            }), 200
        else:
            logger.error("[FORCE-ACTIVE] Failed to update database")
            return jsonify({
                'status': 'error',
                'message': 'Failed to update database'
            }), 500
    except Exception as e:
        logger.error(f"[FORCE-ACTIVE] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/debug/database', methods=['GET'])
@admin_required
def debug_database():
    """Check current database state"""
    try:
        # Get current bot status
        bot_status = get_database_bot_status()
        
        # Get user stats
        try:
            users_response = supabase.table('users').select('*', count='exact').execute()
            total_users = users_response.count if hasattr(users_response, 'count') else 0
        except Exception as e:
            total_users = 0
            logger.error(f"[DEBUG-DB] User count error: {e}")
        
        result = {
            'bot_status': bot_status,
            'total_users': total_users,
            'supabase_connected': supabase is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"[DEBUG-DB] Database state: {result}")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"[DEBUG-DB] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/bot/sync-status', methods=['POST'])
@admin_required
def sync_bot_status():
    """Force sync bot status with actual health check"""
    try:
        service_healthy = check_bot_service_health()
        
        if service_healthy:
            # Force update to active
            update_bot_status_in_db('active', 'Status synchronized - bot is running', 'system')
            return jsonify({
                'status': 'success',
                'message': 'Bot status synchronized to ACTIVE',
                'bot_status': 'active',
                'connection_status': 'connected'
            }), 200
        else:
            update_bot_status_in_db('stopped', 'Status synchronized - bot not responding', 'system')
            return jsonify({
                'status': 'error',
                'message': 'Bot status synchronized to STOPPED',
                'bot_status': 'stopped',
                'connection_status': 'disconnected'
            }), 500
            
    except Exception as e:
        logger.error(f"Error syncing bot status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/admin/bot/start', methods=['POST'])
@admin_required
def start_bot():
    """Start the bot service with verification"""
    try:
        if not supabase:
            return jsonify({'status': 'error', 'message': 'Database not connected'}), 500
        
        # Update database to starting status first
        status_data = {
            'status': 'starting',
            'message': 'Bot is starting...',
            'updated_by': current_user.username,
            'last_updated': datetime.now().isoformat()
        }
        
        response = supabase.table('bot_status').insert(status_data).execute()
        
        if response.data:
            # Send start command to bot service
            bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
            try:
                bot_response = requests.post(
                    f"{bot_service_url}/control",
                    json={"command": "start", "message": "Bot started by admin"},
                    timeout=10
                )
                
                if bot_response.status_code == 200:
                    logger.info(f"Bot service start command sent successfully")
                    
                    # Wait a moment and verify service actually started
                    import time
                    time.sleep(3)  # Give service time to start
                    
                    if check_bot_service_health():
                        # Service is responding, update to active
                        update_bot_status_in_db('active', 'Bot started successfully', current_user.username)
                        return jsonify({
                            'status': 'success',
                            'bot_status': 'active',
                            'message': 'Bot started successfully'
                        }), 200
                    else:
                        # Service not responding after start command
                        update_bot_status_in_db('error', 'Bot failed to start - service not responding', current_user.username)
                        return jsonify({
                            'status': 'error',
                            'message': 'Bot failed to start - service not responding'
                        }), 500
                elif bot_response.status_code == 404:
                    # Control endpoint doesn't exist, but bot might be running
                    logger.warning(f"Bot service control endpoint not found (404), checking health...")
                    if check_bot_service_health():
                        # Bot is running but no control endpoint
                        update_bot_status_in_db('active', 'Bot is running (no control endpoint)', current_user.username)
                        return jsonify({
                            'status': 'success',
                            'bot_status': 'active',
                            'message': 'Bot is already running (control endpoint not available)'
                        }), 200
                    else:
                        update_bot_status_in_db('error', 'Bot control endpoint not found and service not responding', current_user.username)
                        return jsonify({
                            'status': 'error',
                            'message': 'Bot control endpoint not available and service not responding'
                        }), 500
                else:
                    logger.warning(f"Bot service responded with status: {bot_response.status_code}")
                    update_bot_status_in_db('error', f'Bot service error: {bot_response.status_code}', current_user.username)
                    return jsonify({
                        'status': 'error',
                        'message': f'Bot service responded with status: {bot_response.status_code}'
                    }), 500
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"Cannot connect to bot service at {bot_service_url}")
                update_bot_status_in_db('error', 'Cannot connect to bot service', current_user.username)
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot connect to bot service'
                }), 500
            except requests.exceptions.Timeout:
                logger.error("Bot service timeout during start command")
                update_bot_status_in_db('error', 'Bot service timeout during start', current_user.username)
                return jsonify({
                    'status': 'error',
                    'message': 'Bot service timeout during start'
                }), 500
            except Exception as e:
                logger.error(f"Failed to send start command to bot service: {e}")
                update_bot_status_in_db('error', f'Failed to start: {str(e)}', current_user.username)
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to communicate with bot service'
                }), 500
        else:
            return jsonify({'status': 'error', 'message': 'Failed to update database'}), 500
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/api/admin/bot/stop', methods=['POST'])
@admin_required
def stop_bot():
    """Stop the bot service"""
    try:
        if not supabase:
            return jsonify({
                'status': 'error',
                'message': 'Database not connected'
            }), 500
        
        # Update bot status in database
        status_data = {
            'status': 'stopped',
            'last_updated': datetime.now().isoformat(),
            'updated_by': current_user.username,
            'message': 'Bot stopped successfully'
        }
        
        response = supabase.table('bot_status').insert(status_data).execute()
        
        if response.data:
            # Send stop command to bot service
            bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
            try:
                bot_response = requests.post(
                    f"{bot_service_url}/control",
                    json={"command": "stop", "message": "Bot stopped by admin"},
                    timeout=10
                )
                if bot_response.status_code == 200:
                    logger.info(f"Bot service stop command sent successfully")
                else:
                    logger.warning(f"Bot service responded with status: {bot_response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send stop command to bot service: {e}")
            
            logger.info(f"Bot stopped by admin: {current_user.username}")
            return jsonify({
                'status': 'success',
                'bot_status': 'stopped',
                'message': 'Bot stopped successfully',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to stop bot'
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to stop bot'
        }), 500

@app.route('/api/admin/bot/pause', methods=['POST'])
@admin_required
def pause_bot():
    """Pause the bot service"""
    try:
        if not supabase:
            return jsonify({
                'status': 'error',
                'message': 'Database not connected'
            }), 500
        
        # Update bot status in database
        status_data = {
            'status': 'paused',
            'last_updated': datetime.now().isoformat(),
            'updated_by': current_user.username,
            'message': 'Bot paused successfully'
        }
        
        response = supabase.table('bot_status').insert(status_data).execute()
        
        if response.data:
            # Send pause command to bot service
            bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
            try:
                bot_response = requests.post(
                    f"{bot_service_url}/control",
                    json={"command": "pause", "message": "Bot paused by admin"},
                    timeout=10
                )
                if bot_response.status_code == 200:
                    logger.info(f"Bot service pause command sent successfully")
                else:
                    logger.warning(f"Bot service responded with status: {bot_response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send pause command to bot service: {e}")
            
            logger.info(f"Bot paused by admin: {current_user.username}")
            return jsonify({
                'status': 'success',
                'bot_status': 'paused',
                'message': 'Bot paused successfully',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to pause bot'
            }), 500
            
    except Exception as e:
        logger.error(f"Error pausing bot: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to pause bot'
        }), 500

@app.route('/api/admin/bot/restart', methods=['POST'])
@admin_required
def restart_bot():
    """Restart the bot service"""
    try:
        if not supabase:
            return jsonify({
                'status': 'error',
                'message': 'Database not connected'
            }), 500
        
        # Update bot status to restarting first
        status_data = {
            'status': 'restarting',
            'last_updated': datetime.now().isoformat(),
            'updated_by': current_user.username,
            'message': 'Bot is restarting...'
        }
        
        response = supabase.table('bot_status').insert(status_data).execute()
        
        if response.data:
            # Send restart command to bot service
            bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
            try:
                bot_response = requests.post(
                    f"{bot_service_url}/control",
                    json={"command": "restart", "message": "Bot restarted by admin"},
                    timeout=10
                )
                if bot_response.status_code == 200:
                    logger.info(f"Bot service restart command sent successfully")
                else:
                    logger.warning(f"Bot service responded with status: {bot_response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send restart command to bot service: {e}")
            
            logger.info(f"Bot restarted by admin: {current_user.username}")
            
            # After a delay, update to active (simulating restart completion)
            # In real implementation, bot service would update its own status
            return jsonify({
                'status': 'success',
                'bot_status': 'restarting',
                'message': 'Bot is restarting...',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to restart bot'
            }), 500
            
    except Exception as e:
        logger.error(f"Error restarting bot: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to restart bot'
        }), 500

@app.route('/api/admin/bot/maintenance', methods=['POST'])
@admin_required
def toggle_maintenance():
    """Toggle maintenance mode"""
    try:
        if not supabase:
            return jsonify({
                'status': 'error',
                'message': 'Database not connected'
            }), 500
        
        # Get current status
        current_response = supabase.table('bot_status').select('*').order('last_updated', desc=True).limit(1).execute()
        
        current_status = 'inactive'
        if current_response.data:
            current_status = current_response.data[0]['status']
        
        # Toggle maintenance mode
        if current_status == 'maintenance':
            new_status = 'active'
            message = 'Maintenance mode disabled'
        else:
            new_status = 'maintenance'
            message = 'Maintenance mode enabled'
        
        # Update bot status in database
        status_data = {
            'status': new_status,
            'last_updated': datetime.now().isoformat(),
            'updated_by': current_user.username,
            'message': message
        }
        
        response = supabase.table('bot_status').insert(status_data).execute()
        
        if response.data:
            # Send maintenance command to bot service
            bot_service_url = os.getenv('BOT_SERVICE_URL', 'https://pythontutor-bot.onrender.com')
            try:
                bot_response = requests.post(
                    f"{bot_service_url}/control",
                    json={"command": "maintenance", "message": message},
                    timeout=10
                )
                if bot_response.status_code == 200:
                    logger.info(f"Bot service maintenance command sent successfully")
                else:
                    logger.warning(f"Bot service responded with status: {bot_response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to send maintenance command to bot service: {e}")
            
            logger.info(f"Maintenance mode toggled by admin: {current_user.username} - {new_status}")
            return jsonify({
                'status': 'success',
                'bot_status': new_status,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to toggle maintenance mode'
            }), 500
            
    except Exception as e:
        logger.error(f"Error toggling maintenance mode: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to toggle maintenance mode'
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask application on port {port}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.info(f"Supabase connected: {supabase is not None}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {e}")
        raise