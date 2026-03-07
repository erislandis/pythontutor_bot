import json
import random
import os
from typing import List, Dict, Any
from pathlib import Path

class ExerciseGenerator:
    """Generador de ejercicios para todos los niveles - CORREGIDO"""
    
    @staticmethod
    def _map_difficulty_to_level(difficulty):
        """Convierte difficulty numérico a level string"""
        level_mapping = {
            1: 'principiante',
            2: 'intermedio', 
            3: 'avanzado',
            4: 'experto'
        }
        return level_mapping.get(difficulty, 'principiante')
    
    @staticmethod
    def _find_correct_answer_index(options, correct_answer):
        """Encuentra el índice de la respuesta correcta en las opciones"""
        try:
            correct_answer_str = str(correct_answer).strip()
            for i, option in enumerate(options):
                if str(option).strip() == correct_answer_str:
                    return i + 1  # Índice base 1
            return 1  # Default a primera opción si no encuentra
        except:
            return 1
    
    @staticmethod
    def _generate_options(correct_answer, answer_type="numeric"):
        """Genera opciones de respuesta para un ejercicio"""
        # Convertir answer a string para consistencia
        correct_answer_str = str(correct_answer)
        options = [correct_answer_str]
        
        # Generar opciones incorrectas basadas en el tipo de respuesta
        if answer_type == "numeric":
            # Para respuestas numéricas
            try:
                correct_num = float(correct_answer_str) if '.' in correct_answer_str else int(correct_answer_str)
                
                # Generar opciones incorrectas cercanas al número correcto
                incorrect_options = []
                if isinstance(correct_num, (int, float)):
                    # Opciones para números
                    incorrect_options = [
                        str(correct_num + 1),
                        str(correct_num - 1),
                        str(correct_num * 2),
                        str(correct_num // 2) if isinstance(correct_num, int) and correct_num > 0 else "0",
                        str(abs(correct_num - 5)),
                        str(correct_num + random.randint(2, 10))
                    ]
                
                # Añadir opciones comunes para distractores
                common_incorrect = ["0", "1", "Error", "None", "True", "False", "SyntaxError", "[]", "{}"]
                incorrect_options.extend(random.sample(common_incorrect, 2))
                
                # Añadir opciones incorrectas únicas (máximo 3 adicionales)
                for opt in incorrect_options:
                    if len(options) >= 4:
                        break
                    opt_str = str(opt)
                    if opt_str not in options and opt_str != correct_answer_str:
                        options.append(opt_str)
                
            except ValueError:
                # Si no se puede convertir a número, tratar como texto
                pass
        
        elif answer_type == "boolean":
            # Para respuestas booleanas (True/False)
            if correct_answer_str.lower() == "true":
                options = ["True", "False"]
            else:
                options = ["False", "True"]
        
        elif answer_type == "text":
            # Para respuestas de texto
            incorrect_texts = ["Error", "None", "0", "1", "[]", "{}", "SyntaxError", "NameError", 
                             "IndexError", "ValueError", "TypeError", "KeyError"]
            while len(options) < 4:
                opt = random.choice(incorrect_texts)
                if opt not in options and opt != correct_answer_str:
                    options.append(opt)
        
        # Asegurar que tenemos exactamente 4 opciones
        while len(options) < 4:
            options.append(f"Opción {len(options) + 1}")
        
        # Mezclar las opciones aleatoriamente (pero asegurar que correct_answer esté presente)
        if correct_answer_str in options:
            random.shuffle(options)
        
        return options
    
    @staticmethod
    def _get_answer_type(answer):
        """Determina el tipo de respuesta para generar opciones apropiadas"""
        answer_str = str(answer)
        
        if answer_str.lower() in ['true', 'false']:
            return "boolean"
        
        try:
            # Intentar convertir a número
            if '.' in answer_str:
                float(answer_str)
            else:
                int(answer_str)
            return "numeric"
        except ValueError:
            # No es un número
            if len(answer_str) < 20:  # Respuestas cortas
                return "text"
            else:
                return "text"
    
    @staticmethod
    def generate_beginner_exercises(count=300):
        """Genera ejercicios para nivel principiante"""
        exercises = []
        
        for i in range(1, count + 1):
            exercise_type = random.choice([
                'variables', 'operators', 'strings', 'lists', 
                'conditionals', 'loops', 'functions', 'type_conversion'
            ])
            
            if exercise_type == 'variables':
                exercise = ExerciseGenerator._generate_variable_exercise(i)
            elif exercise_type == 'operators':
                exercise = ExerciseGenerator._generate_operator_exercise(i)
            elif exercise_type == 'strings':
                exercise = ExerciseGenerator._generate_string_exercise(i)
            elif exercise_type == 'lists':
                exercise = ExerciseGenerator._generate_list_exercise(i)
            elif exercise_type == 'conditionals':
                exercise = ExerciseGenerator._generate_conditional_exercise(i)
            elif exercise_type == 'loops':
                exercise = ExerciseGenerator._generate_loop_exercise(i)
            elif exercise_type == 'functions':
                exercise = ExerciseGenerator._generate_function_exercise(i)
            else:  # type_conversion
                exercise = ExerciseGenerator._generate_type_conversion_exercise(i)
            
            # Generar opciones para el ejercicio
            answer = exercise['answer']
            answer_type = ExerciseGenerator._get_answer_type(answer)
            options = ExerciseGenerator._generate_options(answer, answer_type)
            
            # Encontrar el índice correcto
            correct_answer_index = ExerciseGenerator._find_correct_answer_index(options, answer)
            
            # Crear ejercicio con formato CORRECTO
            formatted_exercise = {
                'level': 'principiante',  # Campo level requerido
                'question': exercise['question'],
                'options': options,
                'correct_answer': correct_answer_index,  # Índice numérico 1-4
                'explanation': exercise['explanation']
                # Nota: NO incluir 'id', 'type', 'answer' - la BD los genera o no los necesita
            }
            
            exercises.append(formatted_exercise)
        
        return exercises
    
    @staticmethod
    def _generate_variable_exercise(id_num):
        """Genera ejercicio de variables"""
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        
        # Evitar división por cero para la operación //
        operations = [
            ('+', a + b),
            ('-', a - b),
            ('*', a * b),
            ('//', a // b if b != 0 else 0)
        ]
        op, result = random.choice(operations)
        
        # Si elegimos // y b es 0, cambiar b
        if op == '//' and b == 0:
            b = random.randint(1, 100)
            result = a // b
        
        return {
            'question': f'¿Qué valor tendrá la variable "resultado" después de ejecutar este código?\n\n'
                       f'a = {a}\n'
                       f'b = {b}\n'
                       f'resultado = a {op} b',
            'answer': str(result),
            'explanation': f'La operación {a} {op} {b} = {result}'
        }
    
    @staticmethod
    def _generate_operator_exercise(id_num):
        """Genera ejercicio de operadores"""
        operators = ['==', '!=', '>', '<', '>=', '<=', 'and', 'or', 'not']
        op = random.choice(operators)
        
        if op in ['and', 'or']:
            a = random.choice([True, False])
            b = random.choice([True, False])
            code = f'a = {a}\nb = {b}\nresultado = a {op} b'
            
            if op == 'and':
                result = a and b
            else:  # or
                result = a or b
            
            explanation = f'La operación a {op} b resulta en {result}'
        
        elif op == 'not':
            a = random.choice([True, False])
            code = f'a = {a}\nresultado = not a'
            result = not a
            explanation = f'La operación not a resulta en {result}'
        
        else:
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            code = f'a = {a}\nb = {b}\nresultado = a {op} b'
            
            if op == '==':
                result = a == b
            elif op == '!=':
                result = a != b
            elif op == '>':
                result = a > b
            elif op == '<':
                result = a < b
            elif op == '>=':
                result = a >= b
            else:  # '<='
                result = a <= b
            
            explanation = f'La operación a {op} b resulta en {result}'
        
        return {
            'question': f'¿Qué valor tendrá la variable "resultado" después de ejecutar este código?\n\n{code}',
            'answer': str(result),
            'explanation': explanation
        }
    
    @staticmethod
    def _generate_string_exercise(id_num):
        """Genera ejercicio de strings"""
        string = random.choice([
            'Python', 'Hola Mundo', 'Programación', 'Desarrollo', 
            'Aprendizaje', 'Ejercicio', 'Práctica', 'Código'
        ])
        
        exercise_type = random.choice(['lower', 'upper', 'len'])
        
        if exercise_type == 'lower':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'texto = "{string}"\n'
                           f'resultado = texto.lower()',
                'answer': string.lower(),
                'explanation': f'El método lower() convierte todo el texto a minúsculas.'
            }
        elif exercise_type == 'upper':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'texto = "{string}"\n'
                           f'resultado = texto.upper()',
                'answer': string.upper(),
                'explanation': f'El método upper() convierte todo el texto a mayúsculas.'
            }
        else:  # 'len'
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'texto = "{string}"\n'
                           f'resultado = len(texto)',
                'answer': str(len(string)),
                'explanation': f'La función len() devuelve la longitud del string.'
            }
        
        return exercise
    
    @staticmethod
    def _generate_list_exercise(id_num):
        """Genera ejercicio de listas"""
        numbers = [random.randint(1, 20) for _ in range(5)]
        
        exercise_type = random.choice(['len', 'first', 'sum'])
        
        if exercise_type == 'len':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'lista = {numbers}\n'
                           f'resultado = len(lista)',
                'answer': str(len(numbers)),
                'explanation': f'La función len() devuelve el número de elementos en la lista.'
            }
        elif exercise_type == 'first':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'lista = {numbers}\n'
                           f'resultado = lista[0]',
                'answer': str(numbers[0]),
                'explanation': f'lista[0] accede al primer elemento de la lista.'
            }
        else:  # 'sum'
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'lista = {numbers}\n'
                           f'resultado = sum(lista)',
                'answer': str(sum(numbers)),
                'explanation': f'La función sum() devuelve la suma de todos los elementos.'
            }
        
        return exercise
    
    @staticmethod
    def _generate_conditional_exercise(id_num):
        """Genera ejercicio de condicionales"""
        exercise_type = random.choice(['comparison', 'even_odd'])
        
        if exercise_type == 'comparison':
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            exercise = {
                'question': f'¿Qué valor tendrá "resultado" después de ejecutar este código?\n\n'
                           f'a = {a}\n'
                           f'b = {b}\n'
                           f'if a > b:\n'
                           f'    resultado = "mayor"\n'
                           f'else:\n'
                           f'    resultado = "menor o igual"',
                'answer': 'mayor' if a > b else 'menor o igual',
                'explanation': f'a = {a}, b = {b}, por lo tanto a > b es {a > b}'
            }
        else:  # 'even_odd'
            a = random.randint(1, 20)
            exercise = {
                'question': f'¿Qué valor tendrá "resultado" después de ejecutar este código?\n\n'
                           f'numero = {a}\n'
                           f'if numero % 2 == 0:\n'
                           f'    resultado = "par"\n'
                           f'else:\n'
                           f'    resultado = "impar"',
                'answer': 'par' if a % 2 == 0 else 'impar',
                'explanation': f'El número {a} es {"par" if a % 2 == 0 else "impar"}'
            }
        
        return exercise
    
    @staticmethod
    def _generate_loop_exercise(id_num):
        """Genera ejercicio de bucles"""
        exercise_type = random.choice(['sum', 'list'])
        
        if exercise_type == 'sum':
            n = random.randint(3, 10)
            exercise = {
                'question': f'¿Qué valor tendrá "resultado" después de ejecutar este código?\n\n'
                           f'resultado = 0\n'
                           f'for i in range({n}):\n'
                           f'    resultado += i',
                'answer': str(sum(range(n))),
                'explanation': f'Suma de 0 a {n-1} = {sum(range(n))}'
            }
        else:  # 'list'
            n = random.randint(3, 10)
            exercise = {
                'question': f'¿Qué valor tendrá "resultado" después de ejecutar este código?\n\n'
                           f'resultado = []\n'
                           f'for i in range({n}):\n'
                           f'    resultado.append(i * 2)',
                'answer': str([i * 2 for i in range(n)]),
                'explanation': f'Lista de números pares desde 0 hasta {2*(n-1)}'
            }
        
        return exercise
    
    @staticmethod
    def _generate_function_exercise(id_num):
        """Genera ejercicio de funciones"""
        exercise_type = random.choice(['sum', 'square'])
        
        if exercise_type == 'sum':
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            exercise = {
                'question': f'¿Qué devuelve la llamada a la función?\n\n'
                           f'def suma(x, y):\n'
                           f'    return x + y\n\n'
                           f'resultado = suma({a}, {b})',
                'answer': str(a + b),
                'explanation': f'La función suma devuelve {a} + {b} = {a + b}'
            }
        else:  # 'square'
            a = random.randint(1, 10)
            exercise = {
                'question': f'¿Qué devuelve la llamada a la función?\n\n'
                           f'def cuadrado(x):\n'
                           f'    return x ** 2\n\n'
                           f'resultado = cuadrado({a})',
                'answer': str(a ** 2),
                'explanation': f'El cuadrado de {a} es {a ** 2}'
            }
        
        return exercise
    
    @staticmethod
    def _generate_type_conversion_exercise(id_num):
        """Genera ejercicio de conversión de tipos"""
        exercise_type = random.choice(['int', 'str'])
        
        if exercise_type == 'int':
            num = random.randint(1, 100)
            string_num = str(num)
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'numero = "{string_num}"\n'
                           f'resultado = int(numero)',
                'answer': string_num,
                'explanation': f'int() convierte el string "{string_num}" al número entero {string_num}'
            }
        else:  # 'str'
            num = random.randint(1, 100)
            string_num = str(num)
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'numero = {num}\n'
                           f'resultado = str(numero)',
                'answer': string_num,
                'explanation': f'str() convierte el número {num} al string "{string_num}"'
            }
        
        return exercise
    
    @staticmethod
    def generate_intermediate_exercises(count=300):
        """Genera ejercicios para nivel intermedio"""
        exercises = []
        
        for i in range(1, count + 1):
            exercise_type = random.choice([
                'list_comprehension', 'dictionaries', 'tuples', 
                'string_methods', 'exceptions', 'lambda', 'map_filter'
            ])
            
            if exercise_type == 'list_comprehension':
                exercise = ExerciseGenerator._generate_list_comprehension_exercise(i)
            elif exercise_type == 'dictionaries':
                exercise = ExerciseGenerator._generate_dictionary_exercise(i)
            elif exercise_type == 'tuples':
                exercise = ExerciseGenerator._generate_tuple_exercise(i)
            elif exercise_type == 'string_methods':
                exercise = ExerciseGenerator._generate_string_methods_exercise(i)
            elif exercise_type == 'exceptions':
                exercise = ExerciseGenerator._generate_exception_exercise(i)
            elif exercise_type == 'lambda':
                exercise = ExerciseGenerator._generate_lambda_exercise(i)
            elif exercise_type == 'map_filter':
                exercise = ExerciseGenerator._generate_map_filter_exercise(i)
            else:
                exercise = ExerciseGenerator._generate_basic_intermediate_exercise(i)
            
            # Generar opciones para el ejercicio
            answer = exercise['answer']
            answer_type = ExerciseGenerator._get_answer_type(answer)
            options = ExerciseGenerator._generate_options(answer, answer_type)
            
            # Encontrar el índice correcto
            correct_answer_index = ExerciseGenerator._find_correct_answer_index(options, answer)
            
            # Crear ejercicio con formato CORRECTO
            formatted_exercise = {
                'level': 'intermedio',  # Campo level requerido
                'question': exercise['question'],
                'options': options,
                'correct_answer': correct_answer_index,  # Índice numérico 1-4
                'explanation': exercise['explanation']
            }
            
            exercises.append(formatted_exercise)
        
        return exercises
    
    @staticmethod
    def _generate_list_comprehension_exercise(id_num):
        """Genera ejercicio de list comprehension"""
        exercise_type = random.choice(['squares', 'even'])
        
        if exercise_type == 'squares':
            start = random.randint(1, 10)
            end = start + random.randint(5, 15)
            exercise = {
                'question': f'¿Qué produce la siguiente list comprehension?\n\n'
                           f'cuadrados = [x**2 for x in range({start}, {end})]',
                'answer': str([x**2 for x in range(start, end)]),
                'explanation': f'Genera una lista con los cuadrados de los números del {start} al {end-1}'
            }
        else:  # 'even'
            start = random.randint(1, 10)
            end = start + random.randint(5, 15)
            exercise = {
                'question': f'¿Qué produce esta list comprehension?\n\n'
                           f'pares = [x for x in range({start}, {end}) if x % 2 == 0]',
                'answer': str([x for x in range(start, end) if x % 2 == 0]),
                'explanation': f'Genera una lista con los números pares del {start} al {end-1}'
            }
        
        return exercise
    
    @staticmethod
    def _generate_dictionary_exercise(id_num):
        """Genera ejercicio de diccionarios"""
        exercise_type = random.choice(['value', 'keys'])
        
        keys = ['nombre', 'edad', 'ciudad', 'profesion']
        values = [
            ['Juan', 'Ana', 'Carlos', 'María'],
            ['25', '30', '22', '35'],
            ['Madrid', 'Barcelona', 'Valencia', 'Sevilla'],
            ['Ingeniero', 'Doctor', 'Profesor', 'Arquitecto']
        ]
        
        idx = random.randint(0, 3)
        diccionario = {
            'nombre': values[0][idx],
            'edad': values[1][idx],
            'ciudad': values[2][idx],
            'profesion': values[3][idx]
        }
        
        if exercise_type == 'value':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'persona = {diccionario}\n'
                           f'resultado = persona["nombre"]',
                'answer': diccionario['nombre'],
                'explanation': f'Accede al valor de la clave "nombre" en el diccionario.'
            }
        else:  # 'keys'
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'persona = {diccionario}\n'
                           f'resultado = list(persona.keys())',
                'answer': str(list(diccionario.keys())),
                'explanation': f'persona.keys() devuelve las claves del diccionario.'
            }
        
        return exercise
    
    @staticmethod
    def _generate_tuple_exercise(id_num):
        """Genera ejercicio de tuplas"""
        exercise_type = random.choice(['first', 'len'])
        
        elementos = tuple(random.sample(range(1, 50), 5))
        
        if exercise_type == 'first':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'mi_tupla = {elementos}\n'
                           f'resultado = mi_tupla[0]',
                'answer': str(elementos[0]),
                'explanation': f'Accede al primer elemento de la tupla.'
            }
        else:  # 'len'
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'mi_tupla = {elementos}\n'
                           f'resultado = len(mi_tupla)',
                'answer': str(len(elementos)),
                'explanation': f'Devuelve la longitud de la tupla.'
            }
        
        return exercise
    
    @staticmethod
    def _generate_string_methods_exercise(id_num):
        """Genera ejercicio de métodos de strings"""
        exercise_type = random.choice(['strip', 'split'])
        
        texto = random.choice([
            '  python es genial  ',
            'HOLA MUNDO',
            'python, java, c++',
            'uno dos tres'
        ])
        
        if exercise_type == 'strip':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'texto = "{texto}"\n'
                           f'resultado = texto.strip()',
                'answer': texto.strip(),
                'explanation': f'strip() elimina espacios en blanco al inicio y final.'
            }
        else:  # 'split'
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'texto = "{texto}"\n'
                           f'resultado = texto.split()',
                'answer': str(texto.split()),
                'explanation': f'split() divide el string en una lista usando espacios como separador.'
            }
        
        return exercise
    
    @staticmethod
    def _generate_exception_exercise(id_num):
        """Genera ejercicio de excepciones"""
        a = random.randint(1, 10)
        b = random.choice([0, random.randint(1, 10)])
        
        exercise = {
            'question': f'¿Qué se imprime por pantalla?\n\n'
                       f'try:\n'
                       f'    resultado = {a} / {b}\n'
                       f'    print(resultado)\n'
                       f'except ZeroDivisionError:\n'
                       f'    print("Error: división por cero")',
            'answer': str(a / b) if b != 0 else "Error: división por cero",
            'explanation': f'Si b = 0, se produce ZeroDivisionError y se ejecuta el except.'
        }
        
        return exercise
    
    @staticmethod
    def _generate_lambda_exercise(id_num):
        """Genera ejercicio de funciones lambda"""
        exercise_type = random.choice(['sum', 'double'])
        
        if exercise_type == 'sum':
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'suma = lambda x, y: x + y\n'
                           f'resultado = suma({a}, {b})',
                'answer': str(a + b),
                'explanation': f'La función lambda suma dos números: {a} + {b} = {a + b}'
            }
        else:  # 'double'
            a = random.randint(1, 10)
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'doble = lambda x: x * 2\n'
                           f'resultado = doble({a})',
                'answer': str(a * 2),
                'explanation': f'La función lambda multiplica por 2: {a} * 2 = {a * 2}'
            }
        
        return exercise
    
    @staticmethod
    def _generate_map_filter_exercise(id_num):
        """Genera ejercicio de map y filter"""
        exercise_type = random.choice(['map', 'filter'])
        
        numeros = [random.randint(1, 20) for _ in range(5)]
        
        if exercise_type == 'map':
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'numeros = {numeros}\n'
                           f'resultado = list(map(lambda x: x * 2, numeros))',
                'answer': str([x * 2 for x in numeros]),
                'explanation': f'map aplica la función lambda (multiplicar por 2) a cada elemento.'
            }
        else:  # 'filter'
            exercise = {
                'question': f'¿Qué devuelve el siguiente código?\n\n'
                           f'numeros = {numeros}\n'
                           f'resultado = list(filter(lambda x: x % 2 == 0, numeros))',
                'answer': str([x for x in numeros if x % 2 == 0]),
                'explanation': f'filter selecciona solo los números pares.'
            }
        
        return exercise
    
    @staticmethod
    def _generate_basic_intermediate_exercise(id_num):
        """Genera ejercicio básico para tipos no implementados"""
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        
        exercise = {
            'question': f'¿Qué devuelve el siguiente código?\n\n'
                       f'resultado = {a} * {b} + {a}',
            'answer': str(a * b + a),
            'explanation': f'Operación aritmética: {a} × {b} + {a} = {a * b + a}'
        }
        
        return exercise
    
    @staticmethod
    def generate_advanced_exercises(count=150):
        """Genera ejercicios para nivel avanzado"""
        exercises = []
        
        for i in range(1, count + 1):
            exercise_type = random.choice(['oop', 'decorators', 'generators'])
            
            if exercise_type == 'oop':
                exercise = ExerciseGenerator._generate_oop_exercise(i)
            elif exercise_type == 'decorators':
                exercise = ExerciseGenerator._generate_decorator_exercise(i)
            elif exercise_type == 'generators':
                exercise = ExerciseGenerator._generate_generator_exercise(i)
            else:
                exercise = ExerciseGenerator._generate_basic_advanced_exercise(i)
            
            # Generar opciones para el ejercicio
            answer = exercise['answer']
            answer_type = ExerciseGenerator._get_answer_type(answer)
            options = ExerciseGenerator._generate_options(answer, answer_type)
            
            # Encontrar el índice correcto
            correct_answer_index = ExerciseGenerator._find_correct_answer_index(options, answer)
            
            # Crear ejercicio con formato CORRECTO
            formatted_exercise = {
                'level': 'avanzado',  # Campo level requerido
                'question': exercise['question'],
                'options': options,
                'correct_answer': correct_answer_index,  # Índice numérico 1-4
                'explanation': exercise['explanation']
            }
            
            exercises.append(formatted_exercise)
        
        return exercises
    
    @staticmethod
    def _generate_oop_exercise(id_num):
        """Genera ejercicio de Programación Orientada a Objetos"""
        exercise = {
            'question': f'¿Qué se imprime por pantalla?\n\n'
                       f'class Persona:\n'
                       f'    def __init__(self, nombre):\n'
                       f'        self.nombre = nombre\n\n'
                       f'    def saludar(self):\n'
                       f'        return f"Hola, soy {{self.nombre}}"\n\n'
                       f'p = Persona("Ana")\n'
                       f'print(p.saludar())',
            'answer': 'Hola, soy Ana',
            'explanation': f'Se crea una instancia de Persona y se llama al método saludar.'
        }
        
        return exercise
    
    @staticmethod
    def _generate_decorator_exercise(id_num):
        """Genera ejercicio de decoradores"""
        exercise = {
            'question': f'¿Qué se imprime por pantalla?\n\n'
                       f'def decorador(func):\n'
                       f'    def wrapper():\n'
                       f'        print("Antes de la función")\n'
                       f'        func()\n'
                       f'        print("Después de la función")\n'
                       f'    return wrapper\n\n'
                       f'@decorador\n'
                       f'def saludar():\n'
                       f'    print("¡Hola!")\n\n'
                       f'saludar()',
            'answer': 'Antes de la función\n¡Hola!\nDespués de la función',
            'explanation': f'El decorador envuelve la función y añade funcionalidad antes y después.'
        }
        
        return exercise
    
    @staticmethod
    def _generate_generator_exercise(id_num):
        """Genera ejercicio de generadores"""
        n = random.randint(3, 7)
        
        exercise = {
            'question': f'¿Qué se imprime por pantalla?\n\n'
                       f'def contador(maximo):\n'
                       f'    n = 1\n'
                       f'    while n <= maximo:\n'
                       f'        yield n\n'
                       f'        n += 1\n\n'
                       f'for numero in contador({n}):\n'
                       f'    print(numero)',
            'answer': '\n'.join(str(i) for i in range(1, n + 1)),
            'explanation': f'El generador produce números del 1 al {n}.'
        }
        
        return exercise
    
    @staticmethod
    def _generate_basic_advanced_exercise(id_num):
        """Genera ejercicio básico para nivel avanzado"""
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        
        exercise = {
            'question': f'¿Qué devuelve el siguiente código?\n\n'
                       f'resultado = ({a} ** {b}) // {a}',
            'answer': str((a ** b) // a),
            'explanation': f'Operación avanzada: {a}^{b} // {a} = {(a ** b) // a}'
        }
        
        return exercise
    
    @staticmethod
    def generate_expert_exercises(count=100):
        """Genera ejercicios para nivel experto"""
        exercises = []
        
        for i in range(1, count + 1):
            exercise = ExerciseGenerator._generate_expert_basic_exercise(i)
            
            # Generar opciones para el ejercicio
            answer = exercise['answer']
            answer_type = ExerciseGenerator._get_answer_type(answer)
            options = ExerciseGenerator._generate_options(answer, answer_type)
            
            # Encontrar el índice correcto
            correct_answer_index = ExerciseGenerator._find_correct_answer_index(options, answer)
            
            # Crear ejercicio con formato CORRECTO
            formatted_exercise = {
                'level': 'experto',  # Campo level requerido
                'question': exercise['question'],
                'options': options,
                'correct_answer': correct_answer_index,  # Índice numérico 1-4
                'explanation': exercise['explanation']
            }
            
            exercises.append(formatted_exercise)
        
        return exercises
    
    @staticmethod
    def _generate_expert_basic_exercise(id_num):
        """Genera ejercicio básico para nivel experto"""
        a = random.randint(2, 10)
        b = random.randint(2, 10)
        
        exercise = {
            'question': f'¿Qué devuelve el siguiente código?\n\n'
                       f'resultado = ({a} ** {b}) % ({a} + {b})',
            'answer': str((a ** b) % (a + b)),
            'explanation': f'Operación experta: ({a}^{b}) % ({a} + {b}) = {(a ** b) % (a + b)}'
        }
        
        return exercise
    
    @staticmethod
    def generate_all_exercises():
        """Genera todos los ejercicios para todos los niveles - VERSIÓN CORREGIDA"""
        print("\n" + "="*60)
        print("GENERANDO EJERCICIOS CORREGIDOS PARA TODOS LOS NIVELES")
        print("="*60)
        
        # Crear directorio si no existe
        data_dir = Path('exercises/exercises_data')
        data_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            print("\nGenerando ejercicios para nivel Principiante...")
            beginner = ExerciseGenerator.generate_beginner_exercises(300)
            
            print("Generando ejercicios para nivel Intermedio...")
            intermediate = ExerciseGenerator.generate_intermediate_exercises(300)
            
            print("Generando ejercicios para nivel Avanzado...")
            advanced = ExerciseGenerator.generate_advanced_exercises(150)
            
            print("Generando ejercicios para nivel Experto...")
            expert = ExerciseGenerator.generate_expert_exercises(100)
            
            # Verificar que todos los ejercicios tienen el formato CORRECTO
            print("\nVerificando formato CORREGIDO de los ejercicios...")
            
            all_exercises = {
                'beginner': beginner,
                'intermediate': intermediate,
                'advanced': advanced,
                'expert': expert
            }
            
            for level, exercises in all_exercises.items():
                valid_count = 0
                for ex in exercises:
                    # Verificar formato CORRECTO
                    if ('level' in ex and 
                        'options' in ex and 
                        'correct_answer' in ex and 
                        isinstance(ex['correct_answer'], int) and
                        1 <= ex['correct_answer'] <= 4):
                        valid_count += 1
                print(f"   {level}: {valid_count}/{len(exercises)} ejercicios con formato CORRECTO")
            
            # Guardar en archivos JSON
            print("\nGuardando ejercicios CORREGIDOS en archivos JSON...")
            
            with open(data_dir / 'beginner.json', 'w', encoding='utf-8') as f:
                json.dump(beginner, f, indent=2, ensure_ascii=False)
            print(f"   beginner.json: {len(beginner)} ejercicios CORREGIDOS")
            
            with open(data_dir / 'intermediate.json', 'w', encoding='utf-8') as f:
                json.dump(intermediate, f, indent=2, ensure_ascii=False)
            print(f"   intermediate.json: {len(intermediate)} ejercicios CORREGIDOS")
            
            with open(data_dir / 'advanced.json', 'w', encoding='utf-8') as f:
                json.dump(advanced, f, indent=2, ensure_ascii=False)
            print(f"   advanced.json: {len(advanced)} ejercicios CORREGIDOS")
            
            with open(data_dir / 'expert.json', 'w', encoding='utf-8') as f:
                json.dump(expert, f, indent=2, ensure_ascii=False)
            print(f"   expert.json: {len(expert)} ejercicios CORREGIDOS")
            
            total = len(beginner) + len(intermediate) + len(advanced) + len(expert)
            
            print("\n" + "="*60)
            print(f"EJERCICIOS CORREGIDOS GENERADOS EXITOSAMENTE!")
            print("="*60)
            print(f"TOTAL: {total} ejercicios generados con formato CORRECTO")
            print(f"   • Principiante: {len(beginner)} ejercicios")
            print(f"   • Intermedio: {len(intermediate)} ejercicios")
            print(f"   • Avanzado: {len(advanced)} ejercicios")
            print(f"   • Experto: {len(expert)} ejercicios")
            print("\nCAMBIOS REALIZADOS:")
            print("   • Campo 'difficulty' -> 'level' (string)")
            print("   • Eliminados campos: 'id', 'type', 'answer'")
            print("   • 'correct_answer' como indice numerico (1-4)")
            print("   • Formato compatible con la base de datos")
            print("   • Listos para importar en la pagina web")
            print("="*60)
            
            return {
                'beginner': len(beginner),
                'intermediate': len(intermediate),
                'advanced': len(advanced),
                'expert': len(expert),
                'total': total
            }
            
        except Exception as e:
            print(f"\nERROR al generar ejercicios: {e}")
            import traceback
            traceback.print_exc()
            
            # Crear archivos vacíos como fallback
            print("\nCreando archivos vacios como respaldo...")
            for level in ['beginner', 'intermediate', 'advanced', 'expert']:
                file_path = data_dir / f'{level}.json'
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('[]')
                print(f"   • {level}.json creado (vacio)")
            
            return {
                'beginner': 0,
                'intermediate': 0,
                'advanced': 0,
                'expert': 0,
                'total': 0
            }

def main():
    """Función principal para ejecutar el generador directamente"""
    print("Generador de Ejercicios CORREGIDO - Python Learning Bot")
    print("=" * 50)
    print("VERSION CORREGIDA:")
    print("   • Formato compatible con la base de datos")
    print("   • Campo 'level' en lugar de 'difficulty'")
    print("   • 'correct_answer' como indice numerico")
    print("   • Sin campos innecesarios")
    print("=" * 50)
    
    result = ExerciseGenerator.generate_all_exercises()
    
    if result['total'] > 0:
        print("\nEjercicios CORREGIDOS generados exitosamente!")
        print(f"Ubicacion: exercises/exercises_data/")
        print("\nLos ejercicios ahora tienen el formato CORRECTO:")
        print("   • 'level': string ('principiante', 'intermedio', etc.)")
        print("   • 'correct_answer': numero (1-4)")
        print("   • 'options': array de 4 strings")
        print("   • Sin 'id', 'type', 'answer' innecesarios")
        print("   Listos para importar en la pagina web")
    else:
        print("\nSe crearon archivos vacios. Revisa los errores.")

if __name__ == '__main__':
    main()
