// Exercises Management JavaScript

let currentExerciseId = null;
let exerciseModal = null;
let allExercises = [];

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Exercises.js initialized');
    
    // Initialize Bootstrap modal
    const modalElement = document.getElementById('exerciseModal');
    if (modalElement) {
        exerciseModal = new bootstrap.Modal(modalElement);
        console.log('✅ Bootstrap modal initialized');
    } else {
        console.error('❌ Modal element not found');
    }
    
    // Load exercises from window data or fetch from API
    console.log('📊 Checking window.exercisesData:', typeof window.exercisesData);
    
    if (window.exercisesData) {
        console.log('✅ Using window.exercisesData:', window.exercisesData.length, 'exercises');
        allExercises = window.exercisesData;
        renderExercises(allExercises);
        updateStats();
    } else {
        console.log('⬇️ Fetching exercises from API...');
        loadExercises();
    }
    
    // Add event listeners
    setupEventListeners();
    
    // Update statistics
    updateStats();
});

async function loadExercises() {
    console.log('🔄 loadExercises() called');
    try {
        showLoading(true);
        console.log('📡 Fetching from /api/admin/exercises...');
        const response = await fetch('/api/admin/exercises');
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📡 Response data:', data);
        
        if (response.ok) {
            console.log('✅ API response OK, setting allExercises:', (data.exercises && data.exercises.length) || 0);
            allExercises = data.exercises;
            renderExercises(allExercises);
            updateStats();
        } else {
            console.error('❌ API response failed:', data.error);
            showNotification('Error al cargar ejercicios: ' + data.error, 'danger');
        }
    } catch (error) {
        console.error('💥 Error in loadExercises():', error);
        showNotification('Error de conexión al cargar ejercicios', 'danger');
    } finally {
        showLoading(false);
    }
}

