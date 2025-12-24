# Tempo Testnet Automation
# Автоматизация взаимодействия с Tempo Testnet через AdsPower профили

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

1. Скопируйте `.env.example` в `.env`
2. Заполните параметры:
   - `GOOGLE_SHEET_ID` - ID таблицы с профилями
   - `GOOGLE_CREDENTIALS_PATH` - путь к JSON сервисного аккаунта
   - `ADSPOWER_API_URL` - URL AdsPower API
   - `ADSPOWER_API_KEY` - API ключ (если нужен)

3. Убедитесь что AdsPower запущен

## Использование

```bash
# Запуск для всех профилей
python main.py

# Запуск для конкретного профиля
python main.py --profile 1

# Запуск с ограничением параллельности
python main.py --parallel 2
```

## Структура Google Sheet

| Колонка A | Колонка B | Колонка C |
|-----------|-----------|-----------|
| serial_number | status | timestamp |
| 1 | pending | |
| 2 | completed | 2024-12-24 |
