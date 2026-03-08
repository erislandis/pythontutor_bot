# Instrucciones para Diagnosticar y Corregir Problemas de Importación

## 🔍 Pasos para Diagnosticar el Problema

### **1. Abrir la Página de Ejercicios**
1. Inicia el web-service: `python app.py`
2. Abre: `http://localhost:5000/admin/exercises`
3. Inicia sesión como administrador

### **2. Abrir Consola de Desarrollador**
1. Presiona `F12` o `Ctrl+Shift+I` (Chrome/Firefox)
2. Ve a la pestaña **Console**
3. Busca mensajes de error o advertencias

### **3. Abrir Modal de Importación**
1. Haz clic en el botón **"Importar"** en la parte superior derecha
2. El modal de importación debería abrirse

### **4. Ejecutar Diagnóstico**
1. Dentro del modal, haz clic en el botón **"Diagnosticar"**
2. Se mostrarán los resultados del diagnóstico en la parte inferior del modal
3. También se mostrarán detalles en la consola

### **5. Probar Selección de Archivo**
1. Haz clic en **"Seleccionar Archivo"**
2. Elige un archivo JSON (puedes usar los archivos generados en `generador_de_ejercicios/test_output/`)
3. Observa los mensajes en la consola

## 🚨 Problemas Comunes y Soluciones

### **Problema 1: Errores de JavaScript**
**Síntomas:**
- Mensajes de error en la consola
- El botón de importación nunca se activa
- Nada sucede al hacer clic en los botones

**Solución:**
1. Recarga la página (Ctrl+F5)
2. Limpia la caché del navegador
3. Verifica que no haya extensiones del navegador interfiriendo

### **Problema 2: Elementos Faltantes**
**Síntomas:**
- El diagnóstico muestra elementos como `exists: false`
- Errores como "Element not found"

**Solución:**
1. Asegúrate de que la página se cargó completamente
2. Verifica que estás usando la URL correcta
3. Recarga la página y espera a que cargue completamente

### **Problema 3: Archivo No Válido**
**Síntomas:**
- Mensajes de "Tipo de archivo no permitido"
- "Format mismatch" en la consola

**Solución:**
1. Usa solo archivos `.json` o `.csv`
2. Asegúrate de que el formato seleccionado coincida con el archivo
3. Verifica que el JSON tenga la estructura correcta

### **Problema 4: Bootstrap No Cargado**
**Síntomas:**
- El modal no se abre
- Errores relacionados con `bootstrap` en la consola

**Solución:**
1. Verifica la conexión a internet (para Bootstrap Icons)
2. Recarga la página
3. Verifica que los archivos CSS y JS de Bootstrap estén cargando

## 🧪 Tests de Verificación

### **Test 1: Verificar Inicialización**
En la consola, ejecuta:
```javascript
// Verificar que las funciones existen
console.log('handleFileSelect:', typeof handleFileSelect);
console.log('importExercises:', typeof importExercises);
console.log('diagnoseImportIssues:', typeof diagnoseImportIssues);
```

### **Test 2: Verificar Elementos**
En la consola, ejecuta:
```javascript
// Verificar elementos críticos
console.log('importFileInput:', document.getElementById('importFileInput'));
console.log('importButton:', document.getElementById('importButton'));
console.log('fileInfo:', document.getElementById('fileInfo'));
```

### **Test 3: Probar Manualmente**
En la consola, ejecuta:
```javascript
// Simular selección de archivo
diagnoseImportIssues();
```

## 📋 Formato JSON Esperado

Los archivos JSON deben tener esta estructura:
```json
[
  {
    "level": "principiante",
    "question": "¿Cuál es la salida de este código?\n\ntexto = \"Mundo\"\nresultado = texto.upper()",
    "options": ["ODNUM", "MUNDO", "Mundo", "mundo"],
    "correct_answer": 2,
    "explanation": "El método upper() convierte a mayúsculas"
  }
]
```

## 🛠️ Si Nada Funciona

### **Opción 1: Usar el Endpoint Directo**
```bash
curl -X POST http://localhost:5000/api/admin/exercises/import \
  -H "Content-Type: application/json" \
  -H "Cookie: tu-session-cookie" \
  -d '{"exercises": [{"level": "principiante", "question": "Test", "options": ["A", "B", "C", "D"], "correct_answer": 1, "explanation": "Test"}]}'
```

### **Opción 2: Revisar Logs del Servidor**
1. Mira la terminal donde ejecutas `python app.py`
2. Busca errores o mensajes relacionados con la importación
3. Verifica que la base de datos esté conectada

### **Opción 3: Probar con Archivo Simple**
Crea un archivo `test_simple.json`:
```json
[{"level": "principiante", "question": "¿Qué es 2+2?", "options": ["3", "4", "5", "6"], "correct_answer": 2, "explanation": "2+2=4"}]
```

## 📞 Si el Problema Persiste

1. **Captura de pantalla**: Toma una captura de la consola con los errores
2. **Diagnóstico**: Haz clic en "Diagnosticar" y comparte los resultados
3. **Archivo de prueba**: Comparte el archivo JSON que intentas importar
4. **Logs del servidor**: Comparte cualquier mensaje de error del servidor

## ✅ Checklist Final

- [ ] Sin errores en la consola JavaScript
- [ ] El diagnóstico muestra todos los elementos como `exists: true`
- [ ] El modal de importación se abre correctamente
- [ ] El botón "Seleccionar Archivo" funciona
- [ ] Al seleccionar un archivo, el botón "Importar" se activa
- [ ] La importación se completa sin errores
- [ ] Los ejercicios aparecen en la lista después de importar

Si todos estos puntos están marcados, ¡la importación debería funcionar perfectamente!
