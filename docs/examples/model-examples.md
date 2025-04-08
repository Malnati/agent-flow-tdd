# Exemplos de Uso dos Modelos

Este documento contém exemplos práticos de uso dos diferentes modelos disponíveis no Agent Flow TDD, com casos de uso específicos para cada tipo de modelo.

## TinyLLaMA (1.1B)

### Exemplo 1: Geração de Testes Unitários

```bash
make tdd prompt="Criar testes unitários para uma função que valida CPF" model=tinyllama-1.1b format=python
```

**Saída:**
```python
# test_cpf_validator.py
import unittest
from cpf_validator import validate_cpf

class TestCPFValidator(unittest.TestCase):
    def test_valid_cpf(self):
        self.assertTrue(validate_cpf("529.982.247-25"))
        self.assertTrue(validate_cpf("52998224725"))
        
    def test_invalid_cpf(self):
        self.assertFalse(validate_cpf("111.111.111-11"))
        self.assertFalse(validate_cpf("123.456.789-10"))
        
    def test_invalid_format(self):
        self.assertFalse(validate_cpf("abc.def.ghi-jk"))
        self.assertFalse(validate_cpf(""))
        self.assertFalse(validate_cpf(None))
```

### Exemplo 2: Debugging de Código Simples

```bash
make tdd prompt="Encontrar e corrigir erros no seguinte código Python:
def calcular_media(numeros):
    total = 0
    for num in numeros
        total += num
    return total / len(numeros)" model=tinyllama-1.1b format=python
```

**Saída:**
```python
# Código corrigido:
def calcular_media(numeros):
    total = 0
    for num in numeros:  # Erro corrigido: faltava dois pontos após a condição do loop
        total += num
    
    # Tratamento para evitar divisão por zero
    if len(numeros) == 0:
        return 0
    
    return total / len(numeros)
```

## Phi-2 (2.7B)

### Exemplo 1: Criação de API REST Simples

```bash
make tdd prompt="Criar uma API REST em Flask para gerenciar uma lista de tarefas" model=phi2 format=python
```

**Saída:**
```python
# app.py
from flask import Flask, request, jsonify

app = Flask(__name__)

# Armazenamento em memória para tarefas
tasks = []
task_id_counter = 1

@app.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def create_task():
    global task_id_counter
    data = request.json
    
    if not data or 'title' not in data:
        return jsonify({"error": "Título da tarefa é obrigatório"}), 400
        
    new_task = {
        'id': task_id_counter,
        'title': data['title'],
        'description': data.get('description', ''),
        'completed': False
    }
    
    tasks.append(new_task)
    task_id_counter += 1
    
    return jsonify(new_task), 201

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task:
        return jsonify(task)
    return jsonify({"error": "Tarefa não encontrada"}), 404

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        return jsonify({"error": "Tarefa não encontrada"}), 404
        
    task['title'] = data.get('title', task['title'])
    task['description'] = data.get('description', task['description'])
    task['completed'] = data.get('completed', task['completed'])
    
    return jsonify(task)

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        return jsonify({"error": "Tarefa não encontrada"}), 404
        
    tasks = [t for t in tasks if t['id'] != task_id]
    return jsonify({"message": "Tarefa removida com sucesso"})

if __name__ == '__main__':
    app.run(debug=True)
```

### Exemplo 2: Refatoração de Código

```bash
make tdd prompt="Refatorar o seguinte código para usar programação funcional:
def processar_lista(numeros):
    resultado = []
    for numero in numeros:
        if numero % 2 == 0:
            resultado.append(numero * 2)
    return resultado" model=phi2 format=python
```

**Saída:**
```python
# Código refatorado usando programação funcional
def processar_lista(numeros):
    return list(map(lambda x: x * 2, filter(lambda x: x % 2 == 0, numeros)))

# Versão alternativa usando list comprehension
def processar_lista_alt(numeros):
    return [numero * 2 for numero in numeros if numero % 2 == 0]
```

## DeepSeek Coder (6.7B)

### Exemplo 1: Desenvolvimento de Biblioteca Complexa

```bash
make tdd prompt="Desenvolver uma biblioteca Python para análise de sentimento em textos, com suporte a diferentes idiomas" model=deepseek_local format=python
```

