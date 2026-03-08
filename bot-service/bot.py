import os
import logging
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from supabase import create_client, Client
import asyncio
import signal
import sys
import threading
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import random

# Cargar variables de entorno
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# HEALTH CHECK SERVER PARA RENDER
# ============================================
health_app = Flask(__name__)

@health_app.route('/health')
def health():
    return jsonify({
        "status": "ok", 
        "service": "pythontutor-bot",
        "bot_running": True
    })

@health_app.route('/status')
def bot_status():
    """Get current bot status for admin panel"""
    status = get_bot_status()
    return jsonify({
        "status": "success",
        "bot_status": status['status'],
        "message": status['message'],
        "last_updated": status['last_updated'].isoformat(),
        "service": "pythontutor-bot"
    })

@health_app.route('/control', methods=['POST'])
def bot_control():
    """Receive control commands from web service"""
    try:
        command = request.json.get('command')
        message = request.json.get('message', '')
        
        if not command:
            return jsonify({
                "status": "error",
                "message": "Missing command parameter"
            }), 400
        
        # Validate command
        valid_commands = ['start', 'stop', 'pause', 'restart', 'maintenance']
        if command not in valid_commands:
            return jsonify({
                "status": "error",
                "message": f"Invalid command: {command}"
            }), 400
        
        # Map commands to status
        status_map = {
            'start': 'active',
            'stop': 'stopped',
            'pause': 'paused',
            'restart': 'restarting',
            'maintenance': 'maintenance'
        }
        
        new_status = status_map[command]
        
        # Special handling for maintenance toggle
        if command == 'maintenance':
            current_status = get_bot_status()['status']
            if current_status == 'maintenance':
                new_status = 'active'
                message = 'Maintenance mode disabled'
            else:
                new_status = 'maintenance'
                message = message or 'Maintenance mode enabled'
        
        # Update bot status
        set_bot_status(new_status, message)
        
        logger.info(f"Bot control command received: {command} -> {new_status}")
        
        return jsonify({
            "status": "success",
            "bot_status": new_status,
            "message": message or f"Bot {command}ed successfully",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in bot control endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@health_app.route('/')
def root():
    return jsonify({
        "service": "PythonTutor Bot",
        "status": "running",
        "endpoints": ["/health"]
    })

def run_health_server():
    """Ejecutar servidor de health check en puerto separado"""
    port = int(os.getenv('PORT', 10001))
    logger.info(f"Starting health check server on port {port}")
    health_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Iniciar health check en un hilo separado
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()
logger.info("Health check server started in background thread")

# ============================================
# CONFIGURACIÓN DEL BOT
# ============================================

# Verificar variables de entorno
required_env_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'TELEGRAM_BOT_TOKEN']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    sys.exit(1)

# Supabase initialization
try:
    supabase: Client = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    logger.info("Supabase connected successfully")
    
    # Test the connection
    test_query = supabase.table('users').select('*').limit(1).execute()
    logger.info("Supabase query test successful")
except Exception as e:
    logger.error(f"Supabase connection error: {e}")
    sys.exit(1)

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEB_API_URL = os.getenv('WEB_API_URL', 'https://pythontutor-web.onrender.com')

# User session storage (en memoria, se perderá al reiniciar)
user_sessions = {}

# Bot state management
bot_state = {
    'status': 'active',  # active, inactive, paused, stopped, maintenance, restarting
    'last_updated': datetime.now(),
    'message': 'Bot is running normally'
}

# Bot status lock for thread safety
import threading
status_lock = threading.Lock()

def get_bot_status():
    """Get current bot status"""
    with status_lock:
        return bot_state.copy()

def set_bot_status(status, message=None):
    """Set bot status with thread safety"""
    with status_lock:
        bot_state['status'] = status
        bot_state['last_updated'] = datetime.now()
        if message:
            bot_state['message'] = message
        logger.info(f"Bot status updated to: {status} - {message or ''}")

def is_bot_active():
    """Check if bot is active and can accept user interactions"""
    with status_lock:
        return bot_state['status'] == 'active'

def get_bot_status_message():
    """Get appropriate message for current bot status"""
    with status_lock:
        status = bot_state['status']
        if status == 'stopped':
            return "🔴 El bot está temporalmente desactivado. Intenta más tarde."
        elif status == 'paused':
            return "⏸️ El bot está en pausa. Intenta más tarde."
        elif status == 'maintenance':
            return "🔧 Modo mantenimiento: El bot está siendo actualizado. Vuelve pronto."
        elif status == 'restarting':
            return "🔄 El bot está reiniciando. Espera unos momentos."
        elif status == 'inactive':
            return "⚫ El bot está inactivo. Contacta al administrador."
        else:  # active
            return None  # No message for active status

def check_bot_status(handler):
    """Decorator to check bot status before allowing user interactions"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_bot_active():
            status_message = get_bot_status_message()
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(status_message)
            else:
                await update.message.reply_text(status_message)
            return
        return await handler(update, context)
    return wrapper

def check_bot_access(handler):
    """Decorator to allow user registration in more states than full access"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        current_status = get_bot_status()['status']
        
        # Completely block access in these states
        if current_status in ['stopped', 'paused', 'inactive']:
            status_message = get_bot_status_message()
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(status_message)
            else:
                await update.message.reply_text(status_message)
            return
        
        # Allow access but show warning in these states
        if current_status in ['maintenance', 'restarting']:
            warning_message = get_registration_warning_message(current_status)
            if update.callback_query:
                await update.callback_query.answer()
                # Send warning as a new message to avoid interfering with callback
                await update.callback_query.message.reply_text(warning_message)
            else:
                await update.message.reply_text(warning_message)
        
        # Continue with handler for allowed states
        return await handler(update, context)
    return wrapper

def get_registration_warning_message(status):
    """Get appropriate warning message for registration in limited states"""
    warning = ""
    if status == 'maintenance':
        warning = "🔧 *Modo Mantenimiento*\n\n"
    elif status == 'restarting':
        warning = "🔄 *Bot Reiniciando*\n\n"
    
    warning += "El registro está permitido, pero algunas funciones pueden estar limitadas. " \
               "Por favor intenta más tarde para acceder a todas las funcionalidades."
    return warning

# Exercise cache management
exercise_cache = {}
cache_timestamp = {}

# Level order and progression requirements
LEVELS = ['principiante', 'intermedio', 'avanzado', 'experto']
LEVEL_REQUIREMENTS = {
    'principiante': 0,      # Starting level
    'intermedio': 50,       # Need 50 exercises to unlock
    'avanzado': 150,        # Need 150 exercises to unlock  
    'experto': 300,         # Need 300 exercises to unlock
    'graduado': 500         # Need 500 exercises to graduate
}

def refresh_exercises_cache(level):
    """Refrescar cache de ejercicios"""
    exercises = get_exercises_from_supabase(level)
    exercise_cache[level] = exercises
    cache_timestamp[level] = datetime.now()
    logger.info(f"Exercise cache refreshed for level: {level}")
    return exercises

def get_cached_exercises(level):
    """Obtener ejercicios desde cache con timeout"""
    from datetime import timedelta
    
    # Verificar si cache existe y no está expirada (30 minutos)
    if level not in exercise_cache or \
       datetime.now() - cache_timestamp.get(level, datetime.min) > timedelta(minutes=30):
        return refresh_exercises_cache(level)
    
    return exercise_cache[level]

def invalidate_exercises_cache():
    """Invalidar toda la cache de ejercicios"""
    global exercise_cache, cache_timestamp
    exercise_cache.clear()
    cache_timestamp.clear()
    logger.info("Exercise cache invalidated")

# ============================================
# FUNCIONES DIRECTAS DE SUPABASE
# ============================================

def get_user_from_supabase(telegram_id):
    """Obtener usuario directamente desde Supabase"""
    try:
        logger.info(f"Getting user {telegram_id} from Supabase")
        result = supabase.table('users').select('*').eq('telegram_id', str(telegram_id)).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"User {telegram_id} found in Supabase")
            return result.data[0]
        else:
            logger.info(f"User {telegram_id} not found in Supabase")
            return None
            
    except Exception as e:
        logger.error(f"Error getting user from Supabase: {e}")
        return None