function renderExercises(exercises) {
    console.log('🎨 renderExercises() called with:', (exercises && exercises.length) || 0, 'exercises');
    
    const tbody = document.getElementById('exercisesTableBody');
    if (!tbody) {
        console.error('❌ exercisesTableBody not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (!exercises || exercises.length === 0) {
        console.log('⚠️ No exercises to render');
        updatePaginationVisibility();
        return;
    }
    
    console.log('✅ Rendering', exercises.length, 'exercises in table');
    
    exercises.forEach((exercise, index) => {
        console.log(`📝 Rendering exercise ${index + 1}:`, exercise.id, (exercise.question && exercise.question.substring(0, 30)) + '...');
        const row = createExerciseRow(exercise);
        tbody.appendChild(row);
    });
    
    updatePaginationVisibility();
}

function createExerciseRow(exercise) {
    const row = document.createElement('tr');
    row.dataset.id = exercise.id;
    
    const levelClass = `level-${exercise.level}`;
    const correctOption = exercise.options[exercise.correct_answer - 1] || `Opción ${exercise.correct_answer}`;
    
    row.innerHTML = `
        <td><span class="badge bg-light text-dark">#${String(exercise.id).padStart(3, '0')}</span></td>
        <td>
            <span class="level-badge ${levelClass}">${capitalizeFirst(exercise.level)}</span>
        </td>
        <td>
            <div class="exercise-question-preview" title="${exercise.question}">
                ${exercise.question}
            </div>
        </td>
        <td>${correctOption}</td>
        <td>
            <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-primary" onclick="openEditModal(${exercise.id})" title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteExercise(${exercise.id})" title="Eliminar">
                    <i class="fas fa-trash"></i>
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="previewExerciseFromList(${exercise.id})" title="Vista previa">
                    <i class="fas fa-eye"></i>
                </button>
            </div>
        </td>
    `;
    
    return row;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function showLoading(show, progress = null) {
    const loadingElement = document.getElementById('loading-indicator');
    if (loadingElement) {
        if (show) {
            loadingElement.style.display = 'block';
            
            // Si hay progreso, mostrarlo
            if (progress !== null) {
                let progressHTML = `
                    <div class="progress mb-3">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" 
                             style="width: ${progress}%" 
                             aria-valuenow="${progress}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${progress}%
                        </div>
                    </div>
                `;
                
                // Buscar o crear contenedor de progreso
                let progressContainer = document.getElementById('import-progress-container');
                if (!progressContainer) {
                    progressContainer = document.createElement('div');
                    progressContainer.id = 'import-progress-container';
                    progressContainer.className = 'mb-3';
                    loadingElement.insertBefore(progressContainer, loadingElement.firstChild);
                }
                progressContainer.innerHTML = progressHTML;
            }
        } else {
            loadingElement.style.display = 'none';
            
            // Limpiar contenedor de progreso
            const progressContainer = document.getElementById('import-progress-container');
            if (progressContainer) {
                progressContainer.remove();
            }
        }
    }
}

function showImportProgress(current, total, message = '') {
    const progress = Math.round((current / total) * 100);
    showLoading(true, progress);
    
    // Actualizar mensaje si se proporciona
    if (message) {
        const loadingElement = document.getElementById('loading-indicator');
        if (loadingElement) {
            let messageElement = document.getElementById('import-progress-message');
            if (!messageElement) {
                messageElement = document.createElement('div');
                messageElement.id = 'import-progress-message';
                messageElement.className = 'text-center mt-2';
                loadingElement.appendChild(messageElement);
            }
            messageElement.innerHTML = `<small class="text-muted">${message}</small>`;
        }
    }
}

function setupEventListeners() {

    // Search input with debounce
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(filterExercises, 300));
    }
    
    // Level filter
    const levelFilter = document.getElementById('levelFilter');
    if (levelFilter) {
        levelFilter.addEventListener('change', filterExercises);
    }
    
    // Bulk upload file input
    const bulkFile = document.getElementById('bulkFile');
    if (bulkFile) {
        bulkFile.addEventListener('change', handleBulkUpload);
    }
    
    // Drag and drop for bulk upload
    const bulkArea = document.getElementById('bulkUploadArea');
    if (bulkArea) {
        setupDragAndDrop(bulkArea);
    }
}
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function filterExercises() {
    const searchValue = document.getElementById('searchInput').value.toLowerCase();
    const levelValue = document.getElementById('levelFilter').value;
    
    try {
        showLoading(true);
        const params = new URLSearchParams();
        if (searchValue) params.append('search', searchValue);
        if (levelValue) params.append('level', levelValue);
        
        const response = await fetch(`/api/admin/exercises?${params}`);
        const data = await response.json();
        
        if (response.ok) {
            allExercises = data.exercises;
            renderExercises(allExercises);
            updateStats();
        } else {
            showNotification('Error al filtrar ejercicios: ' + data.error, 'danger');
        }
    } catch (error) {
        console.error('Error filtering exercises:', error);
        showNotification('Error de conexión al filtrar ejercicios', 'danger');
    } finally {
        showLoading(false);
    }
}

function updatePaginationVisibility() {
    const hasExercises = allExercises.length > 0;
    const pagination = document.querySelector('.pagination');
    
    if (!hasExercises) {
        document.getElementById('noResultsMessage').style.display = 'block';
        if (pagination) pagination.style.display = 'none';
    } else {
        document.getElementById('noResultsMessage').style.display = 'none';
        if (pagination) pagination.style.display = 'flex';
    }
}

function updateStats() {
    let total = allExercises.length;
    let counts = {
        principiante: 0,
        intermedio: 0,
        avanzado: 0,
        experto: 0
    };
    
    allExercises.forEach(exercise => {
        if (counts.hasOwnProperty(exercise.level)) {
            counts[exercise.level]++;
        }
    });
    
    document.getElementById('totalExercises').textContent = total;
    document.getElementById('totalPrincipiante').textContent = counts.principiante;
    document.getElementById('totalIntermedio').textContent = counts.intermedio;
    document.getElementById('totalAvanzado').textContent = counts.avanzado;
    
    const expertoElement = document.getElementById('totalExperto');
    if (expertoElement) {
        expertoElement.textContent = counts.experto;
    }
}

function openAddModal() {
    currentExerciseId = null;
    document.getElementById('modalTitle').textContent = 'Agregar Nuevo Ejercicio';
    document.getElementById('exerciseForm').reset();
    document.getElementById('exerciseId').value = '';
    
    // Reset options
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`option${i}`).value = '';
    }
    
    // Reset correct answer radio
    const checkedRadio = document.querySelector('input[name="correctAnswer"]:checked');
    if (checkedRadio) {
        checkedRadio.checked = false;
    }
    
    exerciseModal.show();
}

