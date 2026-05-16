# Xray VPN Service with 3x-ui — Full Stack Architecture

**Полная переписка с Amnezia на Xray + 3x-ui**

Изменения в архитектуре:
- ✅ Заменена Amnezia/WireGuard на Xray/Trojan/VLESS/VMess
- ✅ Добавлена 3x-ui админ-панель (порт 7654 через Nginx на 8080)
- ✅ Переписан FastAPI бэкенд для управления пользователями и подписками
- ✅ Переписан Telegram бот для генерации Xray конфигов (VLESS, VMess, Trojan)
- ✅ Docker Compose стек с Xray, 3x-ui, FastAPI, PostgreSQL, Nginx (8080)

## Структура проекта

```
vpn-2/
├── app/                          # Telegram bot
│   ├── config.py                # Xray config settings
│   ├── xray_api.py              # Xray API client
│   ├── main.py                  # Bot handlers (новый)
│   ├── keyboards.py             # Inline keyboards
│   └── states.py                # FSM states
│
├── backend/                      # FastAPI REST API
│   ├── main.py                  # API endpoints (переписан)
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── crud.py                  # Database operations (упрощен)
│   ├── auth.py                  # JWT & password auth
│   ├── database.py              # DB config
│   └── Dockerfile               # Docker image
│
├── xray/
│   └── config.json              # Xray core config
│
├── docker-compose.yml           # Full stack (Xray, 3x-ui, API, PostgreSQL, Nginx)
├── nginx.xray.conf              # Nginx config (8080 → API, 3x-ui)
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variables template
```

## Сервисы Docker Compose

| Сервис | Порт | Описание |
|--------|------|---------|
| **postgres** | 5432 (внутренний) | PostgreSQL БД для пользователей и подписок |
| **backend** | 8000 | FastAPI (авторизация, планы, подписки) |
| **xray** | 10000-10002, 10085 | Xray VPN сервер + gRPC API |
| **three-x-ui** | 7654 | 3x-ui админ-панель (управление Xray) |
| **nginx** | **8080** | Reverse proxy + фронтенд |

## Доступные эндпоинты на `http://localhost:8080`

### API (FastAPI)
```
POST   /api/auth/register              - Регистрация
POST   /api/auth/token                 - Получить JWT токен
GET    /api/users/me                   - Данные текущего пользователя
POST   /api/vpn/users                  - Создать VPN пользователя
GET    /api/plans                      - Список доступных планов
POST   /api/plans                      - Создать новый план (admin)
POST   /api/subscriptions              - Подписать пользователя на план
GET    /api/subscriptions/active       - Активная подписка
GET    /api/health                     - Health check
GET    /api/metrics                    - Prometheus метрики
```

### 3x-ui Admin Panel
```
http://localhost:8080/admin/  - Вход в админ-панель
```

## Telegram Bot

Команды:
- `/start` — главное меню
- `/quickconfig` — быстро сгенерировать конфиг (VLESS/VMess/Trojan)
- `/account` — информация о профиле
- `/subscribe` — доступные подписки
- `/help` — справка

## Быстрый старт

### 1. Подготовка
```bash
cd vpn-2
cp .env.example .env
# Отредактировать .env с реальными значениями
nano .env
```

### 2. Первый запуск
```bash
docker-compose up -d
```

### 3. Создание админ-пользователя (автоматически при старте)
```
Пользователь: admin
Пароль: admin123
(задать в .env: ADMIN_USER, ADMIN_PASSWORD)
```

### 4. Доступ к сервисам
- **API**: http://localhost:8080/api/health
- **3x-ui**: http://localhost:8080/admin/ (admin/admin123)
- **Telegram бот**: @your_bot_token (настроить в .env TELEGRAM_BOT_TOKEN)

## Переменные окружения (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Database
POSTGRES_PASSWORD=strong_password_here

# API Security
JWT_SECRET_KEY=your-secret-key-min-32-chars-long-for-production