**Saída:**
```python
# sentiment_analyzer.py
import re
import json
import os
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict

class SentimentAnalyzer:
    """
    Biblioteca para análise de sentimento em diferentes idiomas.
    Implementa análise baseada em dicionário léxico e heurísticas simples.
    """
    
    def __init__(self, languages: List[str] = ['pt', 'en', 'es']):
        """
        Inicializa o analisador de sentimento com os idiomas desejados.
        
        Args:
            languages: Lista de códigos de idioma no formato ISO 639-1
        """
        self.languages = languages
        self.lexicons = {}
        self.intensifiers = {}
        self.negation_words = {}
        
        # Carregar lexicons para cada idioma
        for lang in languages:
            self._load_resources(lang)
    
    def _load_resources(self, language: str) -> None:
        """
        Carrega recursos linguísticos para o idioma especificado.
        
        Args:
            language: Código do idioma
        """
        # Caminhos para os arquivos de recursos
        base_path = os.path.dirname(os.path.abspath(__file__))
        resources_path = os.path.join(base_path, 'resources', language)
        
        # Carregar lexicon de sentimento (ou criar um vazio se não existir)
        lexicon_path = os.path.join(resources_path, 'lexicon.json')
        if os.path.exists(lexicon_path):
            with open(lexicon_path, 'r', encoding='utf-8') as f:
                self.lexicons[language] = json.load(f)
        else:
            # Lexicon mínimo para demonstração
            self.lexicons[language] = self._get_default_lexicon(language)
        
        # Carregar palavras de intensificação
        intensifiers_path = os.path.join(resources_path, 'intensifiers.json')
        if os.path.exists(intensifiers_path):
            with open(intensifiers_path, 'r', encoding='utf-8') as f:
                self.intensifiers[language] = json.load(f)
        else:
            self.intensifiers[language] = self._get_default_intensifiers(language)
        
        # Carregar palavras de negação
        negation_path = os.path.join(resources_path, 'negation.json')
        if os.path.exists(negation_path):
            with open(negation_path, 'r', encoding='utf-8') as f:
                self.negation_words[language] = json.load(f)
        else:
            self.negation_words[language] = self._get_default_negation(language)
    
    def _get_default_lexicon(self, language: str) -> Dict[str, float]:
        """Retorna um lexicon padrão mínimo para demonstração."""
        if language == 'pt':
            return {
                "bom": 0.7, "ótimo": 0.9, "excelente": 1.0, "ruim": -0.7, 
                "péssimo": -0.9, "terrível": -1.0, "feliz": 0.8, "triste": -0.8
            }
        elif language == 'en':
            return {
                "good": 0.7, "great": 0.9, "excellent": 1.0, "bad": -0.7,
                "terrible": -1.0, "awful": -0.9, "happy": 0.8, "sad": -0.8
            }
        elif language == 'es':
            return {
                "bueno": 0.7, "genial": 0.9, "excelente": 1.0, "malo": -0.7,
                "terrible": -1.0, "pésimo": -0.9, "feliz": 0.8, "triste": -0.8
            }
        return {}
    
    def _get_default_intensifiers(self, language: str) -> Dict[str, float]:
        """Retorna intensificadores padrão para demonstração."""
        if language == 'pt':
            return {"muito": 1.5, "extremamente": 2.0, "pouco": 0.5}
        elif language == 'en':
            return {"very": 1.5, "extremely": 2.0, "slightly": 0.5}
        elif language == 'es':
            return {"muy": 1.5, "extremadamente": 2.0, "poco": 0.5}
        return {}
    
    def _get_default_negation(self, language: str) -> List[str]:
        """Retorna palavras de negação padrão para demonstração."""
        if language == 'pt':
            return ["não", "nunca", "jamais", "nem"]
        elif language == 'en':
            return ["not", "never", "no", "neither"]
        elif language == 'es':
            return ["no", "nunca", "jamás", "ni"]
        return []
    
    def detect_language(self, text: str) -> str:
        """
        Detecta o idioma do texto com base nos lexicons disponíveis.
        Método simples baseado na contagem de palavras do lexicon.
        
        Args:
            text: Texto para detecção de idioma
            
        Returns:
            Código do idioma detectado, ou o primeiro idioma disponível como fallback
        """
        if not text or not self.languages:
            return self.languages[0] if self.languages else 'en'
        
        # Tokenizar o texto em palavras
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Contar matches de palavras para cada idioma
        lang_scores = defaultdict(int)
        for lang in self.languages:
            lexicon = self.lexicons.get(lang, {})
            for word in words:
                if word in lexicon:
                    lang_scores[lang] += 1
        
        # Retornar o idioma com mais matches
        if lang_scores:
            return max(lang_scores.items(), key=lambda x: x[1])[0]
        
        # Fallback para o primeiro idioma
        return self.languages[0] if self.languages else 'en'
    
    def analyze(self, text: str, language: Optional[str] = None) -> Dict[str, Union[float, str]]:
        """
        Analisa o sentimento de um texto.
        
        Args:
            text: Texto para análise
            language: Código do idioma (se None, será detectado automaticamente)
            
        Returns:
            Dicionário com os resultados da análise
        """
        if not text:
            return {
                "score": 0.0,
                "sentiment": "neutral",
                "language": language or self.languages[0]
            }
        
        # Detectar idioma se não especificado
        if language is None or language not in self.languages:
            language = self.detect_language(text)
        
        # Tokenizar o texto
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Recursos para o idioma
        lexicon = self.lexicons.get(language, {})
        intensifiers = self.intensifiers.get(language, {})
        negation_words = self.negation_words.get(language, [])
        
        # Analisar o sentimento
        score = 0.0
        negation_active = False
        intensifier_value = 1.0
        
        for i, word in enumerate(words):
            # Verificar se é uma palavra de negação
            if word in negation_words:
                negation_active = True
                continue
            
            # Verificar se é um intensificador
            if word in intensifiers:
                intensifier_value = intensifiers[word]
                continue
            
            # Verificar se a palavra está no lexicon
            if word in lexicon:
                word_score = lexicon[word]
                
                # Aplicar negação se ativa
                if negation_active:
                    word_score = -word_score
                    negation_active = False
                
                # Aplicar intensificador
                word_score *= intensifier_value
                intensifier_value = 1.0  # Resetar intensificador
                
                # Adicionar à pontuação total
                score += word_score
        
        # Classificar o sentimento
        sentiment = "neutral"
        if score > 0.05:
            sentiment = "positive"
        elif score < -0.05:
            sentiment = "negative"
        
        return {
            "score": round(score, 2),
            "sentiment": sentiment,
            "language": language
        }
    
    def batch_analyze(self, texts: List[str], language: Optional[str] = None) -> List[Dict[str, Union[float, str]]]:
        """
        Analisa o sentimento de múltiplos textos.
        
        Args:
            texts: Lista de textos para análise
            language: Código do idioma (se None, será detectado individualmente)
            
        Returns:
            Lista de dicionários com os resultados da análise
        """
        return [self.analyze(text, language) for text in texts]

# Exemplo de uso
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    # Exemplos em diferentes idiomas
    texts = [
        "Estou muito feliz com o resultado do projeto!",  # Português
        "This product is terrible, I would never buy it again.",  # Inglês
        "La película fue muy buena, me encantó."  # Espanhol
    ]
    
    for text in texts:
        result = analyzer.analyze(text)
        print(f"Texto: {text}")
        print(f"Idioma detectado: {result['language']}")
        print(f"Sentimento: {result['sentiment']} (score: {result['score']})")
        print("---")
```