async function openEditModal(exerciseId) {
    currentExerciseId = exerciseId;
    document.getElementById('modalTitle').textContent = 'Editar Ejercicio';
    
    try {
        showLoading(true);
        const response = await fetch(`/api/admin/exercises`);
        const data = await response.json();
        
        if (response.ok) {
            const exercise = data.exercises.find(ex => ex.id === exerciseId);
            if (exercise) {
                document.getElementById('exerciseId').value = exerciseId;
                document.getElementById('question').value = exercise.question;
                document.getElementById('level').value = exercise.level;
                document.getElementById('explanation').value = exercise.explanation || '';
                
                // Load options
                if (exercise.options && Array.isArray(exercise.options)) {
                    exercise.options.forEach((opt, index) => {
                        if (index < 4) {
                            document.getElementById(`option${index + 1}`).value = opt;
                        }
                    });
                }
                
                // Set correct answer
                const correctRadio = document.querySelector(`input[name="correctAnswer"][value="${exercise.correct_answer}"]`);
                if (correctRadio) correctRadio.checked = true;
                
                exerciseModal.show();
            } else {
                showNotification('Ejercicio no encontrado', 'danger');
            }
        } else {
            showNotification('Error al cargar ejercicio: ' + data.error, 'danger');
        }
    } catch (error) {
        console.error('Error loading exercise:', error);
        showNotification('Error de conexión al cargar ejercicio', 'danger');
    } finally {
        showLoading(false);
    }
}

