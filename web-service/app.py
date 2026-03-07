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
from datetime import datetime

# Cargar variables de entorno al inicio
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir peticiones del bot
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            # Verificación básica
            if not current_user.is_authenticated:
                logger.info("Admin_required: User not authenticated")
                return redirect(url_for('login'))
            
            # Verificación de ID
            if not hasattr(current_user, 'id') or not current_user.id:
                logger.info("Admin_required: User has no valid ID")
                return redirect(url_for('login'))
            
            # Temporalmente desactivar verificación de cache para debugging
            # if str(current_user.id) in user_cache.get('invalidated', set()):
            #     logger.info(f"Admin_required: User {current_user.id} in invalidation cache")
            #     return redirect(url_for('login'))
            
            logger.info(f"Admin_required: User {current_user.username} passed all checks")
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Admin_required error: {e}")
            return redirect(url_for('login'))
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
@app.route('/')
def index():
    return render_template('public/index.html')

@app.route('/features')
def features():
    return render_template('public/features.html')

@app.route('/about')
def about():
    return render_template('public/about.html')

# Routes - Authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logger.info(f"User already authenticated: {current_user.username}")
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
    
    return render_template('public/login.html')

@app.route('/debug/logout')
def debug_logout():
    """Debug logout endpoint to identify the exact problem"""
    try:
        logger.info("=== DEBUG LOGOUT START ===")
        logger.info(f"Current user object: {current_user}")
        logger.info(f"Is authenticated: {current_user.is_authenticated}")
        logger.info(f"Session data: {dict(session)}")
        logger.info(f"Session keys: {list(session.keys())}")
        
        # Test individual components
        try:
            logout_user()
            logger.info("logout_user() successful")
        except Exception as e:
            logger.error(f"logout_user() failed: {e}")
            return f"logout_user error: {e}", 500
        
        try:
            target_url = url_for('index')
            logger.info(f"url_for('index') successful: {target_url}")
        except Exception as e:
            logger.error(f"url_for('index') failed: {e}")
            return f"url_for error: {e}", 500
        
        try:
            flash('Debug logout successful', 'success')
            logger.info("flash() successful")
        except Exception as e:
            logger.error(f"flash() failed: {e}")
            # Continue without flash
        
        return "Debug logout completed successfully", 200
        
    except Exception as e:
        logger.error(f"Debug logout error: {e}")
        return f"Debug error: {e}", 500

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

@app.route('/debug/session-status')
def debug_session_status():
    """Debug endpoint to check session status"""
    try:
        from flask import session
        from flask_login import current_user
        
        status = {
            'session_keys': list(session.keys()),
            'session_user_id': session.get('_user_id'),
            'current_user_authenticated': current_user.is_authenticated,
            'current_user_id': getattr(current_user, 'id', None),
            'current_user_username': getattr(current_user, 'username', None),
            'session_modified': getattr(session, 'modified', False)
        }
        
        return status, 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/debug/login-flow')
def debug_login_flow():
    """Debug endpoint to check login flow"""
    try:
        from flask_login import current_user
        
        flow_info = {
            'current_user_authenticated': current_user.is_authenticated,
            'current_user_id': getattr(current_user, 'id', None),
            'current_user_username': getattr(current_user, 'username', None),
            'session_keys': list(session.keys()),
            'session_user_id': session.get('_user_id'),
            'user_cache_invalidated': list(user_cache.get('invalidated', set())),
            'dashboard_url': url_for('dashboard'),
            'login_url': url_for('login')
        }
        
        return flow_info, 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/debug/session-deep')
def debug_session_deep():
    """Deep debug of session state"""
    try:
        from flask import session, request
        from flask_login import current_user
        
        debug_info = {
            'request_cookies': dict(request.cookies),
            'session_data': dict(session),
            'session_keys': list(session.keys()),
            'session_user_id': session.get('_user_id'),
            'session_modified': getattr(session, 'modified', False),
            'current_user': {
                'is_authenticated': current_user.is_authenticated,
                'id': getattr(current_user, 'id', None),
                'username': getattr(current_user, 'username', None),
                'is_active': getattr(current_user, 'is_active', None),
            },
            'user_cache_invalidated': list(user_cache.get('invalidated', set())),
            'flask_login_config': {
                'login_view': login_manager.login_view,
                'session_protection': getattr(login_manager, 'session_protection', 'unknown'),
                'refresh_view': getattr(login_manager, 'refresh_view', None),
            }
        }
        
        return debug_info, 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/debug/invalidate-user/<int:user_id>')