### Exemplo 2: Implementação de Algoritmo Complexo

```bash
make tdd prompt="Implementar o algoritmo A* para encontrar o caminho mais curto em um grafo" model=deepseek_local format=python
```

**Saída:**
```python
# astar.py
import heapq
from typing import Dict, List, Tuple, Callable, TypeVar, Set, Optional

T = TypeVar('T')  # Tipo genérico para representar os nós do grafo

class AStar:
    """
    Implementação do algoritmo A* para encontrar o caminho mais curto em um grafo.
    """
    
    @staticmethod
    def find_path(
        start: T,
        goal: T,
        neighbors_fn: Callable[[T], List[T]],
        heuristic_fn: Callable[[T, T], float],
        cost_fn: Callable[[T, T], float] = lambda a, b: 1.0,
        max_iterations: int = 10000
    ) -> Optional[Tuple[List[T], float]]:
        """
        Encontra o caminho mais curto do nó inicial ao nó objetivo usando o algoritmo A*.
        
        Args:
            start: Nó inicial
            goal: Nó objetivo
            neighbors_fn: Função que retorna os vizinhos de um nó
            heuristic_fn: Função heurística que estima a distância até o objetivo
            cost_fn: Função que retorna o custo de mover de um nó para outro
            max_iterations: Número máximo de iterações para evitar loops infinitos
            
        Returns:
            Tupla contendo o caminho (lista de nós) e o custo total, ou None se não for possível 
            encontrar um caminho
        """
        # Conjunto de nós já avaliados
        closed_set: Set[T] = set()
        
        # Conjunto de nós descobertos que ainda precisam ser avaliados
        open_set: Set[T] = {start}
        
        # Fila de prioridade para selecionar o próximo nó a ser avaliado
        # Cada item é uma tupla (f_score, contador, nó), onde contador é usado para
        # desempatar nós com o mesmo f_score e garantir uma ordem determinística
        counter = 0
        open_heap = [(heuristic_fn(start, goal), counter, start)]
        
        # Para cada nó, o nó que o precede no caminho mais eficiente conhecido
        came_from: Dict[T, T] = {}
        
        # Para cada nó, o custo do caminho mais eficiente conhecido do início até o nó
        g_score: Dict[T, float] = {start: 0.0}
        
        # Para cada nó, o custo total estimado do caminho através do nó até o objetivo
        f_score: Dict[T, float] = {start: heuristic_fn(start, goal)}
        
        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Obter o nó com menor f_score
            _, _, current = heapq.heappop(open_heap)
            
            # Verificar se o nó ainda está na lista aberta
            if current not in open_set:
                continue
            
            # Se o objetivo foi alcançado, reconstruir e retornar o caminho
            if current == goal:
                path = AStar._reconstruct_path(came_from, current)
                return path, g_score[current]
            
            # Remover o nó atual da lista aberta e adicioná-lo à lista fechada
            open_set.remove(current)
            closed_set.add(current)
            
            # Avaliar cada vizinho
            for neighbor in neighbors_fn(current):
                # Ignorar vizinhos que já foram avaliados
                if neighbor in closed_set:
                    continue
                
                # Calcular tentativa de g_score
                tentative_g_score = g_score[current] + cost_fn(current, neighbor)
                
                # Verificar se o vizinho é novo ou se encontramos um caminho melhor
                if neighbor not in open_set:
                    open_set.add(neighbor)
                elif tentative_g_score >= g_score.get(neighbor, float('inf')):
                    continue
                
                # Este é o melhor caminho até agora, registrar
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic_fn(neighbor, goal)
                
                # Adicionar à fila de prioridade
                counter += 1
                heapq.heappush(open_heap, (f_score[neighbor], counter, neighbor))
        
        # Se chegamos aqui, não foi possível encontrar um caminho
        return None
    
    @staticmethod
    def _reconstruct_path(came_from: Dict[T, T], current: T) -> List[T]:
        """
        Reconstrói o caminho do nó inicial ao nó atual.
        
        Args:
            came_from: Dicionário mapeando cada nó ao nó que o precede no caminho
            current: Nó atual (objetivo)
            
        Returns:
            Lista de nós representando o caminho do início ao objetivo
        """
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return list(reversed(total_path))


# Exemplo de uso: encontrar caminho em uma grade 2D
def example_grid_path():
    # Definir uma grade 2D com obstáculos (1 = obstáculo, 0 = caminho livre)
    grid = [
        [0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 0]
    ]
    
    # Ponto inicial e objetivo
    start = (0, 0)
    goal = (4, 5)
    
    # Função para obter vizinhos válidos (4 direções: cima, baixo, esquerda, direita)
    def get_neighbors(node):
        row, col = node
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # direita, baixo, esquerda, cima
        neighbors = []
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            
            # Verificar se está dentro dos limites da grade e não é um obstáculo
            if (0 <= new_row < len(grid) and 
                0 <= new_col < len(grid[0]) and 
                grid[new_row][new_col] == 0):
                neighbors.append((new_row, new_col))
        
        return neighbors
    
    # Heurística: distância de Manhattan
    def manhattan_distance(node, goal):
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])
    
    # Encontrar o caminho
    result = AStar.find_path(start, goal, get_neighbors, manhattan_distance)
    
    if result:
        path, cost = result
        print(f"Caminho encontrado com custo {cost}:")
        for node in path:
            print(node)
        
        # Visualizar o caminho na grade
        path_grid = [row[:] for row in grid]  # Fazer uma cópia da grade
        for row, col in path:
            path_grid[row][col] = 2  # Marcar o caminho com 2
        
        # Exibir a grade com o caminho
        symbols = {0: ".", 1: "#", 2: "*"}
        print("\nVisualizando caminho na grade (. = livre, # = obstáculo, * = caminho):")
        for row in path_grid:
            print("".join(symbols[cell] for cell in row))
    else:
        print("Não foi possível encontrar um caminho.")

if __name__ == "__main__":
    example_grid_path()
```

