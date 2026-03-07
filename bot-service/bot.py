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
from flask import Flask, jsonify
from datetime import datetime, timedelta

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
required_env_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'TELEGRAM_BOT_TOKEN', 'WEB_API_URL']
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
except Exception as e:
    logger.error(f"Supabase connection error: {e}")
    sys.exit(1)

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEB_API_URL = os.getenv('WEB_API_URL')

# User session storage (en memoria, se perderá al reiniciar)
user_sessions = {}

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
    exercises = get_exercises_from_api(level)
    exercise_cache[level] = exercises
    cache_timestamp[level] = datetime.now()
    logger.info(f"Exercise cache refreshed for level: {level}")
    return exercises

def get_cached_exercises(level):
    """Obtener ejercicios desde cache con timeout"""
    from datetime import timedelta
    
    # Verificar si cache existe y no está expirada (30 minutos)
    if level not in exercise_cache or \
       datetime.now() - cache_timestamp[level] > timedelta(minutes=30):
        return refresh_exercises_cache(level)
    
    return exercise_cache[level]

def invalidate_exercises_cache():
    """Invalidar toda la cache de ejercicios"""
    global exercise_cache, cache_timestamp
    exercise_cache.clear()
    cache_timestamp.clear()
    logger.info("Exercise cache invalidated")

# API functions
def get_user_from_api(telegram_id):
    """Obtener usuario desde la API del web service"""
    try:
        logger.info(f"Attempting to connect to API: {WEB_API_URL}/api/user/{telegram_id}")
        response = requests.get(f"{WEB_API_URL}/api/user/{telegram_id}", timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Successfully retrieved user {telegram_id}")
            return response.json()
        elif response.status_code == 404:
            logger.info(f"User {telegram_id} not found, will create new user")
            return None
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to API at {WEB_API_URL}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"API connection timeout for user {telegram_id}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting user: {e}")
        return None

def create_user_in_api(user_data):
    """Crear usuario en la API del web service"""
    try:
        logger.info(f"Creating user with data: {user_data}")
        response = requests.post(f"{WEB_API_URL}/api/user", json=user_data, timeout=10)
        
        if response.status_code == 201:
            logger.info(f"Successfully created user {user_data['telegram_id']}")
            return response.json()
        else:
            logger.error(f"Failed to create user: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to API at {WEB_API_URL} for user creation")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"API timeout during user creation")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        return None

def get_exercises_from_api(level):
    """Obtener ejercicios desde la API del web service"""
    try:
        response = requests.get(f"{WEB_API_URL}/api/exercises/{level}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API get_exercises error: {response.status_code}")
            return []
    except requests.RequestException as e:
        logger.error(f"API connection error: {e}")
        return []

