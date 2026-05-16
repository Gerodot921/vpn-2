# Xray VPN with 3x-ui — Полная переписка завершена

## 📋 Краткое резюме

**Проект переписан с нуля с Amnezia/WireGuard на Xray/3x-ui:**

### ✅ Новая архитектура

```
┌──────────────────────────────────────────────────┐
│  Nginx на PORT 8080 (вместо 80/443)             │
├──────────────────────────────────────────────────┤
│  /api/*        →  FastAPI Backend (8000)        │
│  /admin/*      →  3x-ui Web Panel (7654)        │
│  /*            →  Frontend Static Files         │
└──────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│  Сервисы Docker Compose                         │
├──────────────────────────────────────────────────┤
│  ✅ PostgreSQL 15    — База пользователей       │
│  ✅ FastAPI Backend  — REST API, JWT, Billing   │
│  ✅ Xray Core        — VLESS/VMess/Trojan       │
│  ✅ 3x-ui Panel      — Управление Xray          │
│  ✅ Nginx            — Reverse Proxy на 8080    │
└──────────────────────────────────────────────────┘
```

### 🔄 Замены

| Что было | Стало |
|---------|-------|
| SSH подключение к Amnezia | Xray gRPC API |
| WireGuard конфиги | VLESS/VMess/Trojan протоколы |
| Скрипты создания пиров | 3x-ui Admin Panel + API |
| Порт 80 (требовал sudo) | Порт 8080 (user access) |
| Собственная админ-панель | 3x-ui Web UI |

## 📁 Структура проекта

```
vpn-2/
│
├── 🤖 app/                    # Telegram Bot
│   ├── config.py             # ✏️ Переписан для Xray
│   ├── xray_api.py           # 🆕 Xray API client
│   ├── main.py               # ✏️ Новые обработчики
│   ├── keyboards.py          # ✏️ Обновлены
│   └── states.py             # ✏️ Обновлены
│
├── 🔌 backend/               # FastAPI REST API
│   ├── main.py               # ✏️ Полностью переписан
│   ├── crud.py               # ✏️ Упрощен (no SSH)
│   ├── models.py             # Используется как есть
│   ├── schemas.py            # Используется как есть
│   ├── auth.py               # Используется как есть
│   ├── database.py           # Используется как есть
│   ├── __init__.py           # 🆕 Добавлен
│   └── Dockerfile            # ✏️ Обновлен
│
├── ⚙️ xray/
│   └── config.json           # 🆕 Xray конфиг
│
├── 🐳 docker-compose.yml     # ✏️ Новый стек (Xray, 3x-ui, Nginx 8080)
├── nginx.xray.conf           # 🆕 Конфиг на порту 8080
├── requirements.txt          # ✏️ Обновлены зависимости
├── .env                      # ✏️ Переписан для Xray
├── .env.example              # ✏️ Обновлен шаблон
├── pyproject.toml            # ✏️ Обновлен для версии 2.0
├── start.sh                  # 🆕 Скрипт быстрого старта
│
└── 📚 Документация
    ├── README_XRAY_3XUI.md   # 🆕 Полная документация
    ├── MIGRATION_GUIDE.md    # 🆕 Инструкции по миграции
    └── CHANGES.txt           # 🆕 Этот файл
```

## 🚀 Быстрый старт

### 1️⃣ Подготовка

```bash
cd vpn-2

# Обновить переменные окружения
cp .env.example .env
nano .env

# ВАЖНЫЕ переменные для изменения:
# - TELEGRAM_BOT_TOKEN      (ваш бот токен)
# - VPN_ENDPOINT_HOST       (публичный IP/домен сервера)
# - POSTGRES_PASSWORD       (надежный пароль)
# - JWT_SECRET_KEY          (32+ символа)
# - XRAY_ADMIN_SECRET       (защитный ключ)
```

### 2️⃣ Запуск

```bash
# Вариант 1: Использовать скрипт
bash start.sh

# Вариант 2: Вручную
docker-compose build
docker-compose up -d
```

### 3️⃣ Проверка

```bash
# API здоров?
curl http://localhost:8080/api/health
# ↓ {"status":"ok","service":"xray_vpn_api"}

# Логи
docker-compose logs -f backend

# 3x-ui админ-панель
open http://localhost:8080/admin/
# Логин: admin / Пароль: admin123 (из .env)
```

