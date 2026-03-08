# 🐍 Python Tutor Bot

Un bot educativo de Telegram para aprender Python con sistema de progresión, ejercicios interactivos y panel de administración web.

## 📋 Tabla de Contenidos

- [🎯 Características](#características)
- [🏗️ Arquitectura](#arquitectura)
- [🚀 Inicio Rápido](#inicio-rápido)
- [📋 Prerrequisitos](#prerrequisitos)
- [🔧 Configuración del Entorno](#configuración-del-entorno)
- [📁 Estructura del Proyecto](#estructura-del-proyecto)
- [🚀 Despliegue](#despliegue)
- [🤝 Contribuir](#contribuir)
- [📄 Licencia](#licencia)

## 🎯 Características

### 🤖 Características del Bot
- **Sistema de Aprendizaje**: Modos de aprendizaje y práctica con ejercicios interactivos
- **Sistema de Progresión**: Niveles (principiante → intermedio → avanzado → experto)
- **Sistema de XP**: Puntos de experiencia y rachas de aprendizaje
- **Estadísticas**: Seguimiento del progreso y rankings
- **Control de Estado**: Modos de mantenimiento, pausa, reinicio

### 🌐 Características Web
- **Panel de Administración**: Control completo del bot desde interfaz web
- **Gestión de Usuarios**: Ver y administrar usuarios registrados
- **Estadísticas en Tiempo Real**: Monitoreo del estado del bot
- **Control de Acceso**: Bloquear/desbloquear registro de usuarios
- **Base de Datos**: Integración con Supabase para persistencia

## 🏗️ Arquitectura

```
Python_Tutor_Bot/
├── 📱 bot-service/          # Servicio del bot Telegram
│   ├── bot.py              # Lógica principal del bot
│   ├── requirements.txt    # Dependencias Python
│   └── render-bot.yaml    # Configuración Render
├── 🌐 web-service/         # Servicio web de administración
│   ├── app.py             # Aplicación Flask
│   ├── templates/         # Plantillas HTML
│   ├── static/           # Archivos estáticos
│   └── requirements.txt  # Dependencias Python
├── 🧪 test_*.py           # Scripts de prueba
├── 📄 render.yaml         # Configuración Render general
└── 📚 README.md           # Este archivo
```

### Flujo de Arquitectura
```
Usuario Telegram → Bot Service → Web Service API → Supabase Database
     ↑                    ↑              ↑
  Comandos          Health Check    Panel Admin
```

## 🚀 Inicio Rápido

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd Python_Tutor_Bot
```

### 2. Configurar Supabase
1. Crear un nuevo proyecto en [Supabase](https://supabase.com)
2. Ejecutar el script SQL para crear las tablas necesarias
3. Obtener las credenciales (URL y Key)

### 3. Configurar Bot Telegram
1. Hablar con [@BotFather](https://t.me/BotFather) en Telegram
2. Crear un nuevo bot con `/newbot`
3. Obtener el token del bot

### 4. Configurar Variables de Entorno
```bash
# Copiar archivos de ejemplo
cp .env.example .env

# Editar variables
nano .env
```

### 5. Iniciar Servicios
```bash
# Servicio Web (Terminal 1)
cd web-service
pip install -r requirements.txt
python app.py

# Servicio Bot (Terminal 2)
cd bot-service
pip install -r requirements.txt
python bot.py
```

## 📋 Prerrequisitos

### 🔧 Software Requerido
- **Python 3.8+**: Versión mínima de Python
- **pip**: Gestor de paquetes de Python
- **Git**: Control de versiones
- **Cuenta Supabase**: Base de datos y backend
- **Bot Telegram**: Token de bot activo

### 🌐 Servicios Externos
- **Supabase**: Base de datos PostgreSQL y autenticación
- **Telegram API**: Para el funcionamiento del bot

## 🔧 Configuración del Entorno

### Variables de Entorno - Servicio Web
```bash
# web-service/.env
SECRET_KEY=tu_clave_secreta_aqui
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
BOT_SERVICE_URL=http://localhost:10001
FLASK_ENV=development
```

### Variables de Entorno - Servicio Bot
```bash
# bot-service/.env
TELEGRAM_BOT_TOKEN=tu_token_de_bot_aqui
WEB_API_URL=http://localhost:5000
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
PORT=10001
```

### Configuración de Base de Datos
Ejecutar este script SQL en tu proyecto Supabase:

```sql
-- Tabla de usuarios
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

-- Tabla de ejercicios
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

-- Tabla de estado del bot
CREATE TABLE bot_status (
    id SERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'paused', 'stopped', 'maintenance', 'restarting')),
    last_updated TIMESTAMP DEFAULT NOW(),
    updated_by TEXT,
    message TEXT
);
```

## 📁 Estructura del Proyecto

### 📱 Bot Service (`bot-service/`)
- **`bot.py`**: Lógica principal del bot Telegram
- **`requirements.txt`**: Dependencias del servicio bot
- **`render-bot.yaml`**: Configuración para despliegue en Render

### 🌐 Web Service (`web-service/`)
- **`app.py`**: Aplicación Flask principal
- **`templates/`**: Plantillas HTML del panel de administración
- **`static/`**: CSS, JS y otros archivos estáticos
- **`requirements.txt`**: Dependencias del servicio web

### 🧪 Tests
- **`test_bot_control.py`**: Pruebas del sistema de control del bot
- **`test_user_registration.py`**: Pruebas de registro de usuarios

## 🚀 Despliegue

### 🏠 Desarrollo Local
```bash
# Terminal 1 - Web Service
cd web-service
python app.py

# Terminal 2 - Bot Service  
cd bot-service
python bot.py
```

### ☁️ Render (Recomendado)
1. **Web Service**:
   - Conectar repositorio a Render
   - Configurar `web-service` como directorio raíz
   - Establecer comando de inicio: `python app.py`
   - Configurar variables de entorno

2. **Bot Service**:
   - Crear nuevo servicio en Render
   - Configurar `bot-service` como directorio raíz
   - Establecer comando de inicio: `python bot.py`
   - Configurar variables de entorno

### 🐳 Docker (Opcional)
```dockerfile
# Dockerfile para Web Service
FROM python:3.9-slim
WORKDIR /app
COPY web-service/ .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🤝 Contribuir

### 📝 Cómo Contribuir
1. **Fork** el repositorio
2. **Crear** una rama (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** los cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. **Abrir** un Pull Request

### 🎯 Directrices de Contribución
- Seguir el estilo de código existente
- Agregar pruebas para nuevas funcionalidades
- Actualizar la documentación
- Respetar las convenciones de commit

### 🐛 Reportar Issues
- Usar plantillas de issues
- Proporcionar información detallada
- Incluir pasos para reproducir
- Adjuntar capturas de pantalla si aplica

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 📞 Soporte

### 🆘 Ayuda
- **Issues**: Reportar problemas en GitHub Issues
- **Discusiones**: Participar en GitHub Discussions
- **Email**: Contactar al mantenedor del proyecto

### 📚 Recursos
- [Documentación de Telegram Bot API](https://core.telegram.org/bots/api)
- [Documentación de Supabase](https://supabase.com/docs)
- [Documentación de Flask](https://flask.palletsprojects.com/)

## 🏆 Créditos

- **Desarrollador Principal**: [Tu Nombre]
- **Contribuidores**: Gracias a todos los que contribuyen
- **Inspiración**: Sistemas de aprendizaje gamificado

---

<div align="center">
  <p>🤖 Hecho con ❤️ para la comunidad de aprendizaje de Python</p>
  <p>⭐ Si te gusta el proyecto, ¡no olvides darle una estrella!</p>
</div>
