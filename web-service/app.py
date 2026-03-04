import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
import json
from functools import wraps
import logging

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

@login_manager.user_loader
def load_user(user_id):
    if not supabase:
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
        if not current_user.is_authenticated:
            flash('Por favor inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
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

@app.route('/about')
def about():
    return render_template('public/about.html')

# Routes - Authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('auth/login.html')
        
        try:
            if not supabase:
                flash('Error de conexión con la base de datos', 'error')
                return render_template('auth/login.html')
                
            response = supabase.table('admin_users').select('*').eq('username', username).execute()
            
            if response.data and check_password_hash(response.data[0]['password_hash'], password):
                user = AdminUser(response.data[0]['id'], response.data[0]['username'])
                login_user(user, remember=request.form.get('remember') == 'on')
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            
            flash('Credenciales inválidas', 'error')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Error al conectar con la base de datos', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([current_password, new_password, confirm_password]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('La nueva contraseña y la confirmación no coinciden', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 8:
            flash('La nueva contraseña debe tener al menos 8 caracteres', 'error')
            return render_template('auth/change_password.html')
        
        try:
            if not supabase:
                flash('Error de conexión con la base de datos', 'error')
                return render_template('auth/change_password.html')
            
            # Get current user data
            response = supabase.table('admin_users').select('*').eq('id', current_user.id).execute()
            
            if not response.data:
                flash('Usuario no encontrado', 'error')
                return render_template('auth/change_password.html')
            
            user_data = response.data[0]
            
            # Verify current password
            if not check_password_hash(user_data['password_hash'], current_password):
                flash('La contraseña actual es incorrecta', 'error')
                return render_template('auth/change_password.html')
            
            # Update password
            new_password_hash = generate_password_hash(new_password)
            update_response = supabase.table('admin_users').update({
                'password_hash': new_password_hash,
                'updated_at': 'now()'
            }).eq('id', current_user.id).execute()
            
            logger.info(f"Update response: {update_response}")
            
            # Check if update was successful (Supabase update doesn't return data on success)
            if hasattr(update_response, 'data') and update_response.data is not None:
                flash('Contraseña actualizada exitosamente', 'success')
                return redirect(url_for('dashboard'))
            elif not hasattr(update_response, 'error') or not update_response.error:
                # Alternative check - if no error, assume success
                flash('Contraseña actualizada exitosamente', 'success')
                return redirect(url_for('dashboard'))
            else:
                logger.error(f"Supabase update error: {update_response.error}")
                flash('Error al actualizar la contraseña', 'error')
                
        except Exception as e:
            logger.error(f"Change password error: {e}")
            flash('Error al actualizar la contraseña', 'error')
    
    return render_template('auth/change_password.html')

# Routes - Admin Panel
@app.route('/admin/dashboard')
@admin_required
def dashboard():
    try:
        if not supabase:
            logger.error("Supabase client is None")
            flash('Error de conexión con la base de datos', 'error')
            return render_template('auth/dashboard.html', total_users=0, total_exercises=0, exercises_by_level={})
        
        # Initialize default values
        total_users = 0
        total_exercises = 0
        level_counts = {'principiante': 0, 'intermedio': 0, 'avanzado': 0, 'experto': 0}
        
        # Get total users with error handling
        try:
            users_response = supabase.table('users').select('*', count='exact').execute()
            if hasattr(users_response, 'count'):
                total_users = users_response.count
            elif users_response.data:
                total_users = len(users_response.data)
            logger.info(f"Total users retrieved: {total_users}")
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            total_users = 0
        
        # Get total exercises with error handling
        try:
            exercises_response = supabase.table('exercises').select('*', count='exact').execute()
            if hasattr(exercises_response, 'count'):
                total_exercises = exercises_response.count
            elif exercises_response.data:
                total_exercises = len(exercises_response.data)
            logger.info(f"Total exercises retrieved: {total_exercises}")
        except Exception as e:
            logger.error(f"Error getting total exercises: {e}")
            total_exercises = 0
        
        # Get exercises by level with corrected query
        try:
            # First get all exercises to count by level
            all_exercises = supabase.table('exercises').select('level').execute()
            
            if all_exercises and all_exercises.data:
                for exercise in all_exercises.data:
                    level = exercise.get('level', '').lower()
                    if level in level_counts:
                        level_counts[level] += 1
            
            logger.info(f"Exercises by level: {level_counts}")
        except Exception as e:
            logger.error(f"Error getting exercises by level: {e}")
            # Keep default values if query fails
        
        return render_template('auth/dashboard.html', 
                             total_users=total_users,
                             total_exercises=total_exercises,
                             exercises_by_level=level_counts)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error al cargar el dashboard', 'error')
        return render_template('auth/dashboard.html', total_users=0, total_exercises=0, exercises_by_level={})

@app.route('/admin/exercises')
@admin_required
def exercises():
    level = request.args.get('level', 'todos')
    
    try:
        if not supabase:
            flash('Error de conexión con la base de datos', 'error')
            return render_template('auth/exercises.html', exercises=[], current_level=level)
            
        if level and level != 'todos':
            response = supabase.table('exercises').select('*').eq('level', level).execute()
        else:
            response = supabase.table('exercises').select('*').execute()
        
        exercises_list = response.data if response.data else []
        
        # Parse options for each exercise
        for exercise in exercises_list:
            if isinstance(exercise.get('options'), str):
                try:
                    exercise['options'] = json.loads(exercise['options'])
                except:
                    exercise['options'] = []
        
        return render_template('auth/exercises.html', exercises=exercises_list, current_level=level)
    except Exception as e:
        logger.error(f"Exercises error: {e}")
        flash('Error al cargar los ejercicios', 'error')
        return render_template('auth/exercises.html', exercises=[], current_level=level)

@app.route('/admin/add-exercise', methods=['GET', 'POST'])
@admin_required
def add_exercise():
    if request.method == 'POST':
        level = request.form.get('level')
        question = request.form.get('question')
        options = [
            request.form.get('option1', '').strip(),
            request.form.get('option2', '').strip(),
            request.form.get('option3', '').strip(),
            request.form.get('option4', '').strip()
        ]
        correct_answer = int(request.form.get('correct_answer', 1)) - 1
        explanation = request.form.get('explanation', '').strip()
        
        # Validate
        if not all([level, question, all(options)]):
            flash('Todos los campos obligatorios deben estar completos', 'error')
            return redirect(url_for('add_exercise'))
        
        try:
            if not supabase:
                flash('Error de conexión con la base de datos', 'error')
                return redirect(url_for('add_exercise'))
                
            # Check count per level
            current_count = supabase.table('exercises').select('*', count='exact').eq('level', level).execute()
            
            if current_count.count >= 300:
                flash(f'El nivel {level} ya tiene 300 ejercicios', 'error')
                return redirect(url_for('add_exercise'))
            
            # Insert exercise
            exercise_data = {
                'level': level,
                'question': question,
                'options': json.dumps(options),
                'correct_answer': correct_answer,
                'explanation': explanation
            }
            
            response = supabase.table('exercises').insert(exercise_data).execute()
            
            if response.data:
                flash('Ejercicio agregado exitosamente', 'success')
                return redirect(url_for('exercises', level=level))
            else:
                flash('Error al agregar el ejercicio', 'error')
        except Exception as e:
            logger.error(f"Add exercise error: {e}")
            flash('Error al guardar el ejercicio', 'error')
    
    return render_template('auth/add_exercise.html')

@app.route('/admin/edit-exercise/<int:exercise_id>', methods=['GET', 'POST'])
@admin_required
def edit_exercise(exercise_id):
    if request.method == 'POST':
        level = request.form.get('level')
        question = request.form.get('question')
        options = [
            request.form.get('option1', '').strip(),
            request.form.get('option2', '').strip(),
            request.form.get('option3', '').strip(),
            request.form.get('option4', '').strip()
        ]
        correct_answer = int(request.form.get('correct_answer', 1)) - 1
        explanation = request.form.get('explanation', '').strip()
        
        try:
            if not supabase:
                flash('Error de conexión con la base de datos', 'error')
                return redirect(url_for('exercises'))
                
            exercise_data = {
                'level': level,
                'question': question,
                'options': json.dumps(options),
                'correct_answer': correct_answer,
                'explanation': explanation,
                'updated_at': 'now()'
            }
            
            response = supabase.table('exercises').update(exercise_data).eq('id', exercise_id).execute()
            
            if response.data:
                flash('Ejercicio actualizado exitosamente', 'success')
                return redirect(url_for('exercises', level=level))
            else:
                flash('Error al actualizar el ejercicio', 'error')
        except Exception as e:
            logger.error(f"Edit exercise error: {e}")
            flash('Error al actualizar el ejercicio', 'error')
    
    # Get exercise data
    try:
        if not supabase:
            flash('Error de conexión con la base de datos', 'error')
            return redirect(url_for('exercises'))
            
        response = supabase.table('exercises').select('*').eq('id', exercise_id).execute()
        exercise = response.data[0] if response.data else None
        
        if not exercise:
            flash('Ejercicio no encontrado', 'error')
            return redirect(url_for('exercises'))
        
        # Parse options
        if isinstance(exercise.get('options'), str):
            try:
                exercise['options'] = json.loads(exercise['options'])
            except:
                exercise['options'] = []
        
        exercise['current_level'] = request.args.get('level', 'todos')
        
        return render_template('auth/edit_exercise.html', exercise=exercise)
    except Exception as e:
        logger.error(f"Get exercise error: {e}")
        flash('Error al cargar el ejercicio', 'error')
        return redirect(url_for('exercises'))

@app.route('/admin/delete-exercise/<int:exercise_id>')
@admin_required
def delete_exercise(exercise_id):
    try:
        if not supabase:
            flash('Error de conexión con la base de datos', 'error')
            return redirect(url_for('exercises'))
            
        response = supabase.table('exercises').delete().eq('id', exercise_id).execute()
        
        if response.data:
            flash('Ejercicio eliminado exitosamente', 'success')
        else:
            flash('Error al eliminar el ejercicio', 'error')
    except Exception as e:
        logger.error(f"Delete exercise error: {e}")
        flash('Error al eliminar el ejercicio', 'error')
    
    return redirect(url_for('exercises'))

@app.route('/admin/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('add_exercise'))
    
    file = request.files['file']
    level = request.form.get('level')
    
    if not level:
        flash('Debes seleccionar un nivel', 'error')
        return redirect(url_for('add_exercise'))
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('add_exercise'))
    
    if file and file.filename.endswith('.json'):
        try:
            if not supabase:
                flash('Error de conexión con la base de datos', 'error')
                return redirect(url_for('add_exercise'))
                
            exercises = json.load(file)
            
            if not isinstance(exercises, list):
                flash('El archivo debe contener un array de ejercicios', 'error')
                return redirect(url_for('add_exercise'))
            
            # Validate count
            current_count = supabase.table('exercises').select('*', count='exact').eq('level', level).execute()
            available_slots = 300 - (current_count.count if hasattr(current_count, 'count') else 0)
            
            if len(exercises) > available_slots:
                flash(f'Solo hay {available_slots} espacios disponibles para el nivel {level}', 'error')
                return redirect(url_for('add_exercise'))
            
            # Prepare exercises for insertion
            for exercise in exercises:
                if not all(k in exercise for k in ['question', 'options', 'correct_answer']):
                    flash('Formato de ejercicio inválido', 'error')
                    return redirect(url_for('add_exercise'))
                
                exercise['level'] = level
                exercise['options'] = json.dumps(exercise['options'])
                exercise['explanation'] = exercise.get('explanation', '')
            
            response = supabase.table('exercises').insert(exercises).execute()
            
            if response.data:
                flash(f'{len(exercises)} ejercicios agregados exitosamente', 'success')
            else:
                flash('Error al agregar los ejercicios', 'error')
        
        except json.JSONDecodeError:
            flash('Archivo JSON inválido', 'error')
        except Exception as e:
            logger.error(f"Bulk upload error: {e}")
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
    else:
        flash('Por favor sube un archivo JSON válido', 'error')
    
    return redirect(url_for('exercises', level=level))

# API endpoints for bot
@app.route('/api/user/<int:telegram_id>', methods=['GET'])
def get_user(telegram_id):
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        
        if response.data:
            return jsonify(response.data[0])
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"API get_user error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user', methods=['POST'])
def create_user():
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        data = request.json
        response = supabase.table('users').insert(data).execute()
        
        if response.data:
            return jsonify(response.data[0]), 201
        else:
            return jsonify({'error': 'Failed to create user'}), 400
    except Exception as e:
        logger.error(f"API create_user error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/exercises/<level>', methods=['GET'])
def get_exercises_by_level(level):
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        response = supabase.table('exercises').select('*').eq('level', level).execute()
        return jsonify(response.data if response.data else [])
    except Exception as e:
        logger.error(f"API get_exercises error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/progress', methods=['POST'])
def update_user_progress():
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        data = request.json
        telegram_id = data.get('telegram_id')
        exercise_id = data.get('exercise_id')
        completed = data.get('completed', False)
        
        # Check if progress exists
        check = supabase.table('user_progress').select('*')\
            .eq('user_id', telegram_id)\
            .eq('exercise_id', exercise_id)\
            .execute()
        
        if check.data:
            # Update existing progress
            response = supabase.table('user_progress')\
                .update({'completed': completed, 'last_attempt': 'now()'})\
                .eq('user_id', telegram_id)\
                .eq('exercise_id', exercise_id)\
                .execute()
        else:
            # Create new progress
            progress_data = {
                'user_id': telegram_id,
                'exercise_id': exercise_id,
                'completed': completed
            }
            response = supabase.table('user_progress').insert(progress_data).execute()
        
        if completed:
            # Get current progress
            user_response = supabase.table('users').select('level_progress').eq('telegram_id', telegram_id).execute()
            if user_response.data:
                current_progress = user_response.data[0].get('level_progress', 0)
                # Update user stats
                supabase.table('users')\
                    .update({
                        'level_progress': current_progress + 1,
                        'last_activity': 'now()'
                    })\
                    .eq('telegram_id', telegram_id)\
                    .execute()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"API update_progress error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/progress/<int:telegram_id>/<level>', methods=['GET'])
def get_user_progress_by_level(telegram_id, level):
    """Get user progress for a specific level"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        # Count completed exercises for this level
        response = supabase.table('user_progress')\
            .select('exercise_id')\
            .eq('user_id', telegram_id)\
            .eq('completed', True)\
            .execute()
        
        # Get exercise IDs for this level
        exercises_response = supabase.table('exercises')\
            .select('id')\
            .eq('level', level)\
            .execute()
        
        if exercises_response.data and response.data:
            level_exercise_ids = [ex['id'] for ex in exercises_response.data]
            completed_exercises = [prog['exercise_id'] for prog in response.data]
            
            # Count completed exercises in this level
            completed_in_level = len([ex_id for ex_id in completed_exercises if ex_id in level_exercise_ids])
            
            return jsonify({
                'completed_count': completed_in_level,
                'total_count': len(level_exercise_ids)
            })
        
        return jsonify({'completed_count': 0, 'total_count': 0})
    except Exception as e:
        logger.error(f"API get_progress_by_level error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/stats/<int:telegram_id>', methods=['GET'])
def get_user_stats(telegram_id):
    """Get comprehensive user statistics"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        # Get user data
        user_response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        
        if not user_response.data:
            return jsonify({'error': 'User not found'}), 404
            
        user_data = user_response.data[0]
        
        # Get progress by level
        levels = ['principiante', 'intermedio', 'avanzado', 'experto']
        progress_by_level = {}
        
        for level in levels:
            progress_response = supabase.table('user_progress')\
                .select('exercise_id')\
                .eq('user_id', telegram_id)\
                .eq('completed', True)\
                .execute()
            
            # Get exercise IDs for this level
            exercises_response = supabase.table('exercises')\
                .select('id')\
                .eq('level', level)\
                .execute()
            
            if exercises_response.data and progress_response.data:
                level_exercise_ids = [ex['id'] for ex in exercises_response.data]
                completed_exercises = [prog['exercise_id'] for prog in progress_response.data]
                
                completed_in_level = len([ex_id for ex_id in completed_exercises if ex_id in level_exercise_ids])
                progress_by_level[level] = {
                    'completed': completed_in_level,
                    'total': len(level_exercise_ids)
                }
            else:
                progress_by_level[level] = {'completed': 0, 'total': 0}
        
        # Calculate current streak (simplified - days since last activity)
        current_streak = 0
        if user_data.get('last_activity'):
            try:
                from datetime import datetime
                last_activity = datetime.fromisoformat(user_data['last_activity'].replace('Z', '+00:00'))
                today = datetime.now()
                days_diff = (today - last_activity).days
                current_streak = 1 if days_diff <= 1 else 0
            except:
                current_streak = 0
        
        return jsonify({
            'user_data': user_data,
            'progress_by_level': progress_by_level,
            'current_streak': current_streak,
            'total_completed': user_data.get('total_exercises_completed', 0),
            'current_level': user_data.get('current_level', 'principiante')
        })
    except Exception as e:
        logger.error(f"API get_user_stats error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/user/streak/<int:telegram_id>', methods=['POST'])
def update_user_streak(telegram_id):
    """Update user streak"""
    try:
        if not supabase:
            return jsonify({'error': 'Database connection error'}), 500
            
        # Get current user data
        user_response = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        
        if not user_response.data:
            return jsonify({'error': 'User not found'}), 404
            
        user_data = user_response.data[0]
        current_streak = user_data.get('current_streak', 0)
        
        # Update streak (simplified logic)
        new_streak = current_streak + 1
        
        supabase.table('users')\
            .update({'current_streak': new_streak})\
            .eq('telegram_id', telegram_id)\
            .execute()
        
        return jsonify({'success': True, 'new_streak': new_streak})
    except Exception as e:
        logger.error(f"API update_streak error: {e}")
        return jsonify({'error': 'Database error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
