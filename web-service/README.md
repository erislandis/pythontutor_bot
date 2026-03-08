# 🌐 Web Service - Python Tutor Bot

Servicio web de administración para el Python Tutor Bot con panel de control, gestión de usuarios y API REST para comunicación con el bot.

## 📋 Tabla de Contenidos

- [🎯 Características](#características)
- [🏗️ Arquitectura](#arquitectura)
- [🚀 Inicio Rápido](#inicio-rápido)
- [📋 Prerrequisitos](#prerrequisitos)
- [🔧 Configuración](#configuración)
- [👥 Panel de Administración](#panel-de-administración)
- [🔗 API Endpoints](#api-endpoints)
- [🔐 Sistema de Autenticación](#sistema-de-autenticación)
- [🗄️ Base de Datos](#base-de-datos)
- [📊 Estadísticas y Monitoreo](#estadísticas-y-monitoreo)
- [🛡️ Seguridad](#seguridad)
- [🚀 Despliegue](#despliegue)
- [🧪 Pruebas](#pruebas)
- [🐛 Solución de Problemas](#solución-de-problemas)

## 🎯 Características

### 🎛️ Panel de Administración
- **Control del Bot**: Iniciar, detener, pausar, reiniciar, mantenimiento
- **Estado en Tiempo Real**: Monitoreo del estado del bot
- **Gestión de Usuarios**: Ver y administrar usuarios registrados
- **Estadísticas**: Métricas de uso y progreso
- **Configuración**: Ajustes del sistema

### 📊 Gestión de Usuarios
- **Registro de Usuarios**: Creación automática de perfiles
- **Estadísticas Individuales**: Progreso y rendimiento
- **Niveles y XP**: Sistema de progresión completo
- **Rankings**: Tabla de posiciones global
- **Exportación de Datos**: CSV con estadísticas

### 🔌 API REST
- **Endpoints de Usuario**: Gestión completa de usuarios
- **Endpoints de Ejercicios**: Sistema de ejercicios por nivel
- **Endpoints de Control**: Comunicación con el bot
- **Endpoints de Estadísticas**: Datos analíticos
- **CORS Configurado**: Comunicación segura con el bot

### 🛡️ Seguridad
- **Autenticación de Admin**: Sistema de login seguro
- **Protección de Rutas**: Acceso restringido por rol
- **CSRF Protection**: Protección contra ataques CSRF
- **Session Management**: Gestión segura de sesiones

## 🏗️ Arquitectura

```
web-service/
├── 📄 app.py              # Aplicación Flask principal
├── 📁 templates/          # Plantillas HTML
│   ├── 📁 admin/         # Plantillas de administración
│   ├── 📁 auth/          # Plantillas de autenticación
│   └── 📁 public/        # Plantillas públicas
├── 📁 static/            # Archivos estáticos
│   ├── 📁 css/           # Estilos CSS
│   ├── 📁 js/            # JavaScript
│   └── 📁 img/           # Imágenes
├── 📋 requirements.txt   # Dependencias Python
└── ⚙️ render-web.yaml   # Configuración Render
```

### Flujo de Arquitectura
```
Admin Web Interface
    ↓
Flask Web Service (app.py)
    ↓
┌─────────────────┬─────────────────┐
│   Supabase DB   │   Bot Service   │
│     Datos       │    Control      │
└─────────────────┴─────────────────┘
```

### Componentes Principales
- **Flask Application**: Framework web principal
- **Authentication System**: Login y gestión de sesiones
- **API Routes**: Endpoints REST para el bot
- **Template Engine**: Jinja2 para renderizado HTML
- **Database Layer**: Integración con Supabase

## 🚀 Inicio Rápido

### 1. Instalar Dependencias
```bash
cd web-service
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno
```bash
# Crear archivo .env
cp .env.example .env

# Editar configuración
nano .env
```

### 3. Iniciar el Servicio
```bash
python app.py
```

### 4. Acceder al Panel
```
http://localhost:5000/admin/login
```

### 5. Verificar Funcionamiento
```bash
# Health check
curl http://localhost:5000/health

# API status
curl http://localhost:5000/api/admin/bot/status
```

## 📋 Prerrequisitos

### 🔧 Software Requerido
- **Python 3.8+**: Versión mínima requerida
- **pip**: Gestor de paquetes Python
- **Cuenta Supabase**: Base de datos configurada
- **Navegador Web**: Para acceder al panel admin

### 📦 Dependencias Python
```txt
Flask==2.3.3
flask-login==0.6.3
flask-cors==4.0.0
supabase==1.0.4
python-dotenv==1.0.0
werkzeug==2.3.7
gunicorn==21.2.0
Jinja2==3.1.2
```

## 🔧 Configuración

### Variables de Entorno
```bash
# .env file
SECRET_KEY=tu_clave_secreta_aqui
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
BOT_SERVICE_URL=http://localhost:10001
FLASK_ENV=development
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

### Configuración Detallada

#### `SECRET_KEY`
- Clave secreta para sesiones Flask
- Generar con: `python -c "import secrets; print(secrets.token_hex(32))"`
- **Obligatorio**: Sin esta clave la app no funciona

#### `SUPABASE_URL` y `SUPABASE_KEY`
- Credenciales de tu proyecto Supabase
- URL: `https://tu-proyecto.supabase.co`
- Key: Tu clave de servicio (no la anónima para admin)

#### `BOT_SERVICE_URL`
- URL del servicio del bot
- Para desarrollo: `http://localhost:10001`
- Para producción: `https://tu-bot-service.onrender.com`

#### Configuración de Sesiones
- `SESSION_COOKIE_SECURE`: `True` en producción (HTTPS)
- `SESSION_COOKIE_HTTPONLY`: Protección contra XSS
- `SESSION_COOKIE_SAMESITE`: Protección CSRF

## 👥 Panel de Administración

### 🏠 Dashboard Principal
```
/admin/dashboard
├── 📊 Estado del Bot
├── 👥 Usuarios Activos
├── 📈 Estadísticas
└── 🎛️ Controles Rápidos
```

### 🤖 Control del Bot
```
/admin/bot-control
├── 🔄 Estado en Tiempo Real
├── ▶️ Botones de Control
├── 📊 Métricas de Uso
└── ⚙️ Configuración
```

### 👥 Gestión de Usuarios
```
/admin/users
├── 📋 Lista de Usuarios
├── 📊 Estadísticas Individuales
├── 📈 Progresión por Nivel
└── 📤 Exportar Datos
```

### 📊 Estadísticas
```
/admin/stats
├── 📈 Métricas Generales
├── 🏆 Rankings
├── 📊 Gráficos de Progreso
└── 📋 Reportes Detallados
```

## 🔗 API Endpoints

### 🔐 Autenticación

#### `POST /admin/login`
```json
// Request
{
  "username": "admin",
  "password": "password"
}

// Response
{
  "status": "success",
  "message": "Login successful"
}
```

#### `POST /admin/logout`
```json
// Response
{
  "status": "success",
  "message": "Logout successful"
}
```

### 🤖 Control del Bot

#### `GET /api/admin/bot/status`
```json
{
  "status": "success",
  "bot_status": "active",
  "message": "Bot is running normally",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### `POST /api/admin/bot/start`
```json
// Request
{}

// Response
{
  "status": "success",
  "bot_status": "active",
  "message": "Bot started successfully",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### `POST /api/admin/bot/stop`
```json
// Request
{}

// Response
{
  "status": "success",
  "bot_status": "stopped",
  "message": "Bot stopped successfully",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### `POST /api/admin/bot/pause`
```json
// Request
{}

// Response
{
  "status": "success",
  "bot_status": "paused",
  "message": "Bot paused successfully",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### `POST /api/admin/bot/restart`
```json
// Request
{}

// Response
{
  "status": "success",
  "bot_status": "restarting",
  "message": "Bot is restarting...",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### `POST /api/admin/bot/maintenance`
```json
// Request
{}

// Response
{
  "status": "success",
  "bot_status": "maintenance",
  "message": "Maintenance mode activated",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 👥 Gestión de Usuarios

#### `GET /api/user/<telegram_id>`
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "usuario123",
  "first_name": "Juan",
  "last_name": "Pérez",
  "current_level": "intermedio",
  "level_progress": 75,
  "total_exercises_completed": 85,
  "current_streak": 5,
  "longest_streak": 12,
  "created_at": "2024-01-01T00:00:00",
  "last_activity": "2024-01-01T12:00:00"
}
```

#### `POST /api/user`
```json
// Request
{
  "telegram_id": 123456789,
  "username": "usuario123",
  "first_name": "Juan",
  "last_name": "Pérez",
  "current_level": "principiante",
  "level_progress": 0,
  "total_exercises_completed": 0,
  "current_streak": 0,
  "longest_streak": 0
}

// Response
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "usuario123",
  "first_name": "Juan",
  "last_name": "Pérez",
  "current_level": "principiante",
  "level_progress": 0,
  "total_exercises_completed": 0,
  "current_streak": 0,
  "longest_streak": 0,
  "created_at": "2024-01-01T12:00:00",
  "last_activity": "2024-01-01T12:00:00"
}
```

#### `POST /api/user/progress`
```json
// Request
{
  "telegram_id": 123456789,
  "exercise_id": 1,
  "completed": true,
  "level": "principiante"
}

// Response
{
  "status": "success",
  "message": "Progress updated successfully"
}
```

### 📚 Ejercicios

#### `GET /api/exercises/<level>`
```json
[
  {
    "id": 1,
    "level": "principiante",
    "question": "¿Cuál es la salida de print(2 + 3)?",
    "options": ["5", "6", "7", "Error"],
    "correct_answer": 0,
    "explanation": "El operador + suma los números 2 y 3",
    "difficulty": 1
  }
]
```

## 🔐 Sistema de Autenticación

### 👤 Usuarios Admin
- **Usuario por Defecto**: `admin` / `admin123`
- **Roles**: `admin` (acceso completo)
- **Sesiones**: 1 hora de duración
- **Seguridad**: Hash de contraseñas con Werkzeug

### 🔒 Protección de Rutas
```python
# Decorador para rutas admin
@login_required
def admin_route():
    # Requiere login
    pass

# Middleware para verificación de rol
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function
```

### 🍪 Gestión de Sesiones
- **Configuración Segura**: Cookies HTTPOnly y SameSite
- **Tiempo de Vida**: 1 hora de inactividad
- **Logout**: Limpieza completa de sesión
- **Recordar**: Opción de mantener sesión (opcional)

## 🗄️ Base de Datos

### 📋 Tablas Requeridas

#### `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    current_level TEXT DEFAULT 'principiante',
    level_progress INTEGER DEFAULT 0,
    total_exercises_completed INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW()
);
```

#### `exercises`
```sql
CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    level TEXT NOT NULL,
    question TEXT NOT NULL,
    options TEXT[],
    correct_answer INTEGER NOT NULL,
    explanation TEXT,
    difficulty INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `bot_status`
```sql
CREATE TABLE bot_status (
    id SERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'paused', 'stopped', 'maintenance', 'restarting')),
    last_updated TIMESTAMP DEFAULT NOW(),
    updated_by TEXT,
    message TEXT
);
```

### 🔗 Conexión Supabase
```python
# Configuración de Supabase
supabase: Client = create_client(
    supabase_url=os.getenv('SUPABASE_URL'),
    supabase_key=os.getenv('SUPABASE_KEY')
)
```

## 📊 Estadísticas y Monitoreo

### 📈 Métricas Disponibles
- **Usuarios Totales**: Número de usuarios registrados
- **Usuarios Activos**: Usuarios con actividad reciente
- **Ejercicios Completados**: Total de ejercicios resueltos
- **Progresión por Nivel**: Distribución de usuarios por nivel
- **Racha Promedio**: Estadísticas de streaks

### 📊 Reportes
- **Exportación CSV**: Datos de usuarios y progreso
- **Gráficos Interactivos**: Visualización de estadísticas
- **Filtros por Fecha**: Análisis temporal
- **Rankings**: Tabla de posiciones actualizada

### 🔄 Actualización en Tiempo Real
- **Estado del Bot**: Polling cada 5 segundos
- **Estadísticas**: Actualización automática
- **Notificaciones**: Alertas de cambios de estado

## 🛡️ Seguridad

### 🔒 Medidas de Seguridad
- **Autenticación**: Login seguro con hash de contraseñas
- **CSRF Protection**: Tokens CSRF en formularios
- **Session Security**: Cookies seguras y HTTPOnly
- **Input Validation**: Validación de datos de entrada
- **SQL Injection Protection**: Uso de Supabase (seguro por defecto)

### 🚨 Configuración de Seguridad
```python
# Configuración Flask de seguridad
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS en producción
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
```

### 🛡️ CORS Configuration
```python
# Configuración CORS para API
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Restringir en producción
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})
```

## 🚀 Despliegue

### 🏠 Desarrollo Local
```bash
# Iniciar servicio web
cd web-service
python app.py

# Acceder al panel
http://localhost:5000/admin/login
```

### ☁️ Render
1. **Crear Nuevo Servicio**:
   - Tipo: Web Service
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

2. **Configurar Variables**:
   - Añadir todas las variables de entorno
   - Configurar SECRET_KEY seguro
   - Establecer URLs de producción

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
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### 🌐 Nginx (Producción)
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
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
curl http://localhost:5000/health

# 2. Probar API de estado
curl http://localhost:5000/api/admin/bot/status

# 3. Probar login de admin
curl -X POST http://localhost:5000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 4. Probar creación de usuario
curl -X POST http://localhost:5000/api/user \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "username": "test", "first_name": "Test"}'
```

## 🐛 Solución de Problemas

### 🚨 Problemas Comunes

#### Error de login
```bash
# Verificar usuario admin
python -c "
from app import create_app, db
from werkzeug.security import check_password_hash
app = create_app()
with app.app_context():
    # Verificar si existe usuario admin
    pass
"

# Resetear contraseña admin
python -c "
from werkzeug.security import generate_password_hash
print('Nueva hash:', generate_password_hash('admin123'))
"
```

#### Error de conexión a Supabase
```bash
# Verificar credenciales
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Probar conexión
curl -H "apikey: $SUPABASE_KEY" \
  "$SUPABASE_URL/rest/v1/users?select=*&limit=1"
```

#### Error de CORS
```bash
# Verificar configuración CORS
curl -H "Origin: http://localhost:10001" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS http://localhost:5000/api/user
```

### 📊 Monitoreo y Logs

#### Logs de Flask
```bash
# Ver logs en tiempo real
python app.py 2>&1 | tee flask.log

# Filtrar errores
grep -i error flask.log

# Ver logs de API
grep "/api/" flask.log
```

#### Métricas de Rendimiento
- Tiempo de respuesta de API
- Uso de memoria
- Conexiones a base de datos
- Errores por hora

---

## 📞 Soporte

### 🆘 Ayuda Rápida
- **Login falla**: Verificar usuario admin y contraseña
- **API no responde**: Revisar logs de Flask
- **Base de datos**: Verificar credenciales Supabase
- **Bot no responde**: Comprobar BOT_SERVICE_URL

### 📚 Documentación Relacionada
- [README General](../README.md)
- [Bot Service README](../bot-service/README.md)
- [Documentación Flask](https://flask.palletsprojects.com/)
- [Documentación Supabase](https://supabase.com/docs)

---

<div align="center">
  <p>🌐 Servicio Web de Administración</p>
  <p>⚡ Potenciado por Flask + Supabase</p>
</div>
