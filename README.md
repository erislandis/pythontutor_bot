# PythonTutor - Multi Services Architecture for Render

Sistema de aprendizaje de Python con bot de Telegram y panel web, desplegado como múltiples servicios independientes en Render.

## 🏗️ Arquitectura de Servicios

Este repositorio está estructurado para desplegar dos servicios independientes en Render:

### 🌐 Web Service (pythontutor-web)
- **Ubicación**: `web-service/`
- **Propósito**: Páginas web públicas, panel de administración, API endpoints
- **Tecnologías**: Flask, Supabase, Gunicorn, CORS
- **Tipo**: Web Service en Render
- **URL**: `https://pythontutor-web.onrender.com`

### 🤖 Bot Service (pythontutor-bot)
- **Ubicación**: `bot-service/`
- **Propósito**: Bot de Telegram interactivo para aprendizaje
- **Tecnologías**: python-telegram-bot, Supabase, requests
- **Tipo**: Worker Service en Render
- **Bot**: @pythonpersonaltutor_bot

## 📁 Estructura del Repositorio

```
Python_Tutor_Bot/
├── web-service/           # Servicio web completo
│   ├── app.py            # Flask application con API endpoints
│   ├── requirements.txt  # Dependencias: Flask, CORS, Supabase
│   ├── static/          # CSS y JavaScript
│   │   ├── css/
│   │   └── js/
│   └── templates/       # Plantillas HTML
│       ├── public/      # Páginas públicas
│       └── auth/        # Panel de administración
├── bot-service/          # Servicio bot completo
│   ├── bot.py           # Telegram bot con API calls
│   └── requirements.txt # Dependencias: python-telegram-bot, requests
├── render.yaml          # Configuración multi-servicio para Render
├── .env.example         # Ejemplo de variables de entorno
└── README.md            # Este archivo
```

## 🚀 Despliegue en Render

### 1. Preparar Repositorio
```bash
# Clonar repositorio
git clone <repository-url>
cd Python_Tutor_Bot

# Verificar estructura
ls web-service/
ls bot-service/
```

