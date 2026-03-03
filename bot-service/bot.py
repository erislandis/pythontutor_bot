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

# Level order
LEVELS = ['principiante', 'intermedio', 'avanzado', 'experto']

# API functions
def get_user_from_api(telegram_id):
    """Obtener usuario desde la API del web service"""
    try:
        response = requests.get(f"{WEB_API_URL}/api/user/{telegram_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API get_user error: {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"API connection error: {e}")
        return None

def create_user_in_api(user_data):
    """Crear usuario en la API del web service"""
    try:
        response = requests.post(f"{WEB_API_URL}/api/user", json=user_data, timeout=10)
        if response.status_code == 201:
            return response.json()
        else:
            logger.error(f"API create_user error: {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"API connection error: {e}")
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
    """Start command handler"""
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
            await update.message.reply_text(
                "❌ Error al crear tu perfil. Por favor intenta más tarde."
            )
            return
    
    # Initialize user session
    user_sessions[telegram_id] = {
        'current_level': user_data.get('current_level', 'principiante'),
        'current_exercise': 0,
        'exercises_completed': [],
        'score': 0
    }
    
    welcome_text = f"""
🐍 ¡Bienvenido a PythonBot, {user.first_name}!

Soy tu tutor personal de Python. Te ayudaré a aprender programación con ejercicios interactivos.

📚 *Niveles disponibles:*
• Principiante
• Intermedio  
• Avanzado
• Experto

🎯 *Tu progreso actual:*
• Nivel: {user_data.get('current_level', 'principiante').title()}
• Ejercicios completados: {user_data.get('total_exercises_completed', 0)}

Usa /help para ver todos los comandos disponibles.
¡Comencemos a programar! 🚀
    """
    
    keyboard = [
        [InlineKeyboardButton("📚 Comenzar a Aprender", callback_data="start_learning")],
        [InlineKeyboardButton("📊 Ver Mi Progreso", callback_data="view_progress")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
🐍 *Comandos de PythonBot*

📚 *Aprendizaje:*
/start - Iniciar o reiniciar el bot
/level <nivel> - Cambiar de nivel (principiante/intermedio/avanzado/experto)
/exercise - Obtener un ejercicio aleatorio
/progress - Ver tu progreso

📊 *Estadísticas:*
/stats - Ver tus estadísticas generales
/leaderboard - Ver el ranking de usuarios

🎯 *Otros:*
/help - Mostrar este mensaje de ayuda
/about - Acerca de PythonBot

💡 *Tips:*
• Completa ejercicios para desbloquear nuevos niveles
• Cada nivel tiene 300 ejercicios únicos
• Tu progreso se guarda automáticamente
• Puedes cambiar de nivel cuando quieras

¿Listo para aprender Python? 🚀
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change level command handler"""
    telegram_id = update.effective_user.id
    
    if telegram_id not in user_sessions:
        await update.message.reply_text(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    if not context.args:
        keyboard = []
        for level in LEVELS:
            keyboard.append([InlineKeyboardButton(
                f"📖 {level.title()}", 
                callback_data=f"change_level_{level}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📚 *Selecciona un nivel:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    level = context.args[0].lower()
    if level not in LEVELS:
        await update.message.reply_text(
            "❌ Nivel no válido. Niveles disponibles: principiante, intermedio, avanzado, experto"
        )
        return
    
    user_sessions[telegram_id]['current_level'] = level
    user_sessions[telegram_id]['current_exercise'] = 0
    
    await update.message.reply_text(
        f"✅ Nivel cambiado a *{level.title()}*.\n"
        f"📝 Usa /exercise para obtener un ejercicio de este nivel.",
        parse_mode='Markdown'
    )

async def exercise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get exercise command handler"""
    telegram_id = update.effective_user.id
    
    if telegram_id not in user_sessions:
        await update.message.reply_text(
            "❌ Por favor usa /start para inicializar tu perfil primero."
        )
        return
    
    current_level = user_sessions[telegram_id]['current_level']
    
    # Get exercises from API
    exercises = get_exercises_from_api(current_level)
    
    if not exercises:
        await update.message.reply_text(
            "❌ No hay ejercicios disponibles en este nivel. Por favor intenta más tarde."
        )
        return
    
    # Get a random exercise
    import random
    exercise = random.choice(exercises)
    
    # Store current exercise in session
    user_sessions[telegram_id]['current_exercise_data'] = exercise
    
    # Format exercise
    question = exercise['question']
    options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
    
    exercise_text = f"""
📝 *Ejercicio - Nivel {current_level.title()}*

{question}

🔘 *Opciones:*
"""
    
    keyboard = []
    for i, option in enumerate(options):
        exercise_text += f"{i+1}. {option}\n"
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {option}", 
            callback_data=f"answer_{exercise['id']}_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("💡 Ver Explicación", callback_data=f"explanation_{exercise['id']}")])
    keyboard.append([InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_exercise")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        exercise_text,
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
    """Show statistics command handler"""
    telegram_id = update.effective_user.id
    
    user_data = get_user_from_api(telegram_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ No se encontró tu perfil. Por favor usa /start para crear uno."
        )
        return
    
    # Get exercises count per level
    stats_text = f"""
📊 *Estadísticas Detalladas*

👤 *Perfil:* {user_data.get('first_name', 'N/A')}
📱 *ID:* {user_data.get('telegram_id', 'N/A')}

📚 *Progreso por Niveles:*
• Principiante: {get_level_progress(telegram_id, 'principiante')}/300
• Intermedio: {get_level_progress(telegram_id, 'intermedio')}/300
• Avanzado: {get_level_progress(telegram_id, 'avanzado')}/300
• Experto: {get_level_progress(telegram_id, 'experto')}/300

🏆 *Logros:*
• Ejercicios Totales: {user_data.get('total_exercises_completed', 0)}
• Nivel Actual: {user_data.get('current_level', 'principiante').title()}
• Racha Actual: 🔥 {get_current_streak(telegram_id)} días

📈 *Porcentaje de Completion:*
{calculate_completion_percentage(telegram_id)}% del curso completado
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Continuar Aprendiendo", callback_data="start_learning")],
        [InlineKeyboardButton("📊 Ver Leaderboard", callback_data="leaderboard")]
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
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    data = query.data
    
    if data == "start_learning":
        await start_learning_callback(query, context)
    elif data == "view_progress":
        await progress_command(update, context)
    elif data == "view_stats":
        await stats_command(update, context)
    elif data.startswith("change_level_"):
        level = data.split("_")[2]
        await change_level_callback(query, context, level)
    elif data.startswith("answer_"):
        parts = data.split("_")
        exercise_id = int(parts[1])
        answer_index = int(parts[2])
        await answer_callback(query, context, exercise_id, answer_index)
    elif data.startswith("explanation_"):
        exercise_id = int(data.split("_")[1])
        await explanation_callback(query, context, exercise_id)
    elif data == "next_exercise":
        await exercise_command(update, context)
    elif data == "leaderboard":
        await leaderboard_callback(query, context)
    elif data == "help":
        await help_command(update, context)

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

async def change_level_callback(query, context, level):
    """Handle level change callback"""
    telegram_id = query.from_user.id
    
    if telegram_id not in user_sessions:
        user_sessions[telegram_id] = {}
    
    user_sessions[telegram_id]['current_level'] = level
    user_sessions[telegram_id]['current_exercise'] = 0
    
    await query.edit_message_text(
        f"✅ Nivel cambiado a *{level.title()}*.\n"
        f"📝 Presiona el botón para obtener tu primer ejercicio:",
        parse_mode='Markdown'
    )
    
    # Get first exercise
    await asyncio.sleep(1)
    await exercise_command(query, context)

async def answer_callback(query, context, exercise_id, answer_index):
    """Handle answer callback"""
    telegram_id = query.from_user.id
    
    # Get exercise from API
    exercises = get_exercises_from_api(user_sessions[telegram_id]['current_level'])
    exercise = next((e for e in exercises if e['id'] == exercise_id), None)
    
    if not exercise:
        await query.edit_message_text("❌ Error al cargar el ejercicio.")
        return
    
    correct_answer = exercise['correct_answer']
    is_correct = answer_index == correct_answer
    
    # Update progress
    update_progress_in_api(telegram_id, exercise_id, is_correct)
    
    if is_correct:
        response_text = "✅ *¡Correcto!*\n\n"
        user_sessions[telegram_id]['score'] += 10
    else:
        options = json.loads(exercise['options']) if isinstance(exercise['options'], str) else exercise['options']
        response_text = f"❌ *Incorrecto.*\n\n"
        response_text += f"La respuesta correcta es: {options[correct_answer]}\n\n"
    
    if exercise.get('explanation'):
        response_text += f"💡 *Explicación:*\n{exercise['explanation']}\n\n"
    
    response_text += f"🏆 *Puntuación:* {user_sessions[telegram_id]['score']} puntos"
    
    keyboard = [
        [InlineKeyboardButton("⏭️ Siguiente Ejercicio", callback_data="next_exercise")],
        [InlineKeyboardButton("📊 Ver Progreso", callback_data="view_progress")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def explanation_callback(query, context, exercise_id):
    """Handle explanation callback"""
    # Get exercise from API
    exercises = get_exercises_from_api(user_sessions[query.from_user.id]['current_level'])
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

# Helper functions
def get_next_level(current_level):
    """Get next level"""
    current_index = LEVELS.index(current_level)
    if current_index < len(LEVELS) - 1:
        return LEVELS[current_index + 1].title()
    return "¡Graduado!"

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
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("exercise", exercise_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("PythonBot is now running and polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()