async function saveExercise() {
    // Validate form
    if (!validateForm()) {
        return;
    }
    
    // Show loading state
    const saveBtn = document.querySelector('#exerciseModal .btn-primary');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Guardando...';
    saveBtn.disabled = true;
    
    try {
        const formData = {
            question: document.getElementById('question').value,
            level: document.getElementById('level').value,
            options: [
                document.getElementById('option1').value,
                document.getElementById('option2').value,
                document.getElementById('option3').value,
                document.getElementById('option4').value
            ],
            correct_answer: parseInt(document.querySelector('input[name="correctAnswer"]:checked').value),
            explanation: document.getElementById('explanation').value
        };
        
        let response;
        if (currentExerciseId) {
            // Update existing exercise
            response = await fetch(`/api/admin/exercises/${currentExerciseId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
        } else {
            // Create new exercise
            response = await fetch('/api/admin/exercises', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            exerciseModal.hide();
            showNotification(
                currentExerciseId ? 'Ejercicio actualizado exitosamente' : 'Ejercicio creado exitosamente', 
                'success'
            );
            await loadExercises(); // Reload exercises
            notifyBotOfChanges(); // Notify bot of changes
        } else {
            showNotification('Error al guardar ejercicio: ' + data.error, 'danger');
        }
    } catch (error) {
        console.error('Error saving exercise:', error);
        showNotification('Error de conexión al guardar ejercicio', 'danger');
    } finally {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    }
}

function validateForm() {
    const question = document.getElementById('question').value;
    const level = document.getElementById('level').value;
    let hasOptions = true;
    let hasCorrectAnswer = false;
    
    // Check options
    for (let i = 1; i <= 4; i++) {
        const option = document.getElementById(`option${i}`).value;
        if (!option.trim()) {
            hasOptions = false;
            break;
        }
    }
    
    // Check correct answer
    const correctAnswer = document.querySelector('input[name="correctAnswer"]:checked');
    if (correctAnswer) {
        hasCorrectAnswer = true;
    }
    
    if (!question || !level) {
        alert('Por favor completa todos los campos obligatorios');
        return false;
    }
    
    if (!hasOptions) {
        alert('Por favor completa todas las opciones');
        return false;
    }
    
    if (!hasCorrectAnswer) {
        alert('Por favor selecciona la respuesta correcta');
        return false;
    }
    
    return true;
}

async function deleteExercise(exerciseId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este ejercicio?')) {
        return;
    }
    
    try {
        showLoading(true);
        const response = await fetch(`/api/admin/exercises/${exerciseId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Ejercicio eliminado exitosamente', 'success');
            await loadExercises(); // Reload exercises
        } else {
            showNotification('Error al eliminar ejercicio: ' + data.error, 'danger');
        }
    } catch (error) {
        console.error('Error deleting exercise:', error);
        showNotification('Error de conexión al eliminar ejercicio', 'danger');
    } finally {
        showLoading(false);
    }
}

function previewExerciseFromList(exerciseId) {
    const exercise = allExercises.find(ex => ex.id === exerciseId);
    if (!exercise) return;
    
    let preview = '📝 PREVIEW DEL EJERCICIO\n\n';
    preview += `Pregunta: ${exercise.question}\n\n`;
    preview += `Nivel: ${capitalizeFirst(exercise.level)}\n\n`;
    
    if (exercise.options && Array.isArray(exercise.options)) {
        exercise.options.forEach((opt, index) => {
            const marker = (index + 1) === exercise.correct_answer ? '✅' : '○';
            preview += `${marker} Opción ${index + 1}: ${opt}\n`;
        });
    }
    
    if (exercise.explanation) {
        preview += `\nExplicación: ${exercise.explanation}`;
    }
    
    alert(preview);
}

function previewExercise() {
    const question = document.getElementById('question').value;
    const options = [];
    let preview = '📝 PREVIEW DEL EJERCICIO\n\n';
    preview += `Pregunta: ${question}\n\n`;
    
    for (let i = 1; i <= 4; i++) {
        const option = document.getElementById(`option${i}`).value;
        const isCorrectInput = document.querySelector(`input[name="correctAnswer"][value="${i}"]`);
        const isCorrect = isCorrectInput ? isCorrectInput.checked : false;
        const marker = isCorrect ? '✅' : '○';
        preview += `${marker} Opción ${i}: ${option}\n`;
    }
    
    const explanation = document.getElementById('explanation').value;
    if (explanation) {
        preview += `\nExplicación: ${explanation}`;
    }
    
    alert(preview);
}

function exportExercises() {
    try {
        const dataStr = JSON.stringify(allExercises, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        const exportName = `ejercicios_${new Date().toISOString().slice(0,10)}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportName);
        linkElement.click();
        
        showNotification(`${allExercises.length} ejercicios exportados`, 'success');
    } catch (error) {
        console.error('Error exporting exercises:', error);
        showNotification('Error al exportar ejercicios', 'danger');
    }
}

function exportExercisesCSV() {
    try {
        let csv = 'ID,Nivel,Pregunta,Opción1,Opción2,Opción3,Opción4,Respuesta,Explicación\n';
        
        allExercises.forEach(exercise => {
            // Escapar comillas y comas para CSV
            const escapeCSV = (str) => {
                if (!str) return '';
                return `"${str.toString().replace(/"/g, '""')}"`;
            };
            
            csv += `${exercise.id},${exercise.level},`;
            csv += `${escapeCSV(exercise.question)},`;
            csv += `${escapeCSV(exercise.options[0])},${escapeCSV(exercise.options[1])},`;
            csv += `${escapeCSV(exercise.options[2])},${escapeCSV(exercise.options[3])},`;
            csv += `${exercise.correct_answer},${escapeCSV(exercise.explanation)}\n`;
        });
        
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `ejercicios_${new Date().toISOString().slice(0,10)}.csv`);
        link.click();
        URL.revokeObjectURL(url);
        
        showNotification(`${allExercises.length} ejercicios exportados a CSV`, 'success');
    } catch (error) {
        console.error('Error exporting exercises to CSV:', error);
        showNotification('Error al exportar ejercicios a CSV', 'danger');
    }
}

function exportExercisesByFormat(format) {
    if (format === 'csv') {
        exportExercisesCSV();
    } else {
        exportExercises();
    }
}

function downloadTemplate() {
    const template = [
        {
            "level": "principiante",
            "question": "¿Cuál es la salida de print(2 ** 3)?",
            "options": ["5", "6", "8", "9"],
            "correct_answer": 3,
            "explanation": "El operador ** significa exponenciación. 2 ** 3 = 2 * 2 * 2 = 8"
        }
    ];
    
    try {
        const dataStr = JSON.stringify(template, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', 'plantilla_ejercicios.json');
        linkElement.click();
        
        showNotification('Plantilla descargada exitosamente', 'success');
    } catch (error) {
        console.error('Error downloading template:', error);
        showNotification('Error al descargar plantilla', 'danger');
    }
}

async function handleBulkUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const fileName = file.name.toLowerCase();
    
    if (fileName.endsWith('.json')) {
        await handleJSONUpload(file);
    } else if (fileName.endsWith('.csv')) {
        await handleCSVUpload(file);
    } else {
        showNotification('Por favor selecciona un archivo JSON o CSV válido', 'danger');
        return;
    }
    
    // Reset file input
    event.target.value = '';
}

