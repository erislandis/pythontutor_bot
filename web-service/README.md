# PythonTutor Web Service

Servicio web de PythonTutor que proporciona:
- Páginas web públicas (index, about)
- Panel de administración para gestionar ejercicios
- API endpoints para el bot de Telegram

## Tecnologías

- **Framework**: Flask
- **Base de datos**: Supabase
- **Autenticación**: Flask-Login
- **CORS**: flask-cors para comunicación con el bot
- **Despliegue**: Gunicorn en Render

## Variables de Entorno

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SECRET_KEY=your_secret_key
FLASK_ENV=production
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
PORT=10000
LOG_LEVEL=INFO
```

## API Endpoints

### Usuarios
- `GET /api/user/<telegram_id>` - Obtener usuario
- `POST /api/user` - Crear usuario

### Ejercicios
- `GET /api/exercises/<level>` - Obtener ejercicios por nivel

### Progreso
- `POST /api/user/progress` - Actualizar progreso de usuario

## Despliegue

1. Crear nuevo Web Service en Render
2. Conectar repositorio `web-service`
3. Configurar variables de entorno
4. Desplegar automáticamente

## Estructura

```
web-service/
├── app.py              # Aplicación Flask principal
├── requirements.txt     # Dependencias Python
├── render-web.yaml     # Configuración de despliegue
├── templates/          # Plantillas HTML
├── static/            # Archivos estáticos (CSS, JS)
└── README.md          # Este archivo
```

## Comunicación con el Bot

El servicio web está configurado con CORS para permitir peticiones del bot service. El bot consume los endpoints API para obtener y actualizar datos de usuarios y ejercicios.

## Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar aplicación
python app.py
```

La aplicación estará disponible en `http://localhost:5000`