def debug_invalidate_user(user_id):
    """Debug endpoint to invalidate a specific user"""
    try:
        user_cache.setdefault('invalidated', set()).add(str(user_id))
        return f"User {user_id} invalidated", 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/debug/test-flask')
def debug_test_flask():
    """Test if Flask is working"""
    return "Flask is working", 200

@app.route('/debug/test-session')
def debug_test_session():
    """Test if session is working"""
    try:
        from flask import session
        return f"Session working: {bool(session)}", 200
    except Exception as e:
        return f"Session error: {e}", 500

@app.route('/debug/test-current-user')
def debug_test_current_user():
    """Test if current_user is working"""
    try:
        from flask_login import current_user
        return f"Current user working: {bool(current_user)}", 200
    except Exception as e:
        return f"Current user error: {e}", 500

@app.route('/debug/test-logout-user')
def debug_test_logout_user():
    """Test if logout_user is working"""
    try:
        from flask_login import logout_user
        return "logout_user working", 200
    except Exception as e:
        return f"logout_user error: {e}", 500

@app.route('/debug/test-url-for')
def debug_test_url_for():
    """Test if url_for is working"""
    try:
        from flask import url_for
        index_url = url_for('index')
        return f"url_for working: {index_url}", 200
    except Exception as e:
        return f"url_for error: {e}", 500

# Routes - Admin Panel
@app.route('/admin/dashboard')
@admin_required
def dashboard():
    try:
        return render_template('admin/dashboard.html')
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error al cargar el dashboard', 'error')
        return render_template('admin/dashboard.html')





# ==================== ADMIN ROUTES ====================




@login_required
def admin_help():
    """Admin help page"""
    return render_template('admin/help.html')

@app.route('/admin/profile')
@login_required
def admin_profile():
    """Admin profile page"""
    return render_template('admin/profile.html')

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """Admin logs page"""
    return render_template('admin/logs.html')

@app.route('/admin/backup')
@login_required
def admin_backup():
    """Admin backup page"""
    return render_template('admin/backup.html')


@app.route('/admin/bot-control')
@admin_required
def admin_bot_control():
    """Admin bot control page"""
    try:
        # Check if Supabase is available for bot operations
        if not supabase:
            flash('Conexión a la base de datos no disponible', 'warning')
        return render_template('admin/bot_control.html', db_connected=(supabase is not None))
    except Exception as e:
        logger.error(f"Admin bot control error: {e}")
        flash('Error al cargar la página de control del bot', 'error')
        return render_template('admin/bot_control.html', db_connected=False)

@app.route('/admin/notifications')
@admin_required
def admin_notifications():
    """Admin notifications page"""
    try:
        # Check if Supabase is available for notifications
        if not supabase:
            flash('Conexión a la base de datos no disponible', 'warning')
        return render_template('admin/notifications.html', db_connected=(supabase is not None))
    except Exception as e:
        logger.error(f"Admin notifications error: {e}")
        flash('Error al cargar la página de notificaciones', 'error')
        return render_template('admin/notifications.html', db_connected=False)

@app.route('/admin/exercises')
@admin_required
def admin_exercises():
    """Admin exercises management page"""
    try:
        if not supabase:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('admin/exercises.html', exercises=[])
        
        # Get all exercises
        exercises_response = supabase.table('exercises').select('*').order('created_at', desc=True).execute()
        exercises = exercises_response.data or []
        
        return render_template('admin/exercises.html', exercises=exercises)
    except Exception as e:
        logger.error(f"Admin exercises error: {e}")
        flash('Error al cargar ejercicios', 'danger')
        return render_template('admin/exercises.html', exercises=[])

