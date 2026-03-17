import subprocess
import json

def test_agent_basic():
    """Проверяем, что агент работает и возвращает правильный JSON"""
    
    # Запускаем агента с простым вопросом
    result = subprocess.run(
        ["uv", "run", "agent.py", "Сколько будет 2+2?"],
        capture_output=True,
        text=True
    )
    
    # Проверяем, что программа завершилась успешно
    assert result.returncode == 0, f"Программа вернула ошибку: {result.stderr}"
    
    # Пробуем распарсить JSON из stdout
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f"Вывод не является JSON: {result.stdout}"
    
    # Проверяем, что в JSON есть нужные поля
    assert "answer" in output, "В ответе нет поля answer"
    assert "tool_calls" in output, "В ответе нет поля tool_calls"
    assert isinstance(output["tool_calls"], list), "tool_calls должен быть списком"
    
    print("Тест пройден успешно!")

# Это нужно, чтобы тест можно было запустить как обычную программу
if __name__ == "__main__":
    test_agent_basic()
    print("Все тесты пройдены!")