def create_user_in_supabase(user_data):
    """Crear usuario directamente en Supabase"""
    try:
        logger.info(f"Creating user in Supabase: {user_data}")
        
        # Ensure telegram_id is string
        if 'telegram_id' in user_data:
            user_data['telegram_id'] = str(user_data['telegram_id'])
        
        # Set default values if not provided
        defaults = {
            'current_level': 'principiante',
            'level_progress': 0,
            'total_exercises_completed': 0,
            'current_streak': 0,
            'longest_streak': 0,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'is_active': True
        }
        
        for key, value in defaults.items():
            if key not in user_data:
                user_data[key] = value
        
        result = supabase.table('users').insert(user_data).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"User created successfully in Supabase: {result.data[0]}")
            return {"success": True, "data": result.data[0]}
        else:
            logger.error("No data returned from Supabase insert")
            return {"success": False, "error": "no_data_returned"}
            
    except Exception as e:
        logger.error(f"Error creating user in Supabase: {e}")
        return {"success": False, "error": str(e)}

def update_user_in_supabase(telegram_id, updates):
    """Actualizar usuario en Supabase"""
    try:
        telegram_id = str(telegram_id)
        updates['last_activity'] = datetime.now().isoformat()
        
        result = supabase.table('users').update(updates).eq('telegram_id', telegram_id).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"User {telegram_id} updated successfully")
            return result.data[0]
        else:
            logger.warning(f"No user found to update: {telegram_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error updating user in Supabase: {e}")
        return None

def get_exercises_from_supabase(level):
    """Obtener ejercicios desde Supabase"""
    try:
        logger.info(f"Getting exercises for level: {level} from Supabase")
        result = supabase.table('exercises').select('*').eq('level', level).execute()
        
        if result.data:
            logger.info(f"Found {len(result.data)} exercises for level {level}")
            return result.data
        else:
            logger.warning(f"No exercises found for level {level}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting exercises from Supabase: {e}")
        return []

def update_progress_in_supabase(telegram_id, exercise_id, completed):
    """Actualizar progreso en Supabase"""
    try:
        telegram_id = str(telegram_id)
        
        # Get current user data
        user = get_user_from_supabase(telegram_id)
        if not user:
            logger.error(f"User {telegram_id} not found for progress update")
            return False
        
        # Update user statistics
        updates = {}
        if completed:
            updates['total_exercises_completed'] = user.get('total_exercises_completed', 0) + 1
            updates['level_progress'] = user.get('level_progress', 0) + 1
            updates['current_streak'] = user.get('current_streak', 0) + 1
            
            # Update longest streak if needed
            if updates['current_streak'] > user.get('longest_streak', 0):
                updates['longest_streak'] = updates['current_streak']
        else:
            updates['current_streak'] = 0
        
        updates['last_activity'] = datetime.now().isoformat()
        
        # Update user
        update_user_in_supabase(telegram_id, updates)
        
        # Record exercise completion
        progress_data = {
            'user_id': user.get('id'),
            'exercise_id': exercise_id,
            'completed_at': datetime.now().isoformat(),
            'was_correct': completed
        }
        
        supabase.table('user_progress').insert(progress_data).execute()
        
        logger.info(f"Progress updated for user {telegram_id}, exercise {exercise_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating progress in Supabase: {e}")
        return False