### 4️⃣ Telegram бот

```
Отправить /start в бот → выбрать "🚀 Quick Config"
→ выбрать протокол (VLESS/VMess/Trojan)
→ получить готовый конфиг для клиента
```

## 📊 API Endpoints

### Авторизация
```bash
POST /api/auth/register              # Регистрация нового пользователя
POST /api/auth/token                 # Получить JWT токен
GET  /api/users/me                   # Данные текущего пользователя
```

### VPN Управление
```bash
POST /api/vpn/users                  # Создать конфиг для пользователя
```

### Подписки
```bash
GET  /api/plans                      # Список доступных планов
POST /api/subscriptions              # Подписать пользователя на план
GET  /api/subscriptions/active       # Активная подписка пользователя
```

### Админ
```bash
POST /api/plans                      # Создать новый план (admin only)
GET  /api/admin/stats                # Статистика системы
```

### Мониторинг
```bash
GET  /api/health                     # Health check
GET  /api/metrics                    # Prometheus метрики
```

## 🔐 Безопасность

✅ **JWT токены** — 60-минутный expiry  
✅ **Bcrypt хеш** — пароли  
✅ **Admin-only endpoints** — проверка прав  
✅ **Secret ключи** — в .env (не в коде)  
✅ **HTTPS поддержка** — Nginx + SSL/TLS  
✅ **Xray API authentication** — secret key  

## 🗑️ Удалить старые файлы

```bash
# Файлы Amnezia больше не нужны
rm -f app/amnezia_ssh.py
rm -f app/generator_client.py
rm -f app/local_generator.py
rm -f app/main_new.py
rm -f nginx.conf nginx.prod.conf
rm -f docker-compose.prod.yml
rm -f amnezia-wg.service
rm -f README_3x_ui_deploy.md
rm -f systemd/

# Очистить кеш
rm -rf app/__pycache__ backend/__pycache__
```

## 🔄 Миграция пользователей (если требуется)

Если у вас есть существующие пользователи Amnezia:

```python
# backend/migrations/migrate_amnezia_to_xray.py
def migrate():
    # 1. Экспортировать пиры из Amnezia конфига
    # 2. Создать пользователей в PostgreSQL
    # 3. Добавить в Xray через API
    pass
```

## 📈 Что дальше?

### Краткосрочно (это неделя)
- [ ] Тестирование всех эндпоинтов
- [ ] Настройка SSL сертификата
- [ ] Проверка производительности
- [ ] Документирование API (Swagger)

### Среднесрочно (1-2 недели)
- [ ] Frontend React/Vue dashboard
- [ ] WebSocket для real-time статистики
- [ ] Email уведомления о подписке
- [ ] Payment gateway (Stripe)

### Долгосрочно (месяц+)
- [ ] Multi-language поддержка
- [ ] VPN статистика и аналитика
- [ ] Backup & restore системы
- [ ] High-availability кластер

## 🆘 Troubleshooting

### Xray не стартует
```bash
docker-compose logs xray
# Проверить xray/config.json синтаксис
```

### Nginx 502 Bad Gateway
```bash
docker-compose restart nginx
# Или проверить что backend running
docker-compose ps
```

### API не доступен
```bash
curl -v http://localhost:8080/api/health
# Проверить логи backend
docker-compose logs backend
```

### Telegram бот не отвечает
```bash
# Проверить TELEGRAM_BOT_TOKEN в .env
# Проверить интернет соединение контейнера
docker-compose exec backend curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe
```

## 💾 Git

```bash
# Сделать коммит всех изменений
git add -A
git commit -m "Полная переписка: Amnezia → Xray + 3x-ui

- Заменена SSH интеграция на Xray gRPC API
- Добавлена 3x-ui админ-панель
- Переписан Telegram бот для VLESS/VMess/Trojan
- Переписан FastAPI бэкенд для подписок
- Docker стек с Nginx на порту 8080
- BREAKING CHANGE: порт изменен с 80 на 8080"

git push origin main
```

## 📞 Поддержка

- 📧 GitHub Issues: https://github.com/Gerodot921/vpn-2/issues
- 📚 Документация: [README_XRAY_3XUI.md](README_XRAY_3XUI.md)
- 📖 Миграция: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

---

**Версия:** 2.0.0  
**Дата:** Май 2026  
**Статус:** ✅ Переписка завершена, требуется тестирование