async function handleJSONUpload(file) {
    // Validar tamaño del archivo (máximo 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showNotification('El archivo es demasiado grande. Máximo permitido: 10MB', 'danger');
        return;
    }
    
    // Validar tipo de archivo
    if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
        showNotification('Por favor selecciona un archivo JSON válido', 'danger');
        return;
    }
    
    showLoading(true);
    
    try {
        // Usar Promise para mejor manejo de errores
        const exercises = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            // Configurar timeout
            const timeout = setTimeout(() => {
                reader.abort();
                reject(new Error('Tiempo de espera agotado al leer el archivo'));
            }, 30000); // 30 segundos
            
            reader.onload = function(e) {
                clearTimeout(timeout);
                try {
                    const result = e.target.result;
                    if (!result || result.length === 0) {
                        reject(new Error('El archivo está vacío'));
                        return;
                    }
                    
                    const parsed = JSON.parse(result);
                    resolve(parsed);
                } catch (parseError) {
                    reject(new Error('Error al parsear JSON: ' + parseError.message));
                }
            };
            
            reader.onerror = function() {
                clearTimeout(timeout);
                const error = reader.error;
                if (error) {
                    if (error.name === 'NetworkError' || error.message.includes('NetworkError')) {
                        reject(new Error('Error de red al leer el archivo. Intenta con un archivo más pequeño o verifica tu conexión.'));
                    } else {
                        reject(new Error('Error al leer el archivo: ' + error.message));
                    }
                } else {
                    reject(new Error('Error desconocido al leer el archivo'));
                }
            };
            
            reader.onabort = function() {
                clearTimeout(timeout);
                reject(new Error('Lectura del archivo cancelada'));
            };
            
            // Iniciar lectura
            try {
                reader.readAsText(file);
            } catch (readError) {
                clearTimeout(timeout);
                reject(new Error('Error al iniciar la lectura del archivo: ' + readError.message));
            }
        });
        
        // Validar que sea un array y tenga ejercicios
        if (!Array.isArray(exercises)) {
            showNotification('El archivo JSON debe contener un array de ejercicios', 'danger');
            return;
        }
        
        if (exercises.length === 0) {
            showNotification('El archivo no contiene ejercicios', 'warning');
            return;
        }
        
        if (exercises.length > 1000) {
            showNotification('El archivo contiene demasiados ejercicios. Máximo permitido: 1000', 'danger');
            return;
        }
        
        console.log(`Archivo JSON leído exitosamente: ${exercises.length} ejercicios`);
        
        // Validar ejercicios
        const validation = validateExercises(exercises);
        if (!validation.valid) {
            showNotification(`Errores de validación: ${validation.errors.slice(0, 5).join(', ')}${validation.errors.length > 5 ? '...' : ''}`, 'danger');
            console.error('Validation errors:', validation.errors);
            return;
        }
        
        // Preparar datos para envío
        const importData = {
            exercises: exercises,
            metadata: {
                filename: file.name,
                size: file.size,
                uploaded_at: new Date().toISOString(),
                total_exercises: exercises.length
            }
        };
        
        console.log('Enviando datos al servidor...', importData.metadata);
        
        // Mostrar progreso inicial
        showImportProgress(0, exercises.length, 'Iniciando importación...');
        
        // Enviar al servidor con timeout extendido y progreso
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutos para 300 ejercicios
        
        // Simular progreso mientras espera respuesta del servidor
        let progressInterval;
        let currentProgress = 0;
        
        const startProgressSimulation = () => {
            progressInterval = setInterval(() => {
                if (currentProgress < 90) {
                    currentProgress += Math.random() * 5; // Incremento aleatorio
                    currentProgress = Math.min(currentProgress, 90);
                    showImportProgress(
                        Math.round(currentProgress), 
                        exercises.length, 
                        `Procesando ejercicios... (${Math.round(currentProgress)}%)`
                    );
                }
            }, 1000);
        };
        
        startProgressSimulation();
        
        try {
            const response = await fetch('/api/admin/exercises/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(importData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            clearInterval(progressInterval);
            
            // Mostrar progreso casi completo
            showImportProgress(95, exercises.length, 'Procesando respuesta del servidor...');
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = 'Error al importar ejercicios';
                
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || errorMessage;
                } catch {
                    errorMessage = `${errorMessage}: ${response.status} ${response.statusText}`;
                }
                
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            console.log('Respuesta del servidor:', data);
            
            // Progreso completo
            showImportProgress(100, exercises.length, 'Importación completada');
            
            // Pequeña pausa para mostrar el 100%
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Mostrar resultados
            const successRate = ((data.imported / data.total) * 100).toFixed(1);
            let message = `${data.imported} de ${data.total} ejercicios importados exitosamente (${successRate}%)`;
            
            if (data.skipped_duplicates > 0) {
                message += `, ${data.skipped_duplicates} duplicados omitidos`;
            }
            
            if (data.errors && data.errors.length > 0) {
                message += `, ${data.errors.length} errores`;
                console.warn('Import errors:', data.errors);
                
                // Mostrar primeros 5 errores
                const errorSummary = data.errors.slice(0, 5).join('; ');
                showNotification(`${message}. Errores: ${errorSummary}${data.errors.length > 5 ? '...' : ''}`, 'warning');
            } else {
                showNotification(message, 'success');
            }
            
            // Recargar ejercicios si hubo importación exitosa
            if (data.imported > 0) {
                await loadExercises();
                notifyBotOfChanges();
            }
            
        } catch (fetchError) {
            clearTimeout(timeoutId);
            clearInterval(progressInterval);
            throw fetchError;
        }
        
    } catch (error) {
        console.error('Error en handleJSONUpload:', error);
        
        let errorMessage = error.message;
        
        if (error.name === 'AbortError') {
            errorMessage = 'Tiempo de espera agotado. El archivo es muy grande o el servidor está tardando mucho en responder.';
        } else if (error.message.includes('fetch')) {
            errorMessage = 'Error de conexión con el servidor. Verifica tu conexión a internet.';
        } else if (error.message.includes('JSON')) {
            errorMessage = 'El archivo JSON no tiene un formato válido. Verifica la sintaxis.';
        }
        
        showNotification('Error al importar ejercicios: ' + errorMessage, 'danger');
    } finally {
        showLoading(false);
    }
}