# Admin Account
ADMIN_USER=admin
ADMIN_PASSWORD=change_me_in_production

# Xray
XRAY_API_HOST=xray
XRAY_API_PORT=10085
XRAY_ADMIN_SECRET=xray-secret-key

# VPN Endpoint (публичный IP/домен сервера)
VPN_ENDPOINT_HOST=vpn.example.com
VPN_ENDPOINT_PORT=443

# 3x-ui
THREE_X_UI_USERNAME=admin
THREE_X_UI_PASSWORD=admin123
```

## Управление пользователями

### Через API (FastAPI)
```bash
# Регистрация
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass123"}'

# Получить токен
curl -X POST http://localhost:8080/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=pass123"

# Создать VPN конфиг
curl -X POST http://localhost:8080/api/vpn/users \
  -H "Authorization: Bearer YOUR_TOKEN"

# Создать подписку
curl -X POST http://localhost:8080/api/subscriptions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id":1}'
```

### Через 3x-ui Web Panel
1. Перейти на http://localhost:8080/admin/
2. Логин: admin / Пароль: admin123
3. Создавать/удалять пользователей и управлять инбаундами

### Через Telegram Bot
1. Начать чат: `/start`
2. Выбрать "🚀 Quick Config"
3. Выбрать протокол (VLESS/VMess/Trojan)
4. Выбрать формат (Link/QR/JSON)
5. Получить конфиг

## Интеграция с существующей системой

### Если у вас уже есть Amnezia сервер
- Новая система работает **параллельно** с Amnezia (другие порты)
- Можно мигрировать пользователей постепенно

### Миграция данных пользователей
```python
# backend/crud.py добавить функцию миграции
# Экспортировать пользователей из Amnezia
# Импортировать в новую PostgreSQL БД
```

## Мониторинг и логи

```bash
# Логи контейнеров
docker-compose logs -f backend      # FastAPI логи
docker-compose logs -f xray         # Xray логи
docker-compose logs -f nginx        # Nginx логи

# Metrics
curl http://localhost:8080/api/metrics

# Health check
curl http://localhost:8080/api/health
```

## Обновление и развёртывание

### На production сервере
```bash
git pull origin main
docker-compose pull
docker-compose down
docker-compose up -d
```

### С использованием Systemd
```bash
sudo nano /etc/systemd/system/xray-vpn.service
```

```ini
[Unit]
Description=Xray VPN Service
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/srv/xray-vpn
ExecStart=/usr/bin/docker-compose -f docker-compose.yml up
ExecStop=/usr/bin/docker-compose -f docker-compose.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable xray-vpn
sudo systemctl start xray-vpn
```

## Безопасность

✅ **JWT токены** с 60-минутным expiry
✅ **Bcrypt хеширование** паролей
✅ **Xray API authentication** с secret key
✅ **HTTPS** поддержка (Nginx + SSL/TLS)
✅ **Database credentials** в .env (не в коде)
✅ **Admin only endpoints** с проверкой is_admin

## Roadmap

- [ ] Frontend React/Vue dashboard (замена 3x-ui)
- [ ] WebSocket для real-time статистики
- [ ] Email уведомления о продлении подписки
- [ ] Payment gateway интеграция (Stripe, PayPal)
- [ ] Backup и restore функционал
- [ ] Multi-language поддержка
- [ ] VPN статистика и логирование

## Проблемы и решения

### Xray не стартует
```bash
docker-compose logs xray
# Проверить xray/config.json синтаксис
```

### Nginx не может достучаться до backend
```bash
docker-compose ps
# Убедиться, что backend контейнер running
# Проверить network (vpn_network)
```

### 3x-ui админ-панель недоступна
```bash
curl http://localhost:8080/admin/
# Если 502 Bad Gateway — перезагрузить three-x-ui сервис
docker-compose restart three-x-ui
```

## Контакты и поддержка

GitHub: https://github.com/Gerodot921/vpn-2
