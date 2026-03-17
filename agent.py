#!/usr/bin/env python
"""
Простой агент для Task 1.
Отправляет вопросы в Qwen API и получает ответы.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Шаг 1: Загружаем настройки из файла .env.agent.secret
load_dotenv('.env.agent.secret')

def call_llm(question):
    """Отправляет вопрос в LLM и возвращает ответ"""
    
    # Читаем настройки
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    # Проверяем, что все настройки есть
    if not api_key or not api_base or not model:
        error_msg = "Ошибка: не все настройки найдены в .env.agent.secret"
        print(error_msg, file=sys.stderr)
        return {
            "answer": error_msg,
            "tool_calls": []
        }
    
    # Готовим запрос к API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Тело запроса с вопросом пользователя
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ],
        "temperature": 0.7
    }
    
    # Отправляем запрос
    try:
        # Формируем полный адрес для запроса
        url = f"{api_base}/chat/completions"
        print(f"Отправляю запрос на {url}", file=sys.stderr)
        
        # Отправляем POST-запрос
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30  # Ждем ответ максимум 30 секунд
        )
        
        # Проверяем, что запрос успешен
        response.raise_for_status()
        
        # Получаем ответ от API
        result = response.json()
        
        # Извлекаем текст ответа
        answer = result['choices'][0]['message']['content']
        
        # Возвращаем результат в нужном формате
        return {
            "answer": answer,
            "tool_calls": []  # Пока пустой список
        }
        
    except requests.exceptions.ConnectionError:
        error = f"Ошибка: не могу подключиться к {api_base}. Проверьте, запущен ли Qwen API на ВМ"
        print(error, file=sys.stderr)
        return {"answer": error, "tool_calls": []}
        
    except requests.exceptions.Timeout:
        error = "Ошибка: превышено время ожидания ответа от API"
        print(error, file=sys.stderr)
        return {"answer": error, "tool_calls": []}
        
    except Exception as e:
        error = f"Ошибка при вызове API: {str(e)}"
        print(error, file=sys.stderr)
        return {
            "answer": error,
            "tool_calls": []
        }

def main():
    """Главная функция программы"""
    
    # Проверяем, что передан ровно один аргумент (вопрос)
    if len(sys.argv) != 2:
        print("Как использовать: uv run agent.py 'Ваш вопрос здесь'", file=sys.stderr)
        print("Пример: uv run agent.py 'Что такое REST?'", file=sys.stderr)
        sys.exit(1)
    
    # Получаем вопрос из командной строки
    question = sys.argv[1]
    
    # Выводим отладочную информацию в stderr
    print(f"Получен вопрос: {question}", file=sys.stderr)
    
    # Получаем ответ от LLM
    result = call_llm(question)
    
    # Выводим результат в формате JSON (только это идет в stdout)
    print(json.dumps(result, ensure_ascii=False))

# Это стандартная конструкция для Python-программ
if __name__ == "__main__":
    main()