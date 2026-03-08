# 🤖 Bot Service - Python Tutor Bot

Servicio del bot Telegram para el sistema de aprendizaje de Python con control de estado, sistema de progresión y monitoreo de salud.

## 📋 Tabla de Contenidos

- [🎯 Características](#características)
- [🏗️ Arquitectura](#arquitectura)
- [🚀 Inicio Rápido](#inicio-rápido)
- [📋 Prerrequisitos](#prerrequisitos)
- [🔧 Configuración](#configuración)
- [🤖 Comandos del Bot](#comandos-del-bot)
- [🌐 Endpoints de API](#endpoints-de-api)
- [📊 Gestión de Estado](#gestión-de-estado)
- [🚨 Manejo de Errores](#manejo-de-errores)
- [🚀 Despliegue](#despliegue)
- [🧪 Pruebas](#pruebas)
- [🐛 Solución de Problemas](#solución-de-problemas)

## 🎯 Características

### 🎮 Funcionalidades del Bot
- **📚 Modo de Aprendizaje**: Lecciones interactivas de Python
- **💪 Modo de Práctica**: Ejercicios con diferentes niveles de dificultad
- **📈 Sistema de Progresión**: 4 niveles (principiante → experto)
- **⭐ Sistema de XP**: Puntos de experiencia y rachas
- **🏆 Rankings**: Tabla de posiciones global
- **📊 Estadísticas**: Progreso personal y logros

### 🎛️ Control Administrativo
- **✅ Estado Activo**: Funcionamiento normal completo
- **⏸️ Estado Pausado**: Detiene temporalmente las interacciones
- **🛠️ Estado Mantenimiento**: Permite registro con funciones limitadas
- **🔄 Estado Reiniciando**: Transición durante reinicio
- **🔴 Estado Detenido**: Bloquea completamente el acceso

### 🌐 Salud y Monitoreo
- **Health Check Server**: Endpoint `/health` para monitoreo
- **Estado del Bot**: Endpoint `/status` para panel de administración
- **Control Remoto**: Endpoint `/control` para comandos admin
- **Logging Completo**: Registro detallado de todas las operaciones

## 🏗️ Arquitectura

```
bot-service/
├── 📄 bot.py              # Lógica principal del bot
├── 📋 requirements.txt    # Dependencias Python
└── ⚙️ render-bot.yaml    # Configuración Render
```

### Flujo de Arquitectura
```
Usuario Telegram 
    ↓
Telegram Bot API
    ↓
python-telegram-bot
    ↓
Bot Logic (bot.py)
    ↓
┌─────────────────┬─────────────────┐
│   Web Service   │   Supabase DB   │
│      API        │     Datos       │
└─────────────────┴─────────────────┘
```

### Componentes Principales
- **Bot Handlers**: Manejadores de comandos y callbacks
- **State Management**: Gestión de estado global del bot
- **Health Server**: Servidor Flask para monitoreo
- **Database Integration**: Conexión con Supabase
- **Error Handling**: Manejo robusto de errores

## 🚀 Inicio Rápido

### 1. Instalar Dependencias
```bash
cd bot-service
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno
```bash
# Crear archivo .env
cp .env.example .env

# Editar configuración
nano .env
```

### 3. Iniciar el Bot
```bash
python bot.py
```

### 4. Verificar Funcionamiento
```bash
# Health check
curl http://localhost:10001/health

# Estado del bot
curl http://localhost:10001/status
```

## 📋 Prerrequisitos

### 🔧 Software Requerido
- **Python 3.8+**: Versión mínima requerida
- **pip**: Gestor de paquetes Python
- **Cuenta Supabase**: Base de datos configurada
- **Bot Telegram**: Token válido y activo

### 📦 Dependencias Python
```txt
Flask==2.3.3
flask-login==0.6.3
flask-cors==4.0.0
supabase==1.0.4
python-dotenv==1.0.0
werkzeug==2.3.7
gunicorn==21.2.0
python-telegram-bot==20.6
requests==2.31.0
```

## 🔧 Configuración

### Variables de Entorno
```bash
# .env file
TELEGRAM_BOT_TOKEN=tu_token_de_bot_aqui
WEB_API_URL=http://localhost:5000
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
PORT=10001
```

### Configuración Detallada

#### `TELEGRAM_BOT_TOKEN`
- Token proporcionado por @BotFather
- Formato: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
- **Obligatorio**: Sin este token el bot no puede funcionar

#### `WEB_API_URL`
- URL del servicio web de administración
- Para desarrollo: `http://localhost:5000`
- Para producción: `https://tu-web-service.onrender.com`

#### `SUPABASE_URL` y `SUPABASE_KEY`
- Credenciales de tu proyecto Supabase
- URL: `https://tu-proyecto.supabase.co`
- Key: Tu clave pública o anónima

#### `PORT`
- Puerto para el health check server
- Default: `10001`
- Debe ser diferente del puerto del servicio web

## 🤖 Comandos del Bot

### 📋 Comandos Principales
```bash
/start          - Iniciar sesión y crear perfil
/help           - Mostrar menú de ayuda
/learning       - Modo de aprendizaje
/practice       - Modo de práctica
/ranking        - Ver tabla de posiciones
/stats          - Ver estadísticas personales
```

### 🎮 Modos de Interacción

#### Modo Aprendizaje
- Lecciones estructuradas por nivel
- Explicaciones detalladas
- Progresión secuencial

#### Modo Práctica
- Ejercicios interactivos
- Opción múltiple
- Retroalimentación inmediata

### 📊 Sistema de Progresión
```
Principiante (0-50 ejercicios)
    ↓
Intermedio (51-150 ejercicios)
    ↓
Avanzado (151-300 ejercicios)
    ↓
Experto (300+ ejercicios)
```

## 🌐 Endpoints de API

### Health Check Endpoints

#### `GET /health`
```json
{
  "status": "ok",
  "service": "pythontutor-bot",
  "bot_running": true
}
```
- Propósito: Verificación básica de salud
- Uso: Load balancers, monitoreo
- Response: Simple estado del servicio

#### `GET /status`
```json
{
  "status": "success",
  "bot_status": "active",
  "message": "Bot is running normally",
  "last_updated": "2024-01-01T12:00:00",
  "service": "pythontutor-bot"
}
```
- Propósito: Estado detallado del bot
- Uso: Panel de administración
- Response: Estado completo con metadata

#### `POST /control`
```json
// Request
{
  "command": "start",
  "message": "Bot started by admin"
}

// Response
{
  "status": "success",
  "message": "Command executed successfully"
}
```
- Propósito: Control remoto del bot
- Uso: Panel de administración
- Comandos: `start`, `stop`, `pause`, `restart`, `maintenance`

## 📊 Gestión de Estado

### Estados del Bot
| Estado | Registro Usuarios | Funcionalidad Completa | Mensaje al Usuario |
|--------|-------------------|------------------------|-------------------|
| **active** | ✅ Permitido | ✅ Completa | Funcionamiento normal |
| **maintenance** | ✅ Permitido | ⚠️ Limitada | 🛠️ Modo mantenimiento |
| **restarting** | ✅ Permitido | ⚠️ Limitada | 🔄 Bot reiniciando |
| **paused** | ❌ Bloqueado | ❌ Ninguna | ⏸️ Bot en pausa |
| **stopped** | ❌ Bloqueado | ❌ Ninguna | 🔴 Bot detenido |
| **inactive** | ❌ Bloqueado | ❌ Ninguna | 💤 Bot inactivo |

### Transiciones de Estado
```
inactive → active → paused → active
    ↓         ↓         ↓
  stopped ← maintenance ← restarting
```

### Control de Acceso
```python
# Decorador para acceso completo
@check_bot_status
async def full_access_command(update, context):
    # Solo funciona en estado 'active'
    pass

# Decorador para acceso limitado
@check_bot_access  
async def registration_command(update, context):
    # Funciona en 'active', 'maintenance', 'restarting'
    pass
```

## 🚨 Manejo de Errores

### Tipos de Errores

#### 🌐 Errores de Conexión
```python
# Error de conexión al servicio web
if not check_web_service_health():
    await update.message.reply_text(
        "❌ *Error de conexión*\n\n"
        "🔄 El servicio web no está disponible\n"
        "💡 Por favor intenta más tarde"
    )
```

#### 🗄️ Errores de Base de Datos
```python
# Error al crear usuario
if not create_user_in_api(user_data):
    await update.message.reply_text(
        "❌ *Error en la base de datos*\n\n"
        "🔄 No se pudo crear tu perfil\n"
        "💡 Por favor intenta de nuevo"
    )
```

#### 🤖 Errores del Bot
```python
# Error general del bot
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    await update.message.reply_text(
        "❌ *Error inesperado*\n\n"
        "🔄 Ocurrió un error interno\n"
        "💡 Por favor intenta más tarde"
    )
```

### Logging Completo
```python
# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
```

## 🚀 Despliegue

### 🏠 Desarrollo Local
```bash
# Iniciar bot localmente
cd bot-service
python bot.py

# Verificar funcionamiento
curl http://localhost:10001/health
```

### ☁️ Render
1. **Crear Nuevo Servicio**:
   - Tipo: Web Service
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`

2. **Configurar Variables**:
   - Añadir todas las variables de entorno
   - Verificar token del bot
   - Configurar URL del servicio web

3. **Health Check**:
   - Health Check Path: `/health`
   - Auto-deploy: Activar

### 🐳 Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 10001

CMD ["python", "bot.py"]
```

## 🧪 Pruebas

### 📋 Scripts de Prueba
```bash
# Ejecutar pruebas de control del bot
python ../test_bot_control.py

# Ejecutar pruebas de registro
python ../test_user_registration.py
```

### 🧪 Pruebas Manuales
```bash
# 1. Probar health check
curl http://localhost:10001/health

# 2. Probar estado del bot
curl http://localhost:10001/status

# 3. Probar control del bot
curl -X POST http://localhost:10001/control \
  -H "Content-Type: application/json" \
  -d '{"command": "status"}'

# 4. Probar bot en Telegram
# Enviar /start a tu bot en Telegram
```

## 🐛 Solución de Problemas

### 🚨 Problemas Comunes

#### Bot no responde
```bash
# Verificar token
echo $TELEGRAM_BOT_TOKEN

# Verificar conexión
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe

# Revisar logs
python bot.py 2>&1 | tee bot.log
```

#### Error de conexión a base de datos
```bash
# Verificar credenciales Supabase
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Probar conexión
curl -H "apikey: $SUPABASE_KEY" \
  "$SUPABASE_URL/rest/v1/users?select=*"
```

#### Health check falla
```bash
# Verificar puerto
netstat -tlnp | grep 10001

# Probar localmente
curl http://localhost:10001/health

# Revisar logs del servidor Flask
grep -i flask bot.log
```

### 📊 Monitoreo

#### Logs Importantes
```bash
# Logs del bot
grep "ERROR\|WARNING" bot.log

# Logs de estado
grep "bot_status" bot.log

# Logs de usuarios
grep "User.*started" bot.log
```

#### Métricas Clave
- Usuarios activos por hora
- Ejercicios completados
- Errores de conexión
- Tiempo de respuesta

---

## 📞 Soporte

### 🆘 Ayuda Rápida
- **Bot no responde**: Verificar token y conexión
- **Error de base de datos**: Revisar credenciales Supabase
- **Health check falla**: Verificar puerto y logs

### 📚 Documentación Relacionada
- [README General](../README.md)
- [Web Service README](../web-service/README.md)
- [Documentación Telegram Bot API](https://core.telegram.org/bots/api)

---

<div align="center">
  <p>🤖 Servicio del Bot Python Tutor</p>
  <p>⚡ Potenciado por python-telegram-bot + Flask</p>
</div>