### 2. Conectar a Render
1. Crear cuenta en [Render](https://render.com)
2. Conectar este repositorio a Render
3. Render detectará automáticamente los dos servicios desde `render.yaml`

### 3. Configurar Variables de Entorno

#### Web Service (pythontutor-web)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SECRET_KEY=your_secret_key_here
FLASK_ENV=production
SESSION_COOKIE_SECURE=true
```

#### Bot Service (pythontutor-bot)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEB_API_URL=https://pythontutor-web.onrender.com
```

### 4. Despliegue Automático
- Render construirá ambos servicios independientemente
- **Web service**: Disponible en su URL asignada
- **Bot service**: Se ejecuta como worker process 24/7

## 🔄 Comunicación entre Servicios

El bot consume la API del web service a través de endpoints específicos:

### API Endpoints Disponibles
```python
# Gestión de Usuarios
GET  /api/user/<telegram_id>              # Obtener datos de usuario
POST /api/user                            # Crear nuevo usuario

# Ejercicios
GET  /api/exercises/<level>               # Obtener ejercicios por nivel

# Progreso
POST /api/user/progress                   # Actualizar progreso
GET  /api/user/progress/<telegram_id>/<level>  # Progreso por nivel

# Estadísticas
GET  /api/user/stats/<telegram_id>        # Estadísticas completas
POST /api/user/streak/<telegram_id>       # Actualizar racha
```

## 🛠️ Desarrollo Local

### 1. Configurar Entorno
```bash
# Instalar dependencias del web service
cd web-service
pip install -r requirements.txt

# Instalar dependencias del bot service
cd ../bot-service
pip install -r requirements.txt
```

### 2. Configurar Variables
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus variables
nano .env
```

### 3. Ejecutar Servicios
```bash
# Terminal 1 - Web Service
cd web-service
python app.py
# http://localhost:5000

# Terminal 2 - Bot Service
cd bot-service
python bot.py
# Bot activo en Telegram
```

## 📊 Funcionalidades Implementadas

### Web Service
- **Páginas Públicas**: Inicio, Acerca de con enlaces al bot
- **Panel Admin**: Login, gestión de ejercicios CRUD, subida masiva
- **API REST**: Endpoints completos para el bot
- **CORS**: Configurado para comunicación con el bot

### Bot Service
- **Comandos Completos**: /start, /help, /level, /exercise, /progress, /stats, /about
- **Niveles de Aprendizaje**: Principiante, Intermedio, Avanzado, Experto
- **Ejercicios Interactivos**: 1200+ ejercicios con opción múltiple
- **Estadísticas Reales**: Progreso por nivel, racha, porcentaje de completion
- **Manejo de Errores**: Reintentos automáticos, logging detallado

## 🌟 Características Técnicas

### Base de Datos Compartida
- **Supabase**: Ambos servicios comparten la misma base de datos
- **Tablas**: users, exercises, user_progress, admin_users
- **Consistencia**: Manejo de concurrencia apropiado

### Comunicación API
- **HTTP/HTTPS**: Requests estándar entre servicios
- **Timeout**: 10 segundos para todas las peticiones
- **Manejo de Errores**: Reintentos y fallbacks
- **Logging**: Detallado para debugging

### Seguridad
- **CORS**: Configurado para permitir peticiones del bot
- **Variables de Entorno**: Separadas por servicio
- **Tokens**: Bot token y Supabase keys seguros

## 📈 Monitoreo y Mantenimiento

### Logs por Servicio
- **Web Service**: Logs de Flask, API, errores HTTP
- **Bot Service**: Logs de Telegram, comunicación API, errores

### Métricas Independientes
- **Web**: Tráfico, rendimiento, endpoints más usados
- **Bot**: Usuarios activos, comandos ejecutados, errores API

### Escalabilidad
- **Independiente**: Cada servicio puede escalar separadamente
- **Recursos**: Memoria y CPU dedicados por servicio
- **Costos**: Facturación independiente

## 🚨 Troubleshooting

### Problemas Comunes

#### Bot no responde
1. Verificar que el web service esté online
2. Checar variables de entorno del bot
3. Revisar logs del bot service en Render
4. Verificar URL del web service

#### Web service lento
1. Optimizar queries a Supabase
2. Implementar caching si es necesario
3. Escalar a plan superior de Render

#### Error de conexión entre servicios
1. Verificar URL del web service en variables del bot
2. Checar configuración CORS
3. Validar que ambos servicios estén running

### Debugging en Render
1. **Logs**: Acceder a logs de cada servicio en dashboard
2. **Environment**: Verificar variables de entorno configuradas
3. **Status**: Revisar estado de los servicios
4. **Metrics**: Analizar métricas de rendimiento

## 🔄 Actualizaciones y Despliegue

### Para Actualizar el Sistema
1. Hacer cambios en el código local
2. Commit y push al repositorio
3. Render detectará cambios y actualizará ambos servicios
4. Verificar funcionamiento en producción

### Rollback
1. Identificar el commit problemático
2. Revertir cambios localmente
3. Push al repositorio
4. Render actualizará automáticamente

## 📞 Soporte y Contribuciones

### Para Issues o Problemas
1. Revisar logs del servicio afectado
2. Consultar esta documentación
3. Verificar configuración de variables
4. Crear issue en el repositorio

### Contribuciones
1. Fork del repositorio
2. Crear branch para cambios
3. Testing local de ambos servicios
4. Pull request con descripción detallada

---

**Desarrollado con ❤️ para la comunidad de aprendizaje de Python**

**Bot**: [@pythonpersonaltutor_bot](https://t.me/pythonpersonaltutor_bot)  
**Web**: [PythonTutor Web](https://pythontutor-web.onrender.com)