async function handleCSVUpload(file) {
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const csvText = e.target.result;
            const exercises = parseCSVToExercises(csvText);
            
            if (exercises.length > 0) {
                // Validar ejercicios
                const validation = validateExercises(exercises);
                if (!validation.valid) {
                    showNotification(`Errores de validación: ${validation.errors.join(', ')}`, 'danger');
                    return;
                }
                
                showLoading(true);
                
                const response = await fetch('/api/admin/exercises/import', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ exercises })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showNotification(
                        `${data.imported} de ${data.total} ejercicios importados exitosamente desde CSV`, 
                        data.errors.length > 0 ? 'warning' : 'success'
                    );
                    
                    if (data.errors.length > 0) {
                        console.warn('Import errors:', data.errors);
                    }
                    
                    await loadExercises(); // Reload exercises
                    notifyBotOfChanges(); // Notify bot
                } else {
                    showNotification('Error al importar ejercicios: ' + data.error, 'danger');
                }
            } else {
                showNotification('El archivo CSV no contiene ejercicios válidos', 'danger');
            }
        } catch (error) {
            console.error('Error reading CSV file:', error);
            showNotification('Error al leer el archivo CSV: ' + error.message, 'danger');
        } finally {
            showLoading(false);
        }
    };
    reader.readAsText(file);
}

