"""
Класс для анализа логов с помощью LLM
"""

import requests
from PySide6.QtCore import QThread, Signal
from core.constants import logger
from core.prompts import DEFAULT_LOG_ANALYSIS_PROMPT
from dotenv import load_dotenv
import os

class LLMAnalyzer(QThread):
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, api_url, api_key, log_text, vectorizer):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.log_text = log_text
        self.vectorizer = vectorizer
        logger.debug("Инициализация LLMAnalyzer")
        
    def run(self):
        try:
            logger.debug("Начало анализа с помощью LLM")
            
            # Загружаем промпт из переменных окружения на случай, если он был изменен
            load_dotenv(override=True)
            
            # Получаем актуальный промпт или используем стандартный
            current_prompt = os.getenv('LLM_PROMPT', DEFAULT_LOG_ANALYSIS_PROMPT)
            logger.debug(f"Загружен пользовательский промпт, длина: {len(current_prompt)}")
            
            embeddings = self.vectorizer.get_embeddings(self.log_text)
            logger.debug("Получены эмбеддинги")
            
            similar_logs = self.vectorizer.search(embeddings, k=2)
            logger.debug("Найдены похожие логи")
            
            max_chars = 2000
            truncated_logs = self.log_text[:max_chars] + "..." if len(self.log_text) > max_chars else self.log_text
            truncated_similar = similar_logs[:max_chars] + "..." if len(similar_logs) > max_chars else similar_logs
            
            # Формируем промпт, используя актуальный шаблон
            prompt = current_prompt.format(
                current_logs=truncated_logs,
                similar_logs=truncated_similar
            )
            
            logger.debug("Отправка запроса к LLM")
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            data = {
                "model": "default",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": os.getenv('LLM_TEMPERATURE'),
                "max_tokens": os.getenv('LLM_MAX_TOKENS')
            }
            
            # Коррекция URL
            endpoint = "/v1/chat/completions"
            if self.api_url.endswith(endpoint):
                api_url = self.api_url
            elif self.api_url.endswith("/"):
                api_url = f"{self.api_url[:-1]}{endpoint}"
            else:
                api_url = f"{self.api_url}{endpoint}"
                
            logger.debug(f"Отправка запроса на URL: {api_url}")
            logger.debug(f"Длина запроса: {len(prompt)} символов")
            
            # Отправляем запрос
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Получен ответ API: {str(result)[:200]}...")
            
            analysis = "Не удалось получить ответ от LLM"
            
            # Проверяем различные варианты структуры ответа
            if isinstance(result, dict):
                if "choices" in result and len(result["choices"]) > 0:
                    # Стандартный формат OpenAI
                    if "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                        analysis = result["choices"][0]["message"]["content"]
                        logger.debug(f"Извлечен ответ в формате OpenAI, длина: {len(analysis)}")
                        logger.debug(f"Начало ответа: {analysis[:100]}...")
                        logger.debug(f"Конец ответа: ...{analysis[-100:]}")
                    # Альтернативные форматы
                    elif "text" in result["choices"][0]:
                        analysis = result["choices"][0]["text"]
                        logger.debug(f"Извлечен ответ из поля text, длина: {len(analysis)}")
                # LM Studio может использовать свой формат
                elif "response" in result:
                    analysis = result["response"]
                    logger.debug(f"Извлечен ответ из поля response, длина: {len(analysis)}")
                
            # Если ничего не нашли, используем весь ответ как текст
            if analysis == "Не удалось получить ответ от LLM":
                logger.warning("Не удалось извлечь ответ из стандартных полей, использую сырой ответ")
                analysis = str(result)
                logger.debug(f"Сырой ответ, длина: {len(analysis)}")
                
            # Проверяем целостность ответа
            if analysis and analysis[-1:] in {'.', '!', '?', ':', ';', ','}:
                logger.debug("Ответ выглядит завершенным (заканчивается знаком препинания)")
            else:
                logger.warning("Ответ может быть обрезан (не заканчивается знаком препинания)")
                
            logger.debug("Получен ответ от LLM")
            
            # Дополнительная обработка для случаев, когда ответ обрезан
            if len(analysis) >= 1900:  # Если ответ близок к максимальной длине
                logger.warning(f"Ответ очень длинный ({len(analysis)} символов) и может быть обрезан")
                # Добавляем предупреждение в конец ответа
                analysis += "\n\n[Внимание: ответ может быть обрезан из-за ограничений API]"
            
            self.finished.emit(analysis)
            
        except Exception as e:
            error_message = f"Ошибка при анализе: {str(e)}"
            
            # Добавляем более подробную информацию для некоторых типов ошибок
            if isinstance(e, requests.HTTPError) and hasattr(e, 'response'):
                status_code = e.response.status_code
                if status_code == 400:
                    try:
                        error_data = e.response.json()
                        if 'error' in error_data and 'message' in error_data['error']:
                            error_message = f"Ошибка API: {error_data['error']['message']}"
                    except:
                        pass
                    
                    # Добавляем рекомендации по исправлению ошибки
                    error_message += "\n\nВозможные решения:" \
                                     "\n1. Попробуйте уменьшить размер анализируемых логов" \
                                     "\n2. Проверьте настройки API и URL" \
                                     "\n3. Увеличьте лимит токенов в настройках LLM сервера, если это возможно"
                elif status_code == 401 or status_code == 403:
                    error_message = "Ошибка авторизации. Проверьте API ключ в настройках."
                elif status_code == 404:
                    error_message = "Ошибка: Сервер LLM не найден. Проверьте URL в настройках."
                elif status_code >= 500:
                    error_message = "Ошибка сервера LLM. Пожалуйста, попробуйте позже."
            
            logger.error(error_message, exc_info=True)
            self.error.emit(error_message) 