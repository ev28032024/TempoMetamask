# Tempo Testnet Automation

Автоматизация взаимодействия с Tempo Testnet через AdsPower профили и Google Sheets.

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

### 1. Google Sheets

1. Создайте сервисный аккаунт в [Google Cloud Console](https://console.cloud.google.com/)
2. Скачайте JSON-ключ и сохраните как `credentials.json`
3. Дайте сервисному аккаунту доступ к вашей таблице

### 2. Конфигурация

Отредактируйте `config.yaml`:

```yaml
google_sheets:
  sheet_id: "ВАШ_SHEET_ID"
  sheet_name: "Testnet (v1) (test)"

adspower:
  api_url: "http://local.adspower.net:50325"
```

### 3. Структура Google Sheet

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Profile Number | Address | Add Funds | Set fee token | GM | Ready/Error |
| 1 | 0x... | OK | OK | OK | Ready |
| 2 | 0x... | | | | |

## Использование

```bash
# Все pending профили (не Ready)
python main.py

# Конкретный профиль
python main.py --profile 1

# Все профили принудительно  
python main.py --all

# Параллельная обработка (2 профиля)
python main.py --parallel 2

# Предпросмотр
python main.py --dry-run
```

## Паттерн пароля MetaMask

```
ВвожуПароль!<serial_number>
```

Например для профиля 1: `ОткрываюМетамаск!1`

## Логи

Логи записываются в `tempo_automation.log`