# API Endpoints for Bot
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
    """Create new user for bot"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        user_data = request.get_json()
        
        # Validate required fields
        required_fields = ['telegram_id', 'username', 'first_name']
        for field in required_fields:
            if field not in user_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if user already exists
        existing_user = supabase.table('users').select('*').eq('telegram_id', user_data['telegram_id']).execute()
        if existing_user.data:
            return jsonify(existing_user.data[0]), 200
        
        # Create new user
        response = supabase.table('users').insert({
            'telegram_id': user_data['telegram_id'],
            'username': user_data.get('username', ''),
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'current_level': user_data.get('current_level', 'principiante'),
            'level_progress': user_data.get('level_progress', 0),
            'total_exercises_completed': user_data.get('total_exercises_completed', 0),
            'last_activity': 'now()',
            'created_at': 'now()'
        }).execute()
        
        if response.data:
            return jsonify(response.data[0]), 201
        else:
            return jsonify({'error': 'Failed to create user'}), 500
            
    except Exception as e:
        logger.error(f"API create user error: {e}")
        return jsonify({'error': 'Database error'}), 500

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
            return jsonify(response.data), 200
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
        # This is a simplified version - in a real implementation you'd have a separate progress table
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

@app.route('/api/admin/exercises/export/csv')
@admin_required
def export_exercises_csv():
    """Export exercises in CSV format"""
    try:
        if not supabase:
            return jsonify({'error': 'Database not connected'}), 500
        
        exercises_response = supabase.table('exercises').select('*').order('created_at', desc=True).execute()
        exercises = exercises_response.data or []
        
        # Create CSV content
        csv_content = 'ID,Nivel,Pregunta,Opción1,Opción2,Opción3,Opción4,Respuesta,Explicación\n'
        
        for exercise in exercises:
            # Escape quotes and commas for CSV
            def escape_csv(text):
                if not text:
                    return ''
                return f'"{str(text).replace('"', '""')}"'
            
            csv_content += f"{exercise.id},{exercise.level},"
            csv_content += f"{escape_csv(exercise.question)},"
            csv_content += f"{escape_csv(exercise.options[0])},{escape_csv(exercise.options[1])},"
            csv_content += f"{escape_csv(exercise.options[2])},{escape_csv(exercise.options[3])},"
            csv_content += f"{exercise.correct_answer},{escape_csv(exercise.explanation)}\n"
        
        from flask import Response
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=ejercicios_{datetime.now().strftime("%Y-%m-%d")}.csv'
        return response
        
    except Exception as e:
        logger.error(f"Error exporting exercises to CSV: {e}")
        return jsonify({'error': str(e)}), 500

# API Endpoints for Exercises Management
@app.route('/api/admin/exercises', methods=['GET'])
@admin_required
def api_get_exercises():
    """Get all exercises"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        level = request.args.get('level')
        search = request.args.get('search')
        
        query = supabase.table('exercises').select('*')
        
        if level:
            query = query.eq('level', level)
        
        if search:
            query = query.ilike('question', f'%{search}%')
        
        response = query.order('created_at', desc=True).execute()
        
        return jsonify({'exercises': response.data or []})
    except Exception as e:
        logger.error(f"API get exercises error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/exercises', methods=['POST'])
@admin_required
def api_create_exercise():
    """Create new exercise"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        
        # Validate required fields
        required_fields = ['question', 'level', 'options', 'correct_answer']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create exercise
        exercise_data = {
            'question': data['question'],
            'level': data['level'],
            'options': data['options'],
            'correct_answer': data['correct_answer'],
            'explanation': data.get('explanation', ''),
            'created_at': 'now()'
        }
        
        response = supabase.table('exercises').insert(exercise_data).execute()
        
        if response.data:
            return jsonify(response.data[0]), 201
        else:
            return jsonify({'error': 'Failed to create exercise'}), 400
    except Exception as e:
        logger.error(f"API create exercise error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/exercises/<int:exercise_id>', methods=['PUT'])
@admin_required
def api_update_exercise(exercise_id):
    """Update exercise"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        
        # Update exercise
        update_data = {
            'question': data.get('question'),
            'level': data.get('level'),
            'options': data.get('options'),
            'correct_answer': data.get('correct_answer'),
            'explanation': data.get('explanation', ''),
            'updated_at': 'now()'
        }
        
        response = supabase.table('exercises').update(update_data).eq('id', exercise_id).execute()
        
        if response.data:
            return jsonify(response.data[0])
        else:
            return jsonify({'error': 'Exercise not found'}), 404
    except Exception as e:
        logger.error(f"API update exercise error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/exercises/<int:exercise_id>', methods=['DELETE'])
@admin_required
def api_delete_exercise(exercise_id):
    """Delete exercise"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        response = supabase.table('exercises').delete().eq('id', exercise_id).execute()
        
        if response.data:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Exercise not found'}), 404
    except Exception as e:
        logger.error(f"API delete exercise error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/exercises/import', methods=['POST'])
@admin_required
def api_import_exercises():
    """Import exercises from JSON"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        exercises = data.get('exercises', [])
        
        if not isinstance(exercises, list):
            return jsonify({'error': 'Exercises must be an array'}), 400
        
        imported_count = 0
        errors = []
        
        for exercise in exercises:
            try:
                # Validate exercise structure
                required_fields = ['question', 'level', 'options', 'correct_answer']
                if not all(field in exercise for field in required_fields):
                    errors.append(f"Invalid exercise structure: {exercise.get('question', 'Unknown')}")
                    continue
                
                exercise_data = {
                    'question': exercise['question'],
                    'level': exercise['level'],
                    'options': exercise['options'],
                    'correct_answer': exercise['correct_answer'],
                    'explanation': exercise.get('explanation', ''),
                    'created_at': 'now()'
                }
                
                supabase.table('exercises').insert(exercise_data).execute()
                imported_count += 1
            except Exception as e:
                errors.append(f"Error importing exercise: {str(e)}")
        
        return jsonify({
            'imported': imported_count,
            'total': len(exercises),
            'errors': errors
        })
    except Exception as e:
        logger.error(f"API import exercises error: {e}")
        return jsonify({'error': 'Database error'}), 500

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
            total_users_response = supabase.table('bot_users').select('id', count='exact').execute()
            active_users_response = supabase.table('bot_users').select('id', count='exact').eq('is_active', True).execute()
            inactive_users_response = supabase.table('bot_users').select('id', count='exact').eq('is_active', False).execute()
            
            stats = {
                'total': total_users_response.count or 0,
                'active': active_users_response.count or 0,
                'inactive': inactive_users_response.count or 0
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            stats = {'total': 0, 'active': 0, 'inactive': 0}
        
        # Get recent users (last 10)
        try:
            users_response = supabase.table('bot_users').select('*').order('created_at', desc=True).limit(10).execute()
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
        query = supabase.table('bot_users').select('*')
        
        # Apply filters
        if search:
            query = query.or_(f"username.ilike.%{search}%,first_name.ilike.%{search}%,last_name.ilike.%{search}%")
        
        if status == 'active':
            query = query.eq('is_active', True)
        elif status == 'inactive':
            query = query.eq('is_active', False)
        
        # Get total count
        count_query = query
        count_response = count_query.select('id', count='exact').execute()
        total = count_response.count or 0
        
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
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"API get users error: {e}")
        return jsonify({'error': 'Database error'}), 500

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
        response = supabase.table('bot_users').update({
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
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id):
    """Delete user"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get user info for logging
        user_response = supabase.table('bot_users').select('username, telegram_id').eq('id', user_id).execute()
        
        # Delete user
        response = supabase.table('bot_users').delete().eq('id', user_id).execute()
        
        if response.data:
            user_info = user_response.data[0] if user_response.data else {}
            logger.info(f"User {user_id} ({user_info.get('username', 'Unknown')}) deleted by admin {current_user.username}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"API delete user error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/users/stats', methods=['GET'])
@admin_required
def api_get_user_stats():
    """Get user statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
        
        # Get basic stats
        total_response = supabase.table('bot_users').select('id', count='exact').execute()
        active_response = supabase.table('bot_users').select('id', count='exact').eq('is_active', True).execute()
        
        # Get recent users (last 7 days)
        import datetime
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        recent_response = supabase.table('bot_users').select('id', count='exact').gte('created_at', week_ago).execute()
        
        stats = {
            'total': total_response.count or 0,
            'active': active_response.count or 0,
            'inactive': (total_response.count or 0) - (active_response.count or 0),
            'recent': recent_response.count or 0
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"API get user stats error: {e}")
        return jsonify({'error': 'Database error'}), 500

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
    logger.info(f"Form data received: {list(request.form.keys())}")
    
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
        
        logger.info(f"Form values - current_password: {'provided' if current_password else 'missing'}, "
                    f"new_password: {'provided' if new_password else 'missing'}, "
                    f"confirm_password: {'provided' if confirm_password else 'missing'}")
        
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
        
        logger.info(f"Supabase response success: {response.data is not None}")
        logger.info(f"Response data length: {len(response.data) if response.data else 0}")
        
        if not response.data:
            logger.error("No user data returned from database")
            flash('Error al obtener datos del usuario', 'error')
            return render_template('admin/change_password.html')
        
        user_data = response.data[0]
        logger.info(f"User data keys: {list(user_data.keys())}")
        logger.info(f"User data available fields: {[k for k in user_data.keys() if 'password' in k.lower()]}")
        
        # Verificar que el campo password_hash exista
        if 'password_hash' not in user_data:
            logger.error(f"password_hash field not found. Available fields: {list(user_data.keys())}")
            flash('Error en la estructura de datos del usuario', 'error')
            return render_template('admin/change_password.html')
        
        logger.info("Attempting to verify current password...")
        # Verify current password
        if not check_password_hash(user_data['password_hash'], current_password):
            logger.warning("Current password verification failed")
            flash('La contraseña actual es incorrecta', 'error')
            return render_template('admin/change_password.html')
        
        logger.info("Current password verified successfully")
        
        # Check if new password is same as current
        if check_password_hash(user_data['password_hash'], new_password):
            logger.warning("New password is same as current password")
            flash('La nueva contraseña debe ser diferente a la contraseña actual', 'error')
            return render_template('admin/change_password.html')
        
        logger.info("Generating new password hash...")
        # Hash new password
        new_password_hash = generate_password_hash(new_password)
        
        logger.info("Updating password in database...")
        # Update password in database (solo campos que existen en Supabase)
        update_response = supabase.table('admin_users').update({
            'password_hash': new_password_hash
        }).eq('id', user_id).execute()
        
        logger.info(f"Update response success: {update_response.data is not None}")
        logger.info(f"Update response data: {update_response.data}")
        
        if update_response.data:
            logger.info(f"Password updated successfully for user: {current_user.username}")
            flash('Contraseña actualizada exitosamente', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.error("Database update returned no data")
            logger.error(f"Supabase error details: {getattr(update_response, 'error', 'No error info')}")
            flash('Error al actualizar la contraseña', 'error')
            return render_template('admin/change_password.html')
            
    except KeyError as e:
        logger.error(f"KeyError in change_password: {e}")
        logger.error(f"Available keys: {list(user_data.keys()) if 'user_data' in locals() else 'N/A'}")
        flash('Error en los datos del usuario', 'error')
        return render_template('admin/change_password.html')
    except AttributeError as e:
        logger.error(f"AttributeError in change_password: {e}")
        logger.error(f"User data type: {type(user_data) if 'user_data' in locals() else 'N/A'}")
        flash('Error en el procesamiento de datos', 'error')
        return render_template('admin/change_password.html')
    except ValueError as e:
        logger.error(f"ValueError in change_password: {e}")
        flash('Error en el formato de los datos', 'error')
        return render_template('admin/change_password.html')
    except Exception as e:
        logger.error(f"Unexpected error in change_password: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        logger.error(f"User data available: {'user_data' in locals()}")
        if 'user_data' in locals():
            logger.error(f"User data keys: {list(user_data.keys())}")
        logger.error(f"Current user ID: {current_user.id}")
        flash('Error al procesar la solicitud', 'error')
        return render_template('admin/change_password.html')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
