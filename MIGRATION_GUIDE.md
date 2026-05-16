# Quick start guide for Xray VPN with 3x-ui

## Структура проекта после переписки

✅ **Завершено:**
- Полная замена Amnezia на Xray (VLESS, VMess, Trojan протоколы)
- Интеграция с 3x-ui админ-панелью
- Новый FastAPI бэкенд для управления подписками и авторизацией
- Переписан Telegram бот для генерации конфигов
- Docker Compose стек с всеми сервисами на порту 8080 (вместо 80)

## Файлы, измененные/созданные:

### app/ (Telegram Bot)
- ✅ `config.py` — переписан для Xray параметров
- ✅ `xray_api.py` — новый файл для работы с Xray API
- ✅ `main.py` — переписан для Xray конфигов
- ✅ `keyboards.py` — обновлены для новых стейтов
- ✅ `states.py` — обновлены для новых стейтов

### backend/ (FastAPI API)
- ✅ `main.py` — полностью переписан для Xray
- ✅ `crud.py` — упрощен (убрана Amnezia SSH логика)
- ✅ `Dockerfile` — обновлен

### Configuration
- ✅ `docker-compose.yml` — новый стек с Xray, 3x-ui, Nginx на 8080
- ✅ `xray/config.json` — новый Xray конфиг
- ✅ `nginx.xray.conf` — новый Nginx конфиг для 8080
- ✅ `requirements.txt` — обновлены зависимости
- ✅ `.env` — обновлен для Xray параметров
- ✅ `.env.example` — новый шаблон

### Документация
- ✅ `README_XRAY_3XUI.md` — полная документация

## Следующие шаги:

### 1. Проверить импорты и синтаксис
```bash
python -m py_compile app/main.py
python -m py_compile backend/main.py
```

### 2. Создать образы Docker
```bash
docker-compose build
```

### 3. Запустить стек
```bash
docker-compose up -d
```

### 4. Проверить сервисы
```bash
# API health
curl http://localhost:8080/api/health

# 3x-ui панель
open http://localhost:8080/admin/

# Telegram бот
@your_bot
/start
```

## Старые файлы, которые можно удалить:

```bash
rm -f app/amnezia_ssh.py          # SSH для Amnezia больше не нужен
rm -f app/generator_client.py     # API клиент для Amnezia API
rm -f app/local_generator.py      # Локальный генератор конфигов
rm -f app/main_new.py             # Временный файл
rm -f nginx.conf                  # Старый Nginx конфиг
rm -f nginx.prod.conf             # Старый Nginx prod конфиг
rm -f docker-compose.prod.yml     # Старый docker-compose
rm -f amnezia-wg.service          # Старый systemd сервис
rm -f README_3x_ui_deploy.md      # Старая документация
```

## Отличия от старой архитектуры:

| Компонент | Amnezia (старое) | Xray (новое) |
|-----------|------------------|-------------|
| VPN протокол | WireGuard | VLESS/VMess/Trojan |
| Управление | SSH + скрипты | 3x-ui Web UI + gRPC API |
| Админ-панель | Своя FastAPI | Встроенная 3x-ui |
| Порт Nginx | 80 (требовал sudo) | **8080** (user access) |
| Интеграция | SSH по ключу | REST API + 3x-ui |
| Persistence | Файл конфига | 3x-ui Database |

## Миграция существующих пользователей (если требуется):

```python
# backend/crud.py — добавить функцию миграции
def migrate_amnezia_users_to_xray(amnezia_db_path, xray_db_session):
    """Экспортировать пользователей из Amnezia и создать в Xray"""
    # 1. Прочитать WireGuard конфиг
    # 2. Для каждого пира создать Xray пользователя
    # 3. Сохранить в PostgreSQL
    pass
```

## Проверка что всё работает:

```bash
# 1. Логи backend
docker-compose logs -f backend | grep "Starting Xray VPN API"

# 2. Логи Xray
docker-compose logs -f xray | grep "started"

# 3. API доступна
curl http://localhost:8080/api/health
# ↓
# {"status":"ok","service":"xray_vpn_api"}

# 4. Telegram бот ready
# Отправить /start в бот → должно вернуть главное меню
```

## Commit и Push

```bash
git add -A
git commit -m "Complete rewrite: Amnezia → Xray + 3x-ui"
git push origin main
```

---

**Статус:** ✅ Полная переписка завершена
**Тестирование:** Требуется
**Готовность к production:** Требуется настройка SSL и VPN_ENDPOINT_HOST