def get_global_ranking_from_supabase():
    """Obtener ranking global desde Supabase"""
    try:
        result = supabase.table('users').select('telegram_id, first_name, total_exercises_completed').order('total_exercises_completed', desc=True).limit(50).execute()
        
        if result.data:
            return result.data
        return []
        
    except Exception as e:
        logger.error(f"Error getting ranking from Supabase: {e}")
        return []

# ============================================
# FUNCIONES API (mantenidas por compatibilidad)
# ============================================

def check_web_service_health():
    """Verificar si el servicio web está disponible"""
    try:
        logger.info(f"Checking web service health at: {WEB_API_URL}/api/test")
        response = requests.get(f"{WEB_API_URL}/api/test", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Web service health check passed: {data}")
            return True, data
        else:
            logger.error(f"Web service health check failed with status {response.status_code}")
            return False, None
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to web service at {WEB_API_URL}: {e}")
        return False, None
    except requests.exceptions.Timeout:
        logger.error("Web service health check timeout")
        return False, None
    except Exception as e:
        logger.error(f"Web service health check error: {e}")
        return False, None

def create_local_user_session(telegram_id, user):
    """Crear sesión de usuario local"""
    user_sessions[telegram_id] = {
        'current_level': 'principiante',
        'mode': None,
        'learning_session': {
            'current_exercise': 0,
            'streak': 0,
            'completed_today': 0
        },
        'practice_session': {
            'target_count': 0,
            'completed_count': 0,
            'correct_count': 0,
            'current_exercise': None
        },
        'score': 0,
        'local_mode': True
    }
    logger.info(f"Created local session for user {telegram_id} ({user.first_name})")

# ============================================
# HANDLERS DEL BOT
# ============================================

@check_bot_access
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler - Direct Supabase integration"""
    user = update.effective_user
    telegram_id = user.id
    
    logger.info(f"User {telegram_id} ({user.first_name}) started the bot")
    
    # Get user directly from Supabase
    user_data = get_user_from_supabase(telegram_id)
    
    if not user_data:
        # User not found - create new user in Supabase
        await update.message.reply_text(
            "👋 ¡Hola! Parece que eres un nuevo usuario.\n\n"
            "📝 *Creando tu perfil en la base de datos...*",
            parse_mode='Markdown'
        )
        
        # Create user in Supabase
        new_user_data = {
            'telegram_id': str(telegram_id),
            'username': user.username or '',
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'current_level': 'principiante',
            'level_progress': 0,
            'total_exercises_completed': 0,
            'current_streak': 0,
            'longest_streak': 0,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'is_active': True
        }
        
        created_user = create_user_in_supabase(new_user_data)
        if created_user.get("success"):
            user_data = created_user.get("data")
            await update.message.reply_text(
                "✅ *¡Perfil creado exitosamente!*\n\n"
                "🎉 *¡Bienvenido a PythonBot!*",
                parse_mode='Markdown'
            )
        else:
            error_msg = f"❌ *Error al crear tu perfil*\n\n"
            error_msg += f"🔄 *{created_user.get('error', 'Error desconocido')}*\n\n"
            error_msg += "💡 *Por favor intenta de nuevo en unos momentos*"
            
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return
    
    # Check and update level based on progress
    updated_level = check_and_update_level(telegram_id, user_data)
    if updated_level != user_data.get('current_level'):
        user_data['current_level'] = updated_level
        update_user_in_supabase(telegram_id, {'current_level': updated_level})
    
    # Initialize user session
    user_sessions[telegram_id] = {
        'current_level': user_data.get('current_level', 'principiante'),
        'mode': None,
        'learning_session': {
            'current_exercise': 0,
            'streak': 0,
            'completed_today': 0
        },
        'practice_session': {
            'target_count': 0,
            'completed_count': 0,
            'correct_count': 0,
            'current_exercise': None
        },
        'score': 0
    }
    
    # Get progression info
    current_level = user_data.get('current_level', 'principiante')
    total_completed = user_data.get('total_exercises_completed', 0)
    next_level_info = get_next_level_info(current_level, total_completed)
    
    # Duolingo-style welcome interface
    welcome_text = f"""
🐍 ¡Bienvenido a PythonBot, {user.first_name}!

Soy tu tutor personal de Python. Te ayudaré a aprender programación con ejercicios interactivos.

📚 *Sistema de Aprendizaje:*
• Comienzas en nivel Principiante
• Avanza automáticamente por logros
• Desbloquea niveles superiores

🎯 *Tu Progreso Actual:*
• Nivel Actual: {current_level.title()}
• Ejercicios Completados: {total_completed}
• Progreso del Nivel: {user_data.get('level_progress', 0)}/50

{next_level_info}

⭐ *Elige tu modo de aprendizaje:*
    """
    
    # Duolingo-style main menu
    keyboard = [
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_menu")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")],
        [InlineKeyboardButton("🏆 Ranking Mundial", callback_data="ranking")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

@check_bot_status
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        message = update.message
        reply_func = message.reply_text
    
    help_text = """
🐍 *Comandos de PythonBot*

📚 *Aprendizaje:*
/start - Iniciar o reiniciar el bot
/practice - Modo Práctica (ejercicios de tu nivel)

📊 *Estadísticas:*
/stats - Ver tus estadísticas y progreso
/ranking - Ver el ranking mundial de usuarios

🎯 *Sistema de Progresión:*
• Comienzas automáticamente en Principiante
• Avanza completando ejercicios
• Desbloquea niveles superiores:
  🌱 Principiante → Intermedio (50 ejercicios)
  🌿 Intermedio → Avanzado (150 ejercicios)
  🚀 Avanzado → Experto (300 ejercicios)
  👑 Experto → Graduado (500 ejercicios)

⭐ *Características:*
• 1200+ ejercicios interactivos
• Progreso automático
• Logros y recompensas
• Ranking global

🎮 *Tips:*
• Completa ejercicios diariamente
• Cada respuesta correcta suma puntos
• Tu progreso se guarda automáticamente
• ¡Compite con otros usuarios!

¿Listo para aprender Python? 🚀
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_menu")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(help_text, parse_mode='Markdown', reply_markup=reply_markup)

@check_bot_status
async def learning_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Learning mode handler - XP-earning progression mode"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    # Check if user exists
    user_data = get_user_from_supabase(telegram_id)
    if not user_data:
        await reply_func(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    # Set mode to learning
    if telegram_id not in user_sessions:
        user_sessions[telegram_id] = {}
    
    user_sessions[telegram_id]['mode'] = 'learning'
    user_sessions[telegram_id]['learning_session'] = user_sessions[telegram_id].get('learning_session', {
        'current_exercise': 0,
        'streak': 0,
        'completed_today': 0
    })
    
    # Check and update level based on progress
    updated_level = check_and_update_level(telegram_id, user_data)
    if updated_level != user_data.get('current_level'):
        user_data['current_level'] = updated_level
        update_user_in_supabase(telegram_id, {'current_level': updated_level})
        if update.callback_query:
            await celebrate_level_up(update.callback_query, user_data.get('current_level'), updated_level)
        else:
            await celebrate_level_up(update, user_data.get('current_level'), updated_level)
        return
    
    current_level = user_data.get('current_level', 'principiante')
    level_progress = user_data.get('level_progress', 0)
    total_completed = user_data.get('total_exercises_completed', 0)
    
    # Get exercises from cache
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await reply_func(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['learning_session']['current_exercise_data'] = exercise
    user_sessions[telegram_id]['current_level'] = current_level
    
    # Format exercise with learning progress info
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    progress_bar = create_progress_bar(level_progress, 50)
    streak = user_sessions[telegram_id]['learning_session']['streak']
    
    exercise_text = f"""
🎯 *Lección del Día - Nivel {current_level.title()}*

{question}

📊 *Progreso del Nivel:* {progress_bar} {level_progress}/50
🔥 *Racha Actual:* {streak} ejercicios seguidos
🏆 *Total Completados:* {total_completed} ejercicios

🔘 *Opciones:*
"""
    
    keyboard = []
    for i, option in enumerate(options):
        exercise_text += f"{i+1}. {option}\n"
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {option}", 
            callback_data=f"learning_answer_{exercise['id']}_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("💡 Ver Explicación", callback_data=f"explanation_{exercise['id']}")])
    keyboard.append([InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_learning_exercise")])
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

@check_bot_status
async def practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Practice command handler - Redirect to practice menu"""
    await practice_menu(update, context)

@check_bot_status
async def practice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Practice menu handler - Choose practice session size"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    # Check if user exists
    user_data = get_user_from_supabase(telegram_id)
    if not user_data:
        await reply_func(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    current_level = user_data.get('current_level', 'principiante')
    
    practice_text = f"""
📝 *Modo Práctica - Nivel {current_level.title()}*

Elige cuántos ejercicios quieres practicar:

📚 *Características del Modo Práctica:*
• No ganas experiencia (XP)
• No afecta tu nivel de progreso
• Ideal para practicar y dominar conceptos
• Repite ejercicios tantas veces como quieras

📊 *Tu progreso actual no se verá afectado*
    """
    
    keyboard = [
        [InlineKeyboardButton("🔥 5 Ejercicios", callback_data="setup_practice_5")],
        [InlineKeyboardButton("⚡ 10 Ejercicios", callback_data="setup_practice_10")],
        [InlineKeyboardButton("💪 20 Ejercicios", callback_data="setup_practice_20")],
        [InlineKeyboardButton("∞ Ilimitado", callback_data="setup_practice_unlimited")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        practice_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def setup_practice(update: Update, context: ContextTypes.DEFAULT_TYPE, target_count):
    """Setup practice session handler"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    # Check if user exists
    user_data = get_user_from_supabase(telegram_id)
    if not user_data:
        await reply_func(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    current_level = user_data.get('current_level', 'principiante')
    
    # Initialize practice session
    if telegram_id not in user_sessions:
        user_sessions[telegram_id] = {}
    
    unlimited = target_count == -1
    actual_target = float('inf') if unlimited else target_count
    
    user_sessions[telegram_id]['mode'] = 'practice'
    user_sessions[telegram_id]['practice_session'] = {
        'target_count': actual_target,
        'completed_count': 0,
        'correct_count': 0,
        'current_exercise': None,
        'unlimited': unlimited
    }
    
    # Get exercises from cache
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await reply_func(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get first exercise
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['practice_session']['current_exercise'] = exercise
    user_sessions[telegram_id]['current_level'] = current_level
    
    # Format practice exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    session = user_sessions[telegram_id]['practice_session']
    progress_text = f"{session['completed_count']}/∞" if unlimited else f"{session['completed_count']}/{session['target_count']}"
    accuracy = f"{(session['correct_count']/max(1, session['completed_count'])*100):.0f}%" if session['completed_count'] > 0 else "0%"
    
    exercise_text = f"""
📝 *Modo Práctica - Nivel {current_level.title()}*

{question}

📊 *Sesión de Práctica:* {progress_text} ejercicios
✅ *Precisión:* {accuracy}

📚 *Recuerda:* Este modo no afecta tu nivel de progreso

🔘 *Opciones:*
"""
    
    keyboard = []
    for i, option in enumerate(options):
        exercise_text += f"{i+1}. {option}\n"
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {option}", 
            callback_data=f"practice_answer_{exercise['id']}_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("💡 Ver Explicación", callback_data=f"explanation_{exercise['id']}")])
    keyboard.append([InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_practice_exercise")])
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

@check_bot_status
async def ranking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ranking command handler - Global leaderboard"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    # Check if user exists
    user_data = get_user_from_supabase(telegram_id)
    if not user_data:
        await reply_func(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    await reply_func(
        "🏆 *Cargando Ranking Mundial...*\n\n⏳ Obteniendo datos de todos los usuarios...",
        parse_mode='Markdown'
    )
    
    # Get global ranking data from Supabase
    ranking_data = get_global_ranking_from_supabase()
    
    if not ranking_data:
        await reply_func(
            "❌ No se pudo cargar el ranking. Por favor intenta más tarde."
        )
        return
    
    # Find user's position
    user_position = next((i+1 for i, user in enumerate(ranking_data) if str(user['telegram_id']) == str(telegram_id)), None)
    
    ranking_text = "🏆 *Ranking Mundial de PythonBot*\n\n"
    
    # Show top 10 users
    for i, user_rank in enumerate(ranking_data[:10]):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        
        # Highlight current user
        if str(user_rank['telegram_id']) == str(telegram_id):
            ranking_text += f"👤 *{medal} {user_rank['first_name']}* - {user_rank['total_exercises_completed']} pts\n"
        else:
            ranking_text += f"{medal} {user_rank['first_name']} - {user_rank['total_exercises_completed']} pts\n"
    
    ranking_text += "\n"
    
    # Show user's position if not in top 10
    if user_position and user_position > 10:
        ranking_text += f"👤 *Tu Posición: #{user_position}*\n"
        ranking_text += f"📊 *Tus Puntos: {user_data.get('total_exercises_completed', 0)}*\n\n"
    
    ranking_text += "📈 *Categorías del Ranking:*\n"
    ranking_text += "• 🌱 Principiantes: 0-49 ejercicios\n"
    ranking_text += "• 🌿 Intermedios: 50-149 ejercicios\n"
    ranking_text += "• 🚀 Avanzados: 150-299 ejercicios\n"
    ranking_text += "• 👑 Expertos: 300+ ejercicios\n\n"
    ranking_text += "🔄 Ranking actualizado en tiempo real"
    
    keyboard = [
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_menu")],
        [InlineKeyboardButton("🔄 Actualizar Ranking", callback_data="ranking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        ranking_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

@check_bot_status
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics command handler - Enhanced with progression info"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    user_data = get_user_from_supabase(telegram_id)
    
    if not user_data:
        await reply_func(
            "❌ No se encontró tu perfil. Por favor usa /start para crear uno."
        )
        return
    
    # Check and update level based on progress
    updated_level = check_and_update_level(telegram_id, user_data)
    if updated_level != user_data.get('current_level'):
        user_data['current_level'] = updated_level
        update_user_in_supabase(telegram_id, {'current_level': updated_level})
    
    current_level = user_data.get('current_level', 'principiante')
    total_completed = user_data.get('total_exercises_completed', 0)
    level_progress = user_data.get('level_progress', 0)
    
    # Calculate progression info
    next_level_info = get_next_level_info(current_level, total_completed)
    progress_bar = create_progress_bar(level_progress, 50)
    completion_percentage = calculate_completion_percentage(telegram_id)
    
    # Get achievements
    achievements = get_user_achievements(user_data)
    
    stats_text = f"""
📊 *Mis Estadísticas - PythonBot*

👤 *Perfil:* {user_data.get('first_name', 'N/A')}
📱 *ID:* {user_data.get('telegram_id', 'N/A')}

📚 *Progreso Actual:*
• Nivel Actual: {current_level.title()}
• Progreso del Nivel: {progress_bar} {level_progress}/50
• Total Completados: {total_completed} ejercicios
• Porcentaje Total: {completion_percentage}%

{next_level_info}

🏆 *Logros Desbloqueados:*
{achievements}

📈 *Estadísticas Detalladas:*
• Racha Actual: 🔥 {user_data.get('current_streak', 0)} días
• Mejor Racha: ⭐ {user_data.get('longest_streak', 0)} días

🎯 *Próximos Objetivos:*
{get_next_objectives(current_level, total_completed)}
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_menu")],
        [InlineKeyboardButton("🏆 Ver Ranking", callback_data="ranking")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        stats_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About command handler"""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        message = update.message
        reply_func = message.reply_text
    
    about_text = """
🐍 *Acerca de PythonBot*

PythonBot es tu tutor personal de aprendizaje de programación Python.

🎯 *Misión:*
Hacer el aprendizaje de Python accesible, interactivo y divertido para todos.

📚 *Características:*
• 1200+ ejercicios interactivos
• 4 niveles de dificultad
• Aprendizaje adaptativo
• Progreso en tiempo real
• Disponible 24/7

🔧 *Tecnología:*
• Bot de Telegram
• Base de datos Supabase
• API RESTful

👨‍💻 *Desarrollado por:*
Equipo PythonTutor

📧 *Contacto:*
• Web: https://pythontutor-web.onrender.com
• Bot: @PythonTutorBot

¡Aprende Python donde sea, cuando sea! 🚀
    """
    
    keyboard = [
        [InlineKeyboardButton("🌐 Visitar Web", url="https://pythontutor-web.onrender.com")],
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        about_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu handler"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    user_data = get_user_from_supabase(telegram_id)
    
    if not user_data:
        await start(update, context)
        return
    
    welcome_text = f"""
🐍 *PythonBot - Menú Principal*

👤 *Usuario:* {user_data.get('first_name', 'N/A')}
📚 *Nivel Actual:* {user_data.get('current_level', 'principiante').title()}
🏆 *Ejercicios:* {user_data.get('total_exercises_completed', 0)}

⭐ *Elige una opción:*
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_menu")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")],
        [InlineKeyboardButton("🏆 Ranking Mundial", callback_data="ranking")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="help")],
        [InlineKeyboardButton("ℹ️ Acerca de", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

# Callback query handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    data = query.data
    
    logger.info(f"Callback received: {data} from user {telegram_id}")
    
    if data == "learning_mode":
        await learning_mode(update, context)
    elif data == "practice_menu":
        await practice_menu(update, context)
    elif data.startswith("setup_practice_"):
        count_str = data.split("_")[2]
        if count_str == "unlimited":
            count = -1
        else:
            count = int(count_str)
        await setup_practice(update, context, count)
    elif data == "main_menu":
        await main_menu(update, context)
    elif data == "stats":
        await stats_command(update, context)
    elif data == "ranking":
        await ranking_command(update, context)
    elif data == "refresh_ranking":
        await ranking_command(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "about":
        await about_command(update, context)
    elif data == "next_learning_exercise":
        await next_learning_exercise(update, context)
    elif data.startswith("learning_answer_"):
        parts = data.split("_")
        exercise_id = int(parts[2])
        answer_index = int(parts[3])
        await learning_answer_callback(query, context, exercise_id, answer_index)
    elif data == "next_practice_exercise":
        await next_practice_exercise(update, context)
    elif data.startswith("practice_answer_"):
        parts = data.split("_")
        exercise_id = int(parts[2])
        answer_index = int(parts[3])
        await practice_answer_callback(query, context, exercise_id, answer_index)

async def learning_answer_callback(query, context, exercise_id, answer_index):
    """Handle learning mode answer callback - XP earning"""
    telegram_id = query.from_user.id
    
    # Get exercises from cache
    current_level = user_sessions.get(telegram_id, {}).get('current_level', 'principiante')
    exercises = get_cached_exercises(current_level)
    exercise = next((e for e in exercises if e['id'] == exercise_id), None)
    
    if not exercise:
        await query.edit_message_text("❌ Error al cargar el ejercicio.")
        return
    
    correct_answer = exercise['correct_answer']
    is_correct = answer_index == correct_answer
    
    # Update progress in Supabase
    update_progress_in_supabase(telegram_id, exercise_id, is_correct)
    
    # Update learning session streak
    if telegram_id not in user_sessions:
        user_sessions[telegram_id] = {'learning_session': {'streak': 0, 'completed_today': 0}, 'score': 0}
    
    session = user_sessions[telegram_id].get('learning_session', {'streak': 0, 'completed_today': 0})
    if is_correct:
        session['streak'] = session.get('streak', 0) + 1
        session['completed_today'] = session.get('completed_today', 0) + 1
        user_sessions[telegram_id]['score'] = user_sessions[telegram_id].get('score', 0) + 10
    else:
        session['streak'] = 0
    
    user_sessions[telegram_id]['learning_session'] = session
    
    # Get updated user data to check for level up
    user_data = get_user_from_supabase(telegram_id)
    if user_data:
        old_level = user_data.get('current_level', 'principiante')
        new_level = check_and_update_level(telegram_id, user_data)
        
        # Check if user leveled up
        if new_level != old_level:
            await celebrate_level_up(query, old_level, new_level)
            return
    
    # Format response
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    if is_correct:
        response_text = "✅ *¡Correcto!*\n\n"
        response_text += f"🔥 *Racha actual:* {session['streak']} ejercicios seguidos\n\n"
    else:
        response_text = f"❌ *Incorrecto.*\n\n"
        response_text += f"La respuesta correcta es: {options[correct_answer]}\n\n"
        response_text += f"💔 *Racha perdida*\n\n"
    
    if exercise.get('explanation'):
        response_text += f"💡 *Explicación:*\n{exercise['explanation']}\n\n"
    
    response_text += f"🏆 *Puntos:* {user_sessions[telegram_id].get('score', 0)} puntos"
    
    keyboard = [
        [InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_learning_exercise")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def practice_answer_callback(query, context, exercise_id, answer_index):
    """Handle practice mode answer callback - No XP earned"""
    telegram_id = query.from_user.id
    
    # Get exercises from cache
    current_level = user_sessions.get(telegram_id, {}).get('current_level', 'principiante')
    exercises = get_cached_exercises(current_level)
    exercise = next((e for e in exercises if e['id'] == exercise_id), None)
    
    if not exercise:
        await query.edit_message_text("❌ Error al cargar el ejercicio.")
        return
    
    correct_answer = exercise['correct_answer']
    is_correct = answer_index == correct_answer
    
    # Update practice session (no XP)
    if telegram_id not in user_sessions or 'practice_session' not in user_sessions[telegram_id]:
        await query.edit_message_text("❌ Sesión de práctica no encontrada. Por favor inicia una nueva sesión.")
        return
    
    session = user_sessions[telegram_id]['practice_session']
    session['completed_count'] += 1
    if is_correct:
        session['correct_count'] += 1
    
    # Format response
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    if is_correct:
        response_text = "✅ *¡Correcto!*\n\n"
    else:
        response_text = f"❌ *Incorrecto.*\n\n"
        response_text += f"La respuesta correcta es: {options[correct_answer]}\n\n"
    
    if exercise.get('explanation'):
        response_text += f"💡 *Explicación:*\n{exercise['explanation']}\n\n"
    
    # Practice session progress
    unlimited = session.get('unlimited', False)
    progress_text = f"{session['completed_count']}/∞" if unlimited else f"{session['completed_count']}/{session['target_count']}"
    accuracy = f"{(session['correct_count']/session['completed_count']*100):.0f}%" if session['completed_count'] > 0 else "0%"
    
    response_text += f"\n📊 *Sesión de Práctica:* {progress_text} ejercicios\n✅ *Precisión:* {accuracy}\n\n"
    
    # Check if practice session is complete (only for limited sessions)
    if not unlimited and session['completed_count'] >= session['target_count']:
        await complete_practice_session(query, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_practice_exercise")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def complete_practice_session(query, context):
    """Complete practice session handler"""
    telegram_id = query.from_user.id
    
    if telegram_id not in user_sessions or 'practice_session' not in user_sessions[telegram_id]:
        await query.edit_message_text("❌ No hay sesión de práctica activa.")
        return
    
    session = user_sessions[telegram_id]['practice_session']
    
    completion_text = f"""
🎉 *¡Sesión de Práctica Completada!*\n\n📊 *Resultados:*\n• Ejercicios realizados: {session['completed_count']}\n• Respuestas correctas: {session['correct_count']}\n• Precisión: {(session['correct_count']/max(1, session['completed_count'])*100):.0f}%\n\n📚 *Recuerda:* Estos ejercicios no afectaron tu nivel de progreso.\n\n¿Qué te gustaría hacer ahora?
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Nueva Sesión", callback_data="practice_menu")],
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        completion_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def next_practice_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get next practice exercise"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    # Check if user has active practice session
    if telegram_id not in user_sessions or user_sessions[telegram_id].get('mode') != 'practice':
        await practice_menu(update, context)
        return
    
    session = user_sessions[telegram_id]['practice_session']
    unlimited = session.get('unlimited', False)
    
    # Check if practice session is complete (for limited sessions)
    if not unlimited and session['completed_count'] >= session['target_count']:
        if update.callback_query:
            await complete_practice_session(update.callback_query, context)
        else:
            await complete_practice_session(update, context)
        return
    
    # Get exercises from cache
    current_level = user_sessions[telegram_id]['current_level']
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await reply_func(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['practice_session']['current_exercise'] = exercise
    
    # Format practice exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    progress_text = f"{session['completed_count']}/∞" if unlimited else f"{session['completed_count']}/{session['target_count']}"
    accuracy = f"{(session['correct_count']/max(1, session['completed_count'])*100):.0f}%" if session['completed_count'] > 0 else "0%"
    
    exercise_text = f"""
📝 *Modo Práctica - Nivel {current_level.title()}*

{question}

📊 *Sesión de Práctica:* {progress_text} ejercicios
✅ *Precisión:* {accuracy}

📚 *Recuerda:* Este modo no afecta tu nivel de progreso

🔘 *Opciones:*
"""
    
    keyboard = []
    for i, option in enumerate(options):
        exercise_text += f"{i+1}. {option}\n"
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {option}", 
            callback_data=f"practice_answer_{exercise['id']}_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("💡 Ver Explicación", callback_data=f"explanation_{exercise['id']}")])
    keyboard.append([InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_practice_exercise")])
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def next_learning_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get next learning exercise"""
    if update.callback_query:
        await update.callback_query.answer()
        telegram_id = update.callback_query.from_user.id
        message = update.callback_query.message
        reply_func = message.reply_text
    else:
        telegram_id = update.effective_user.id
        message = update.message
        reply_func = message.reply_text
    
    # Check if user has active learning session
    if telegram_id not in user_sessions or user_sessions[telegram_id].get('mode') != 'learning':
        await learning_mode(update, context)
        return
    
    # Get exercises from cache
    current_level = user_sessions[telegram_id]['current_level']
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await reply_func(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['learning_session']['current_exercise_data'] = exercise
    
    # Format learning exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    session = user_sessions[telegram_id]['learning_session']
    user_data = get_user_from_supabase(telegram_id)
    level_progress = user_data.get('level_progress', 0) if user_data else 0
    progress_bar = create_progress_bar(level_progress, 50)
    streak = session.get('streak', 0)
    
    exercise_text = f"""
🎯 *Lección del Día - Nivel {current_level.title()}*

{question}

📊 *Progreso del Nivel:* {progress_bar} {level_progress}/50
🔥 *Racha Actual:* {streak} ejercicios seguidos

🔘 *Opciones:*
"""
    
    keyboard = []
    for i, option in enumerate(options):
        exercise_text += f"{i+1}. {option}\n"
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {option}", 
            callback_data=f"learning_answer_{exercise['id']}_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("💡 Ver Explicación", callback_data=f"explanation_{exercise['id']}")])
    keyboard.append([InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_learning_exercise")])
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await reply_func(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def explanation_callback(query, context, exercise_id):
    """Handle explanation callback"""
    telegram_id = query.from_user.id
    
    # Get exercises from cache
    current_level = user_sessions.get(telegram_id, {}).get('current_level', 'principiante')
    exercises = get_cached_exercises(current_level)
    exercise = next((e for e in exercises if e['id'] == exercise_id), None)
    
    if not exercise or not exercise.get('explanation'):
        await query.answer("No hay explicación disponible para este ejercicio.")
        return
    
    explanation_text = f"💡 *Explicación:*\n\n{exercise['explanation']}"
    
    await query.answer(explanation_text, show_alert=True)

# Helper functions for progression system
def check_and_update_level(telegram_id, user_data):
    """Check if user should level up and update their level"""
    total_completed = user_data.get('total_exercises_completed', 0)
    current_level = user_data.get('current_level', 'principiante')
    
    # Check each level requirement
    for level in LEVELS:
        if total_completed >= LEVEL_REQUIREMENTS[level]:
            if LEVELS.index(level) > LEVELS.index(current_level) if current_level in LEVELS else 0:
                # User should level up
                return level
    
    # Check if user should be graduated
    if total_completed >= LEVEL_REQUIREMENTS['graduado']:
        return 'graduado'
    
    return current_level

def get_next_level_info(current_level, total_completed):
    """Get information about next level unlock"""
    if current_level == 'graduado':
        return "🎓 *¡Felicidades! Ya eres un graduado de PythonBot!*"
    
    # Find next level
    current_index = LEVELS.index(current_level) if current_level in LEVELS else -1
    if current_index < len(LEVELS) - 1:
        next_level = LEVELS[current_index + 1]
        required = LEVEL_REQUIREMENTS[next_level]
        remaining = max(0, required - total_completed)
        
        if remaining == 0:
            return f"🎉 *¡{next_level.title()} desbloqueado! Usa /practice para comenzar."
        else:
            return f"🔓 *Siguiente Nivel:* {next_level.title()}\n📝 *Necesitas:* {remaining} ejercicios más"
    
    return ""

def create_progress_bar(current, total, length=10):
    """Create a text progress bar"""
    if total == 0:
        return "□" * length
    
    filled = int((current / total) * length)
    empty = length - filled
    
    return "■" * filled + "□" * empty

def get_user_achievements(user_data):
    """Get user achievements based on their progress"""
    achievements = []
    total_completed = user_data.get('total_exercises_completed', 0)
    
    # Milestone achievements
    if total_completed >= 1:
        achievements.append("🌟 Primer Ejercicio")
    if total_completed >= 10:
        achievements.append("🔥 10 Ejercicios")
    if total_completed >= 50:
        achievements.append("🌿 Nivel Intermedio")
    if total_completed >= 100:
        achievements.append("💯 Centenario")
    if total_completed >= 150:
        achievements.append("🚀 Nivel Avanzado")
    if total_completed >= 300:
        achievements.append("👑 Nivel Experto")
    if total_completed >= 500:
        achievements.append("🎓 Graduado")
    
    return "\n".join(f"• {achievement}" for achievement in achievements) if achievements else "• 🎯 Sin logros aún"

def get_next_objectives(current_level, total_completed):
    """Get next objectives for the user"""
    objectives = []
    
    # Next milestone
    milestones = [10, 25, 50, 100, 150, 200, 300, 500]
    next_milestone = next((m for m in milestones if m > total_completed), None)
    if next_milestone:
        objectives.append(f"📝 Alcanzar {next_milestone} ejercicios")
    
    # Level specific objectives
    if current_level == 'principiante':
        objectives.append("🌱 Desbloquear nivel Intermedio")
    elif current_level == 'intermedio':
        objectives.append("🌿 Desbloquear nivel Avanzado")
    elif current_level == 'avanzado':
        objectives.append("🚀 Desbloquear nivel Experto")
    elif current_level == 'experto':
        objectives.append("👑 Convertirte en Graduado")
    
    return "\n".join(f"• {obj}" for obj in objectives)

async def celebrate_level_up(query, old_level, new_level):
    """Celebrate when user levels up"""
    celebration_text = f"""
🎉 *¡FELICIDADES! 🎉*

¡Has subido de nivel!

🌱 {old_level.title()} → 🌿 {new_level.title()}

🎯 *Nuevo desbloqueado:*
• Ejercicios más desafiantes
• Nuevos logros por descubrir
• Mayor reconocimiento en el ranking

📝 *¡Usa /practice para comenzar en tu nuevo nivel!*

¡Sigue así! 🚀
    """
    
    keyboard = [
        [InlineKeyboardButton("🎉 ¡Comenzar Ya!", callback_data="practice_menu")],
        [InlineKeyboardButton("📊 Ver Progreso", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        celebration_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def calculate_completion_percentage(telegram_id):
    """Calculate overall completion percentage"""
    try:
        # Get total exercises count from Supabase
        result = supabase.table('exercises').select('count', count='exact').execute()
        total_exercises = result.count if hasattr(result, 'count') else 1200
        
        # Get user's completed exercises
        user_data = get_user_from_supabase(telegram_id)
        completed = user_data.get('total_exercises_completed', 0) if user_data else 0
        
        percentage = (completed / total_exercises) * 100 if total_exercises > 0 else 0
        return f"{percentage:.1f}"
    except Exception as e:
        logger.error(f"Error calculating completion percentage: {e}")
        return "0.0"

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    logger.info("Received shutdown signal, stopping bot...")
    sys.exit(0)

# Main function
def main():
    """Start the bot"""
    logger.info("=" * 50)
    logger.info("Starting PythonBot with Health Check Server")
    logger.info(f"WEB_API_URL: {WEB_API_URL}")
    logger.info(f"Health check port: {os.getenv('PORT', 10001)}")
    logger.info("=" * 50)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("practice", practice_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("ranking", ranking_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("menu", main_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("PythonBot is now running and polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()