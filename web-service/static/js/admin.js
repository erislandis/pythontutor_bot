// Admin panel JavaScript

// Confirm before deleting
function confirmDelete(exerciseId) {
    if (confirm('¿Estás seguro de que quieres eliminar este ejercicio?')) {
        window.location.href = `/admin/delete-exercise/${exerciseId}`;
    }
}

// Preview exercise before saving
function previewExercise() {
    const question = document.getElementById('question').value;
    const options = [
        document.getElementById('option1').value,
        document.getElementById('option2').value,
        document.getElementById('option3').value,
        document.getElementById('option4').value
    ];
    const correctAnswer = document.getElementById('correct_answer').value;
    
    let preview = `📝 Pregunta: ${question}\n\n`;
    options.forEach((opt, index) => {
        const marker = (index + 1) == correctAnswer ? '✅' : '○';
        preview += `${marker} Opción ${index + 1}: ${opt}\n`;
    });
    
    alert(preview);
}

// Bulk upload file validation
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && !file.name.endsWith('.json')) {
                alert('Por favor, selecciona un archivo JSON válido');
                this.value = '';
            }
        });
    }
});

// Level selection for bulk upload
document.querySelector('form[action*="bulk_upload"]')?.addEventListener('submit', function(e) {
    const level = document.getElementById('level').value;
    if (!level) {
        e.preventDefault();
        alert('Por favor, selecciona un nivel antes de subir ejercicios');
    }
});

// Search/filter exercises
function filterExercises() {
    const searchTerm = document.getElementById('search-exercises').value.toLowerCase();
    const rows = document.querySelectorAll('.exercises-table tbody tr');
    
    rows.forEach(row => {
        const question = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        if (question.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Add search box to exercises page
document.addEventListener('DOMContentLoaded', function() {
    const exercisesList = document.querySelector('.exercises-list');
    if (exercisesList && document.querySelector('.exercises-table')) {
        const searchBox = document.createElement('div');
        searchBox.className = 'search-box';
        searchBox.innerHTML = `
            <input type="text" 
                   id="search-exercises" 
                   placeholder="Buscar ejercicios..." 
                   onkeyup="filterExercises()"
                   style="margin-bottom: 20px; padding: 10px; width: 100%; border: 1px solid #ddd; border-radius: 5px;">
        `;
        exercisesList.insertBefore(searchBox, exercisesList.querySelector('h2').nextSibling);
    }
});

// Export exercises to JSON
function exportExercises() {
    const exercises = [];
    const rows = document.querySelectorAll('.exercises-table tbody tr');
    
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        const options = [];
        const optionsList = cells[3].querySelectorAll('li');
        optionsList.forEach(opt => options.push(opt.textContent));
        
        exercises.push({
            id: cells[0].textContent,
            level: cells[1].querySelector('.level-badge').textContent,
            question: cells[2].textContent,
            options: options,
            correct_answer: parseInt(cells[4].textContent.replace('Opción ', '')) - 1
        });
    });
    
    const dataStr = JSON.stringify(exercises, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `ejercicios_${new Date().toISOString().slice(0,10)}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

// Add export button
document.addEventListener('DOMContentLoaded', function() {
    const exercisesList = document.querySelector('.exercises-list');
    if (exercisesList && document.querySelector('.exercises-table')) {
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn-secondary';
        exportBtn.innerHTML = '📥 Exportar a JSON';
        exportBtn.onclick = exportExercises;
        exportBtn.style.marginBottom = '20px';
        exportBtn.style.marginRight = '10px';
        
        const header = exercisesList.querySelector('h2');
        header.parentNode.insertBefore(exportBtn, header.nextSibling);
    }
});