def update_progress_in_api(telegram_id, exercise_id, completed):
    """Actualizar progreso en la API del web service"""
    try:
        response = requests.post(
            f"{WEB_API_URL}/api/user/progress",
            json={
                'telegram_id': telegram_id,
                'exercise_id': exercise_id,
                'completed': completed
            },
            timeout=10
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"API connection error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler - Enhanced with Duolingo-style interface"""
    user = update.effective_user
    telegram_id = user.id
    
    # Check if user exists in database
    user_data = get_user_from_api(telegram_id)
    
    if not user_data:
        # Create new user
        new_user = {
            'telegram_id': telegram_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'current_level': 'principiante',
            'level_progress': 0,
            'total_exercises_completed': 0,
            'last_activity': 'now()'
        }
        
        created_user = create_user_in_api(new_user)
        if created_user:
            user_data = created_user
        else:
            # Fallback: Create user in memory if API fails
            logger.warning(f"API failed, creating user {telegram_id} in memory as fallback")
            user_data = {
                'telegram_id': telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'current_level': 'principiante',
                'level_progress': 0,
                'total_exercises_completed': 0,
                'last_activity': 'now()'
            }
            
            await update.message.reply_text(
                "⚠️ El servicio está temporalmente no disponible, pero puedes continuar usando el bot.\n\n"
                "� Tu perfil ha sido creado localmente.\n"
                "� Se sincronizará cuando el servicio esté disponible."
            )
    
    # Check and update level based on progress
    updated_level = check_and_update_level(telegram_id, user_data)
    if updated_level != user_data.get('current_level'):
        user_data['current_level'] = updated_level
    
    # Initialize user session with Duolingo-style structure
    user_sessions[telegram_id] = {
        'current_level': user_data.get('current_level', 'principiante'),
        'mode': None,  # 'learning' or 'practice'
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
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")],
        [InlineKeyboardButton("🏆 Ranking Mundial", callback_data="world_ranking")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler - Updated for progression system"""
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
        [InlineKeyboardButton("📝 Modo Práctica", callback_data="practice_mode")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")],
        [InlineKeyboardButton("🏆 Ranking Mundial", callback_data="world_ranking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def learning_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Learning mode handler - XP-earning progression mode"""
    telegram_id = update.effective_user.id
    
    # Check if user exists
    user_data = get_user_from_api(telegram_id)
    if not user_data:
        await update.message.reply_text(
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
        await celebrate_level_up(update, user_data.get('current_level'), updated_level)
        return
    
    current_level = user_data.get('current_level', 'principiante')
    level_progress = user_data.get('level_progress', 0)
    total_completed = user_data.get('total_exercises_completed', 0)
    
    # Get exercises from cache
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await update.message.reply_text(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    import random
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
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Practice command handler - Redirect to practice menu"""
    await practice_menu(update, context)

async def practice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Practice menu handler - Choose practice session size"""
    telegram_id = update.effective_user.id
    
    # Check if user exists
    user_data = get_user_from_api(telegram_id)
    if not user_data:
        await update.message.reply_text(
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
    
    await update.message.reply_text(
        practice_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def setup_practice(update: Update, context: ContextTypes.DEFAULT_TYPE, target_count):
    """Setup practice session handler"""
    telegram_id = update.effective_user.id
    
    # Check if user exists
    user_data = get_user_from_api(telegram_id)
    if not user_data:
        await update.message.reply_text(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    current_level = user_data.get('current_level', 'principiante')
    
    # Initialize practice session
    if telegram_id not in user_sessions:
        user_sessions[telegram_id] = {}
    
    user_sessions[telegram_id]['mode'] = 'practice'
    user_sessions[telegram_id]['practice_session'] = {
        'target_count': target_count,
        'completed_count': 0,
        'correct_count': 0,
        'current_exercise': None
    }
    
    # Get exercises from cache
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await update.message.reply_text(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get first exercise
    import random
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['practice_session']['current_exercise'] = exercise
    user_sessions[telegram_id]['current_level'] = current_level
    
    # Format practice exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    session = user_sessions[telegram_id]['practice_session']
    progress_text = f"{session['completed_count']}/{session['target_count']}"
    accuracy = f"{(session['correct_count']/max(1, session['completed_count'])*100):.0f}%" if session['completed_count'] > 0 else "0.0%"
    
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
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def ranking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ranking command handler - Global leaderboard"""
    telegram_id = update.effective_user.id
    
    # Check if user exists
    user_data = get_user_from_api(telegram_id)
    if not user_data:
        await update.message.reply_text(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    await update.message.reply_text(
        "🏆 *Cargando Ranking Mundial...*\n\n⏳ Obteniendo datos de todos los usuarios...",
        parse_mode='Markdown'
    )
    
    # Get global ranking data
    ranking_data = get_global_ranking()
    
    if not ranking_data:
        await update.message.reply_text(
            "❌ No se pudo cargar el ranking. Por favor intenta más tarde."
        )
        return
    
    # Find user's position
    user_position = next((i+1 for i, user in enumerate(ranking_data) if user['telegram_id'] == telegram_id), None)
    
    ranking_text = "🏆 *Ranking Mundial de PythonBot*\n\n"
    
    # Show top 10 users
    for i, user_rank in enumerate(ranking_data[:10]):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        
        # Highlight current user
        if user_rank['telegram_id'] == telegram_id:
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
    ranking_text += "🔄 Ranking actualizado cada hora"
    
    keyboard = [
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_mode")],
        [InlineKeyboardButton("📊 Mis Estadísticas", callback_data="view_stats")],
        [InlineKeyboardButton("🔄 Actualizar Ranking", callback_data="refresh_ranking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        ranking_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show progress command handler"""
    telegram_id = update.effective_user.id
    
    user_data = get_user_from_api(telegram_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ No se encontró tu perfil. Por favor usa /start para crear uno."
        )
        return
    
    progress_text = f"""
📊 *Tu Progreso*

👤 *Usuario:* {user_data.get('first_name', 'N/A')}
📚 *Nivel Actual:* {user_data.get('current_level', 'principiante').title()}
📈 *Progreso del Nivel:* {user_data.get('level_progress', 0)} ejercicios
🏆 *Total Completados:* {user_data.get('total_exercises_completed', 0)} ejercicios
🕐 *Última Actividad:* {user_data.get('last_activity', 'N/A')}

🎯 *Siguiente Nivel:* {get_next_level(user_data.get('current_level', 'principiante'))}
    """
    
    keyboard = [
        [InlineKeyboardButton("📝 Practicar Ejercicios", callback_data="start_learning")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        progress_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics command handler - Enhanced with progression info"""
    telegram_id = update.effective_user.id
    
    user_data = get_user_from_api(telegram_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ No se encontró tu perfil. Por favor usa /start para crear uno."
        )
        return
    
    # Check and update level based on progress
    updated_level = check_and_update_level(telegram_id, user_data)
    if updated_level != user_data.get('current_level'):
        user_data['current_level'] = updated_level
    
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
• Racha Actual: 🔥 {get_current_streak(telegram_id)} días
• Ejercicios por Nivel:
  - 🌱 Principiante: {get_level_progress(telegram_id, 'principiante')}
  - 🌿 Intermedio: {get_level_progress(telegram_id, 'intermedio')}
  - 🚀 Avanzado: {get_level_progress(telegram_id, 'avanzado')}
  - 👑 Experto: {get_level_progress(telegram_id, 'experto')}

� *Próximos Objetivos:*
{get_next_objectives(current_level, total_completed)}
    """
    
    keyboard = [
        [InlineKeyboardButton("📝 Modo Práctica", callback_data="practice_mode")],
        [InlineKeyboardButton("🏆 Ver Ranking", callback_data="world_ranking")],
        [InlineKeyboardButton("📊 Progreso Detallado", callback_data="detailed_progress")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About command handler"""
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
• Base de datos en la nube
• API RESTful
• Machine Learning (próximamente)

👨‍💻 *Desarrollado por:*
Equipo PythonTutor

📧 *Contacto:*
• Web: pythontutor-web.onrender.com
• Bot: @PythonTutorBot

¡Aprende Python donde sea, cuando sea! 🚀
    """
    
    keyboard = [
        [InlineKeyboardButton("🌐 Visitar Web", url="https://pythontutor-web.onrender.com")],
        [InlineKeyboardButton("📝 Comenzar a Aprender", callback_data="start_learning")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        about_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# Callback query handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks - Fixed structure"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    data = query.data
    
    # Single if-elif chain for all callbacks
    if data == "learning_mode":
        await learning_mode(update, context)
    elif data == "practice_menu":
        await practice_menu(update, context)
    elif data.startswith("setup_practice_"):
        count = int(data.split("_")[2])
        await setup_practice(update, context, count)
    elif data == "main_menu":
        await main_menu(update, context)
    elif data == "view_stats":
        await stats_command(update, context)
    elif data == "world_ranking":
        await ranking_command(update, context)
    elif data == "refresh_ranking":
        await ranking_command(update, context)
    elif data == "detailed_progress":
        await progress_command(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "next_learning_exercise":
        await learning_mode(update, context)
    elif data.startswith("learning_answer_"):
        parts = data.split("_")
        exercise_id = int(parts[2])
        answer_index = int(parts[3])
        await learning_answer_callback(query, context, exercise_id, answer_index)
    elif data == "practice_mode":
        await practice_command(update, context)
    elif data == "next_practice_exercise":
        await next_practice_exercise(update, context)
    elif data.startswith("practice_answer_"):
        parts = data.split("_")
        exercise_id = int(parts[2])
        answer_index = int(parts[3])
        await practice_answer_callback(query, context, exercise_id, answer_index)
    elif data.startswith("answer_"):
        parts = data.split("_")
        exercise_id = int(parts[1])
        answer_index = int(parts[2])
        await answer_callback(query, context, exercise_id, answer_index)
    elif data.startswith("explanation_"):
        exercise_id = int(data.split("_")[1])
        await explanation_callback(query, context, exercise_id)
    # Legacy callbacks
    elif data == "start_learning":
        await learning_mode(update, context)
    elif data == "view_progress":
        await progress_command(update, context)
    elif data == "leaderboard":
        await ranking_command(update, context)

async def start_learning_callback(query, context):
    """Handle start learning callback"""
    telegram_id = query.from_user.id
    
    if telegram_id not in user_sessions:
        await query.edit_message_text(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    keyboard = []
    for level in LEVELS:
        keyboard.append([InlineKeyboardButton(
            f"📖 {level.title()}", 
            callback_data=f"change_level_{level}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📚 *Selecciona un nivel para comenzar:*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

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
    
    # Update progress (with XP)
    update_progress_in_api(telegram_id, exercise_id, is_correct)
    
    # Update learning session streak
    session = user_sessions[telegram_id]['learning_session']
    if is_correct:
        session['streak'] += 1
        session['completed_today'] += 1
        user_sessions[telegram_id]['score'] += 10
    else:
        session['streak'] = 0
    
    # Get updated user data to check for level up
    user_data = get_user_from_api(telegram_id)
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
    
    response_text += f"🏆 *Puntos:* {user_sessions[telegram_id]['score']} puntos"
    
    keyboard = [
        [InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_learning_exercise")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")],
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
    progress_text = f"{session['completed_count']}/{session['target_count']}"
    accuracy = f"{(session['correct_count']/session['completed_count']*100):.0f}%" if session['completed_count'] > 0 else "0.0%"
    
    response_text += f"\n📊 *Sesión de Práctica:* {progress_text} ejercicios\n✅ *Precisión:* {accuracy}\n\n"
    
    # Check if practice session is complete
    if session['completed_count'] >= session['target_count']:
        await complete_practice_session(query, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_practice_exercise")],
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")],
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
    
    session = user_sessions[telegram_id]['practice_session']
    
    completion_text = f"""
🎉 *¡Sesión de Práctica Completada!*\n\n📊 *Resultados:*\n• Ejercicios realizados: {session['completed_count']}/{session['target_count']}\n• Respuestas correctas: {session['correct_count']}\n• Precisión: {(session['correct_count']/session['completed_count']*100):.0f}%\n\n📚 *Recuerda:* Estos ejercicios no afectaron tu nivel de progreso.\n\n¿Qué te gustaría hacer ahora?\n    """
    
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
    telegram_id = update.effective_user.id
    
    # Check if user has active practice session
    if telegram_id not in user_sessions or user_sessions[telegram_id].get('mode') != 'practice':
        await practice_command(update, context)
        return
    
    session = user_sessions[telegram_id]['practice_session']
    
    # Check if practice session is complete
    if session['completed_count'] >= session['target_count']:
        await complete_practice_session(update, context)
        return
    
    # Get exercises from cache
    current_level = user_sessions[telegram_id]['current_level']
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await update.message.reply_text(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    import random
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['practice_session']['current_exercise'] = exercise
    
    # Format practice exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    progress_text = f"{session['completed_count']}/{session['target_count']}"
    accuracy = f"{(session['correct_count']/max(1, session['completed_count'])*100):.0f}%" if session['completed_count'] > 0 else "0.0%"
    
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
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def next_learning_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get next learning exercise"""
    telegram_id = update.effective_user.id
    
    # Check if user has active learning session
    if telegram_id not in user_sessions or user_sessions[telegram_id].get('mode') != 'learning':
        await learning_mode(update, context)
        return
    
    # Get exercises from cache
    current_level = user_sessions[telegram_id]['current_level']
    exercises = get_cached_exercises(current_level)
    
    if not exercises:
        await update.message.reply_text(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    import random
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['learning_session']['current_exercise_data'] = exercise
    
    # Format learning exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    session = user_sessions[telegram_id]['learning_session']
    user_data = get_user_from_api(telegram_id)
    progress_bar = create_progress_bar(user_data.get('level_progress', 0), 50)
    streak = session['streak']
    
    exercise_text = f"""
🎯 *Lección del Día - Nivel {current_level.title()}*

{question}

📊 *Progreso del Nivel:* {progress_bar} {user_data.get('level_progress', 0)}/50
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
    keyboard.append([InlineKeyboardButton("📊 Ver Estadísticas", callback_data="view_stats")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        exercise_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ranking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ranking command handler - Global leaderboard"""
    telegram_id = update.effective_user.id
    
    # Check if user exists
    user_data = get_user_from_api(telegram_id)
    if not user_data:
        await update.message.reply_text(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    await update.message.reply_text(
        "🏆 *Cargando Ranking Mundial...*\n\n⏳ Obteniendo datos de todos los usuarios...",
        parse_mode='Markdown'
    )
    
    # Get global ranking data
    ranking_data = get_global_ranking()
    
    if not ranking_data:
        await update.message.reply_text(
            "❌ No se pudo cargar el ranking. Por favor intenta más tarde."
        )
        return
    
    # Find user's position
    user_position = next((i+1 for i, user in enumerate(ranking_data) if user['telegram_id'] == telegram_id), None)
    
    ranking_text = "🏆 *Ranking Mundial de PythonBot*\n\n"
    
    # Show top 10 users
    for i, user_rank in enumerate(ranking_data[:10]):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        
        # Highlight current user
        if user_rank['telegram_id'] == telegram_id:
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
    ranking_text += "🔄 Ranking actualizado cada hora"
    
    keyboard = [
        [InlineKeyboardButton("🎯 Lección del Día", callback_data="learning_mode")],
        [InlineKeyboardButton("💪 Modo Práctica", callback_data="practice_menu")],
        [InlineKeyboardButton("🔄 Actualizar Ranking", callback_data="refresh_ranking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        ranking_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def explanation_callback(query, context, exercise_id):
    """Handle explanation callback"""
    # Get exercises from cache
    exercises = get_cached_exercises(user_sessions[query.from_user.id]['current_level'])
    exercise = next((e for e in exercises if e['id'] == exercise_id), None)
    
    if not exercise or not exercise.get('explanation'):
        await query.answer("No hay explicación disponible para este ejercicio.")
        return
    
    explanation_text = f"💡 *Explicación:*\n\n{exercise['explanation']}"
    
    await query.answer(explanation_text, show_alert=True)

async def leaderboard_callback(query, context):
    """Handle leaderboard callback"""
    # This would require a new API endpoint
    await query.edit_message_text(
        "🏆 *Leaderboard*\n\n"
        "📊 Función en desarrollo...\n\n"
        "¡Pronto podrás ver el ranking de usuarios!",
        parse_mode='Markdown'
    )

# Helper functions for progression system
def check_and_update_level(telegram_id, user_data):
    """Check if user should level up and update their level"""
    total_completed = user_data.get('total_exercises_completed', 0)
    current_level = user_data.get('current_level', 'principiante')
    
    # Check each level requirement
    for level in LEVELS:
        if total_completed >= LEVEL_REQUIREMENTS[level]:
            if LEVELS.index(level) > LEVELS.index(current_level):
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

def get_global_ranking():
    """Get global ranking data (mock implementation)"""
    # This would require a new API endpoint to get all users
    # For now, return mock data
    try:
        # Mock ranking data - replace with actual API call
        mock_ranking = [
            {'telegram_id': 12345, 'first_name': 'Alex', 'total_exercises_completed': 450},
            {'telegram_id': 67890, 'first_name': 'Maria', 'total_exercises_completed': 380},
            {'telegram_id': 11111, 'first_name': 'Carlos', 'total_exercises_completed': 320},
            {'telegram_id': 22222, 'first_name': 'Ana', 'total_exercises_completed': 280},
            {'telegram_id': 33333, 'first_name': 'Luis', 'total_exercises_completed': 250},
        ]
        return mock_ranking
    except Exception as e:
        logger.error(f"Error getting global ranking: {e}")
        return []

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
        [InlineKeyboardButton("🎉 ¡Comenzar Ya!", callback_data="practice_mode")],
        [InlineKeyboardButton("📊 Ver Progreso", callback_data="view_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        celebration_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def get_level_progress(telegram_id, level):
    """Get progress for a specific level"""
    try:
        response = requests.get(f"{WEB_API_URL}/api/user/progress/{telegram_id}/{level}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return f"{data.get('completed_count', 0)}/{data.get('total_count', 0)}"
        return "0/300"
    except requests.RequestException as e:
        logger.error(f"Error getting level progress: {e}")
        return "0/300"

def get_current_streak(telegram_id):
    """Get current streak"""
    try:
        response = requests.get(f"{WEB_API_URL}/api/user/stats/{telegram_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return str(data.get('current_streak', 0))
        return "0"
    except requests.RequestException as e:
        logger.error(f"Error getting current streak: {e}")
        return "0"

def calculate_completion_percentage(telegram_id):
    """Calculate overall completion percentage"""
    try:
        response = requests.get(f"{WEB_API_URL}/api/user/stats/{telegram_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total_exercises = 1200  # 4 levels x 300 exercises
            completed = data.get('total_completed', 0)
            percentage = (completed / total_exercises) * 100
            return f"{percentage:.1f}"
        return "0.0"
    except requests.RequestException as e:
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
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("PythonBot is now running and polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()