function parseCSVToExercises(csvText) {
    const lines = csvText.split('\n').filter(line => line.trim());
    if (lines.length < 2) return []; // Need header + at least one data row
    
    const exercises = [];
    const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
    
    for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length >= 8) { // Minimum required columns
            const exercise = {
                level: values[1] || 'principiante',
                question: values[2] || '',
                options: [
                    values[3] || '',
                    values[4] || '',
                    values[5] || '',
                    values[6] || ''
                ],
                correct_answer: parseInt(values[7]) || 1,
                explanation: values[8] || ''
            };
            
            // Validar respuesta correcta
            if (exercise.correct_answer < 1 || exercise.correct_answer > 4) {
                exercise.correct_answer = 1;
            }
            
            exercises.push(exercise);
        }
    }
    
    return exercises;
}

function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        
        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                current += '"';
                i++; // Skip next quote
            } else {
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    
    result.push(current.trim());
    return result;
}

function validateExercises(exercises) {
    const errors = [];
    const validLevels = ['principiante', 'intermedio', 'avanzado', 'experto'];
    
    exercises.forEach((exercise, index) => {
        const exerciseNum = index + 1;
        
        // Validar nivel
        if (!exercise.level || !validLevels.includes(exercise.level)) {
            errors.push(`Ejercicio ${exerciseNum}: nivel inválido`);
        }
        
        // Validar pregunta
        if (!exercise.question || exercise.question.trim().length < 10) {
            errors.push(`Ejercicio ${exerciseNum}: pregunta demasiado corta`);
        }
        
        // Validar opciones
        if (!Array.isArray(exercise.options) || exercise.options.length !== 4) {
            errors.push(`Ejercicio ${exerciseNum}: debe tener 4 opciones`);
        } else {
            const hasEmptyOptions = exercise.options.some(opt => !opt || opt.trim().length === 0);
            if (hasEmptyOptions) {
                errors.push(`Ejercicio ${exerciseNum}: todas las opciones deben tener contenido`);
            }
        }
        
        // Validar respuesta correcta
        if (!exercise.correct_answer || exercise.correct_answer < 1 || exercise.correct_answer > 4) {
            errors.push(`Ejercicio ${exerciseNum}: respuesta correcta inválida`);
        }
    });
    
    return {
        valid: errors.length === 0,
        errors: errors
    };
}

function notifyBotOfChanges() {
    // Notificar al bot que los ejercicios han cambiado
    fetch('/api/notify-bot-changes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    }).catch(error => {
        console.log('No se pudo notificar al bot:', error);
    });
}

function setupDragAndDrop(bulkArea) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        bulkArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        bulkArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        bulkArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        bulkArea.style.borderColor = '#2196f3';
        bulkArea.style.background = '#e3f2fd';
    }
    
    function unhighlight() {
        bulkArea.style.borderColor = '#e0e0e0';
        bulkArea.style.background = '#f8f9fa';
    }
    
    bulkArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        
        if (file && file.name.endsWith('.json')) {
            handleBulkUpload({ target: { files: [file] } });
        } else {
            showNotification('Por favor arrastra un archivo JSON válido', 'danger');
        }
    }
}

function refreshExercises() {
    loadExercises();
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    const iconClass = type === 'success' ? 'check-circle' : 
                    type === 'danger' ? 'exclamation-triangle' : 
                    type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${iconClass} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(notification);
        bsAlert.close();
    }, 5000);
}

// Función para manejar la exportación según el formato
function exportExercisesByFormat(format) {
    if (format === 'csv') {
        exportExercisesCSV();
    } else {
        exportExercises();
    }
}

// Función para exportar a JSON
function exportExercises() {
    window.location.href = '/api/admin/exercises/export/json';
}

// Función para exportar a CSV
function exportExercisesCSV() {
    window.location.href = '/api/admin/exercises/export/csv';
}

// Función para descargar plantilla
function downloadTemplate() {
    const template = [
        {
            "level": "principiante",
            "question": "¿Cuál es la salida de print(2 ** 3)?",
            "options": ["5", "6", "8", "9"],
            "correct_answer": 3,
            "explanation": "El operador ** significa exponenciación. 2 ** 3 = 2 * 2 * 2 = 8"
        }
    ];
    
    const dataStr = JSON.stringify(template, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', 'plantilla_ejercicios.json');
    linkElement.click();
    
    showNotification('Plantilla descargada exitosamente', 'success');
}

// Función para refrescar ejercicios
function refreshExercises() {
    location.reload();
}