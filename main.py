"""
Основной файл приложения AI Log Analyzer
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.constants import logger
from core.vectorizer import Vectorizer
from ui.main_window import MainWindow

def main():
    """Точка входа в приложение"""
    logger.debug("Запуск приложения")
    app = QApplication(sys.argv)
    
    # Создаем экземпляр главного окна
    main_window = MainWindow(None)  # Временно передаем None вместо vectorizer
    
    # Показываем окно загрузки
    main_window.show_loading()
    
    # Инициализируем векторайзер в отдельном потоке, чтобы не блокировать UI
    def init_vectorizer():
        try:
            logger.debug("Начало инициализации векторизатора...")
            vectorizer = Vectorizer()
            logger.debug("Векторизатор создан успешно, обновляем главное окно")
            
            # Используем новый метод для установки векторизатора
            success = main_window.set_vectorizer(vectorizer)
            if not success:
                logger.error("Не удалось установить векторизатор в главное окно")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(main_window, "Предупреждение", 
                              "Не удалось инициализировать векторизатор полностью.\n"
                              "Некоторые функции могут быть недоступны.")
            
            main_window.hide_loading()
            main_window.show()
            logger.debug("Главное окно отображено")
        except Exception as e:
            logger.error(f"Ошибка при инициализации векторизатора: {str(e)}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(main_window, "Ошибка", 
                             f"Не удалось инициализировать векторизатор: {str(e)}\n\n"
                             "Приложение может работать некорректно.")
            main_window.hide_loading()
            main_window.show()
    
    # Запускаем инициализацию через небольшую задержку
    QTimer.singleShot(100, init_vectorizer)
    
    logger.debug("Приложение запущено")
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 