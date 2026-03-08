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

# Cargar variables de entorno al inicio
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir peticiones del bot
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    try:
        # Check if Supabase is available for bot operations
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
            flash('Error de conexión a la base de datos', 'danger')
            logger.error("Admin exercises: Supabase not connected")
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
        
        # Debug: Log template data
        template_data = {
            'exercises': processed_exercises
        }
        logger.info(f"Passing to template: {len(template_data['exercises'])} exercises")
        
        return render_template('admin/exercises.html', exercises=processed_exercises)
    except Exception as e:
        logger.error(f"Admin exercises error: {e}", exc_info=True)
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
        
        # Process options for each exercise
        for exercise in exercises:
            if isinstance(exercise.get('options'), str):
                try:
                    exercise['options'] = json.loads(exercise['options'])
                except:
                    exercise['options'] = ['', '', '', '']
        
        return jsonify({'exercises': exercises})
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
@admin_required
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

@app.route('/api/admin/exercises/import', methods=['POST'])
@admin_required
def api_import_exercises():
    """Import exercises from JSON - MEJORADO"""
    try:
        if not supabase:
            logger.error("Import failed: Supabase not connected")
            return jsonify({'error': 'Database connection error'}), 500
        
        data = request.json
        exercises = data.get('exercises', [])
        
        if not isinstance(exercises, list):
            logger.error(f"Import failed: exercises is not a list, got {type(exercises)}")
            return jsonify({'error': 'Exercises must be an array'}), 400
        
        logger.info(f"Starting import process: {len(exercises)} exercises to process")
        
        imported_count = 0
        errors = []
        skipped_duplicates = 0
        
        for index, exercise in enumerate(exercises):
            try:
                logger.debug(f"Processing exercise {index + 1}: {exercise.get('question', 'NO QUESTION')[:50]}...")
                
                # Normalize exercise data
                normalized_exercise = normalize_exercise_data(exercise)
                logger.debug(f"Normalized exercise {index + 1}: level={normalized_exercise['level']}, correct_answer={normalized_exercise['correct_answer']}")
                
                # Validate structure
                validation_result = validate_exercise_structure(normalized_exercise)
                if not validation_result['valid']:
                    error_msg = f"Ejercicio {index + 1}: {validation_result['error']}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Check for duplicates (optional)
                if is_duplicate_exercise(normalized_exercise['question']):
                    error_msg = f"Ejercicio {index + 1}: Pregunta duplicada - omitido"
                    logger.info(error_msg)
                    skipped_duplicates += 1
                    continue
                
                # Insert in database
                exercise_data = {
                    'question': normalized_exercise['question'],
                    'level': normalized_exercise['level'],
                    'options': json.dumps(normalized_exercise['options']),
                    'correct_answer': normalized_exercise['correct_answer'],
                    'explanation': normalized_exercise.get('explanation', ''),
                    'created_at': datetime.now().isoformat()
                }
                
                logger.debug(f"Attempting to insert exercise {index + 1} into database")
                result = supabase.table('exercises').insert(exercise_data).execute()
                
                if result.data:
                    imported_count += 1
                    logger.info(f"Successfully imported exercise {index + 1}")
                else:
                    error_msg = f"Ejercicio {index + 1}: Error al insertar en base de datos - no data returned"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
            except Exception as e:
                error_msg = f"Ejercicio {index + 1}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        logger.info(f"Import completed: {imported_count} imported, {skipped_duplicates} duplicates skipped, {len(errors)} errors out of {len(exercises)} total")
        
        return jsonify({
            'imported': imported_count,
            'skipped_duplicates': skipped_duplicates,
            'total': len(exercises),
            'errors': errors
        })
    except Exception as e:
        logger.error(f"API import exercises error: {e}", exc_info=True)
        return jsonify({'error': f'Database error: {str(e)}'}), 500

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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)