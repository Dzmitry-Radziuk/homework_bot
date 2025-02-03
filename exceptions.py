class PracticumAPIError(Exception):
    """Основное исключение для ошибок API Практикума."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class TokenMissingError(PracticumAPIError):
    """Исключение, если отсутствуют обязательные токены."""
    def __init__(self, token_name):
        self.message = f'Отсутствует обязательный токен: {token_name}'
        super().__init__(self.message)


class InvalidHomeworkStatusError(PracticumAPIError):
    """Исключение для неверных статусов домашней работы."""
    def __init__(self, status):
        self.message = f'Неизвестный статус домашней работы: {status}'
        super().__init__(self.message)