## GPT-4 (API OpenAI)

### Exemplo 1: Criação de Aplicação Web Completa

```bash
make tdd prompt="Criar uma aplicação web Flask para gerenciamento de biblioteca, com autenticação de usuários, banco de dados SQLite e templates" model=gpt-4-turbo format=python
```

**Saída:**
A resposta seria um projeto completo com múltiplos arquivos (app.py, modelos, templates, etc). Aqui está um exemplo parcial da estrutura gerada:

```
biblioteca_app/
├── app.py
├── config.py
├── models/
│   ├── __init__.py
│   ├── book.py
│   └── user.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── scripts.js
├── templates/
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── books/
│   │   ├── add.html
│   │   ├── detail.html
│   │   ├── edit.html
│   │   └── index.html
│   ├── base.html
│   └── index.html
└── requirements.txt
```

### Exemplo 2: Otimização de Algoritmo

```bash
make tdd prompt="Otimizar o seguinte algoritmo de ordenação:
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr" model=gpt-4-turbo format=python
```

**Saída:**
```python
def optimized_bubble_sort(arr):
    """
    Versão otimizada do Bubble Sort com as seguintes melhorias:
    1. Flag para detectar quando nenhuma troca foi realizada (array já ordenado)
    2. Redução da parte já ordenada a cada iteração
    3. Verificação inicial de casos triviais (lista vazia ou com um elemento)
    
    Complexidade:
    - Melhor caso: O(n) quando o array já está ordenado
    - Caso médio: O(n²)
    - Pior caso: O(n²)
    """
    # Caso trivial
    n = len(arr)
    if n <= 1:
        return arr
    
    # Cópia para não modificar o original (remover se não for necessário)
    arr = arr.copy()
    
    # Flag para otimização
    swapped = True
    
    # Limite superior que diminui a cada passagem completa
    end = n - 1
    
    while swapped:
        swapped = False
        for i in range(end):
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                swapped = True
        
        # Reduzir o limite, pois o maior elemento já está no lugar certo
        end -= 1
    
    return arr

# Versão alternativa usando um algoritmo de ordenação mais eficiente
def efficient_sort(arr):
    """
    Implementação do algoritmo Timsort (usado pelo sorted() do Python)
    Complexidade: O(n log n) em todos os casos
    """
    return sorted(arr)

# Benchmark para comparar as implementações
import time
import random

def benchmark(sort_functions, sizes=[100, 1000, 10000]):
    results = {}
    
    for name, func in sort_functions.items():
        results[name] = []
        
        for size in sizes:
            # Criar array aleatório
            arr = [random.randint(0, 10000) for _ in range(size)]
            
            # Medir tempo
            start = time.time()
            func(arr)
            end = time.time()
            
            results[name].append((size, end - start))
    
    # Exibir resultados
    print("Tamanho | " + " | ".join(sort_functions.keys()))
    print("--------|" + "|".join(["-" * (len(name) + 2) for name in sort_functions]))
    
    for i, size in enumerate(sizes):
        times = [f"{results[name][i][1]:.6f}s" for name in sort_functions]
        print(f"{size:8d} | " + " | ".join(times))

if __name__ == "__main__":
    # Comparar as implementações
    benchmark({
        "bubble_sort": bubble_sort,
        "optimized_bubble": optimized_bubble_sort,
        "efficient_sort": efficient_sort
    })
```

## Conclusão

Cada modelo tem suas vantagens em diferentes cenários:

- **TinyLLaMA (1.1B)**: Ideal para tarefas simples de debugging, geração de testes unitários e scripts básicos.
- **Phi-2 (2.7B)**: Bom equilíbrio para APIs simples, refatoração e componentes web básicos.
- **DeepSeek Coder (6.7B)**: Melhor para implementações complexas, bibliotecas completas e algoritmos avançados.
- **GPT-4/Claude**: Excelentes para projetos completos com múltiplos arquivos, otimizações avançadas, e código de produção.

Para obter os melhores resultados, recomendamos começar com o modelo mais simples que atenda às suas necessidades e só escalar para modelos maiores quando necessário. 