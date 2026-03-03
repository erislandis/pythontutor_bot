# PythonTutor Bot Service

Bot de Telegram de PythonTutor que proporciona:
- Interacción con usuarios de Telegram
- Ejercicios de programación Python
- Seguimiento de progreso
- Comunicación con el web service

## Tecnologías

- **Framework**: python-telegram-bot
- **Base de datos**: Supabase (compartida con web service)
- **Comunicación API**: requests
- **Despliegue**: Worker Service en Render

## Variables de Entorno

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
TELEGRAM_BOT_TOKEN=your_bot_token
WEB_API_URL=https://pythontutor-web.onrender.com
LOG_LEVEL=INFO
```

## Comandos del Bot

### Básicos
- `/start` - Iniciar o reiniciar el bot
- `/help` - Mostrar ayuda
- `/about` - Acerca de PythonBot

### Aprendizaje
- `/level <nivel>` - Cambiar de nivel
- `/exercise` - Obtener ejercicio aleatorio
- `/progress` - Ver progreso

### Estadísticas
- `/stats` - Ver estadísticas detalladas
- `/leaderboard` - Ver ranking (en desarrollo)

## Comunicación con Web Service

El bot consume los siguientes endpoints del web service:

```python
# Obtener usuario
GET https://pythontutor-web.onrender.com/api/user/<telegram_id>

# Crear usuario
POST https://pythontutor-web.onrender.com/api/user

# Obtener ejercicios
GET https://pythontutor-web.onrender.com/api/exercises/<level>

# Actualizar progreso
POST https://pythontutor-web.onrender.com/api/user/progress
```

## Despliegue

1. Crear nuevo Worker Service en Render
2. Conectar repositorio `bot-service`
3. Configurar variables de entorno
4. Desplegar automáticamente

## Estructura

```
bot-service/
├── bot.py              # Aplicación del bot
├── requirements.txt     # Dependencias Python
├── render-bot.yaml     # Configuración de despliegue
└── README.md          # Este archivo
```

## Funcionalidades

### Niveles de Aprendizaje
- **Principiante**: Fundamentos básicos de Python
- **Intermedio**: Estructuras de control y funciones
- **Avanzado**: Programación orientada a objetos
- **Experto**: Temas avanzados y buenas prácticas

### Sistema de Progreso
- Seguimiento de ejercicios completados
- Puntuación por respuestas correctas
- Estadísticas de aprendizaje
- Niveles desbloqueables

### Interacción
- Ejercicios con opción múltiple
- Explicaciones detalladas
- Retroalimentación inmediata
- Interfaz amigable con botones

## Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar bot
python bot.py
```

## Manejo de Errores

El bot incluye manejo robusto de errores:
- Reconexión automática con el web service
- Logging detallado para debugging
- Mensajes de error amigables para usuarios
- Timeout configurado para peticiones API

## Escalabilidad

Como Worker Service independiente:
- Puede escalar según la carga de usuarios
- No afecta al rendimiento del web service
- Reinicios independientes
- Monitoreo separado
