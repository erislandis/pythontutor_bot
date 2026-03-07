import json
import requests

# Cargar algunos ejercicios de prueba del archivo expert.json
with open('exercises/exercises_data/expert.json', 'r', encoding='utf-8') as f:
    exercises = json.load(f)

# Tomar solo los primeros 5 ejercicios para probar
test_exercises = exercises[:5]

print("Ejercicios de prueba para importar:")
for i, ex in enumerate(test_exercises, 1):
    print(f"\nEjercicio {i}:")
    print(f"  Level: {ex['level']}")
    print(f"  Question: {ex['question'][:50]}...")
    print(f"  Options: {ex['options']}")
    print(f"  Correct Answer: {ex['correct_answer']}")
    print(f"  Explanation: {ex['explanation']}")

# Simular una petición de importación (para pruebas locales)
import_data = {
    'exercises': test_exercises
}

print(f"\nTotal de ejercicios a importar: {len(test_exercises)}")
print("Formato verificado: Listo para importar en la pagina web")
