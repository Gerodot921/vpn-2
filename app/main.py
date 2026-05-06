from __future__ import annotations

import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from .config import Settings
from .generator_client import GenerationRequest, GeneratorClient
from .local_generator import LocalGenerator
from .keyboards import mode_keyboard, yes_no_keyboard
from .states import ConfigFlow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

DEFAULTS = {
    "legacy": {
        "template": "warp_amnezia",
        "dns": "cloudflare",
    },
    "awg2": {
        "template": "warp_amnezia_awg2",
        "dns": "cloudflare",
    },
}


def _normalize_optional_text(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if not value or value.lower() in {"/skip", "skip", "-", "none", "нет", "no"}:
        return None
    return value


def _normalize_keepalive(text: str | None) -> int | None:
    value = _normalize_optional_text(text)
    if value is None:
        return None
    keepalive = int(value)
    if keepalive < 0 or keepalive > 65535:
        raise ValueError("keepalive must be between 0 and 65535")
    return None if keepalive == 0 else keepalive


def _normalize_presets(text: str | None) -> list[str] | None:
    value = _normalize_optional_text(text)
    if value is None:
        return None
    presets = [item.strip() for item in value.split(",") if item.strip()]
    return presets or None


async def _generate_and_send(message: Message, state: FSMContext, client: GeneratorClient) -> None:
    data = await state.get_data()
    mode = data.get("mode") or "legacy"
    template = data.get("template") or DEFAULTS[mode]["template"]
    dns = data.get("dns") or DEFAULTS[mode]["dns"]
    presets = data.get("presets")
    peer_endpoint = data.get("peer_endpoint")
    keepalive = data.get("keepalive")
    i1_ref = data.get("i1_ref")
    i1_raw = data.get("i1_raw")

    request = GenerationRequest(
        mode=mode,
        template=template,
        presets=presets,
        dns=dns,
        peer_endpoint=peer_endpoint,
        keepalive=keepalive,
        i1=i1_raw,
        i1_ref=i1_ref,
    )

    await message.answer("Генерирую конфиг и готовлю файл для отправки...")
    try:
        conf_text, meta = await client.generate(request)
    except Exception as exc:
        await message.answer(f"Не удалось сгенерировать конфиг: {exc}")
        await state.clear()
        return

    suffix = "awg2" if mode == "awg2" else "legacy"
    filename = f"AmneziaVPN-{suffix}.conf"
    document = BufferedInputFile(conf_text.encode("utf-8"), filename=filename)
    await message.answer_document(
        document=document,
        caption=(
            f"Конфиг готов. Режим: {mode}. "
            f"Шаблон: {template}. "
            f"Routes: {meta.get('routesSource', 'n/a')}"
        ),
    )
    await state.clear()


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Это бот для генерации конфигов AmneziaWG.\n"
        "Введите /config, чтобы собрать конфиг по шагам."
    )


@router.message(Command("config"))
async def config(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ConfigFlow.mode)
    await message.answer("Выберите режим конфига:", reply_markup=mode_keyboard())


@router.callback_query(F.data.startswith("mode:"), ConfigFlow.mode)
async def choose_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":", 1)[1]
    if mode not in DEFAULTS:
        await callback.answer("Неизвестный режим", show_alert=True)
        return
    await state.update_data(mode=mode)
    await state.set_state(ConfigFlow.template)
    await callback.message.answer(
        f"Шаблон для {mode}: отправьте значение или /skip для автозначения ({DEFAULTS[mode]['template']})."
    )
    await callback.answer()


@router.message(ConfigFlow.template)
async def set_template(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("mode") or "legacy"
    template = _normalize_optional_text(message.text)
    if template is None:
        template = DEFAULTS[mode]["template"]
    await state.update_data(template=template)
    await state.set_state(ConfigFlow.dns)
    await message.answer("DNS-профиль или /skip для cloudflare:")


@router.message(ConfigFlow.dns)
async def set_dns(message: Message, state: FSMContext) -> None:
    dns = _normalize_optional_text(message.text)
    await state.update_data(dns=dns)
    await state.set_state(ConfigFlow.presets)
    await message.answer(
        "Список route-пресетов через запятую или /skip для полного туннеля.\n"
        "Пример: popular,google,cloudflare"
    )


@router.message(ConfigFlow.presets)
async def set_presets(message: Message, state: FSMContext) -> None:
    presets = _normalize_presets(message.text)
    await state.update_data(presets=presets)
    await state.set_state(ConfigFlow.peer_endpoint)
    await message.answer("Endpoint override в формате host:port или /skip:")


@router.message(ConfigFlow.peer_endpoint)
async def set_peer_endpoint(message: Message, state: FSMContext) -> None:
    peer_endpoint = _normalize_optional_text(message.text)
    await state.update_data(peer_endpoint=peer_endpoint)
    await state.set_state(ConfigFlow.keepalive)
    await message.answer("Persistent keepalive числом 1..65535 или /skip:")


@router.message(ConfigFlow.keepalive)
async def set_keepalive(message: Message, state: FSMContext) -> None:
    try:
        keepalive = _normalize_keepalive(message.text)
    except ValueError:
        await message.answer("Введите число от 1 до 65535 или /skip.")
        return
    await state.update_data(keepalive=keepalive)
    await state.set_state(ConfigFlow.i1_ref)
    await message.answer(
        "I1 reference filename без расширения или /skip.\n"
        "Для больших payload лучше использовать I1 reference."
    )


@router.message(ConfigFlow.i1_ref)
async def set_i1_ref(message: Message, state: FSMContext) -> None:
    i1_ref = _normalize_optional_text(message.text)
    await state.update_data(i1_ref=i1_ref)
    await state.set_state(ConfigFlow.i1_raw)
    await message.answer("Сырый I1 payload или /skip:")


@router.message(ConfigFlow.i1_raw)
async def set_i1_raw(message: Message, state: FSMContext) -> None:
    i1_raw = _normalize_optional_text(message.text)
    await state.update_data(i1_raw=i1_raw)
    await state.set_state(ConfigFlow.confirm)
    data = await state.get_data()
    await message.answer(
        "Проверка параметров:\n"
        f"mode: {data.get('mode')}\n"
        f"template: {data.get('template') or 'auto'}\n"
        f"dns: {data.get('dns') or 'cloudflare'}\n"
        f"presets: {', '.join(data.get('presets') or []) or 'full tunnel'}\n"
        f"endpoint: {data.get('peer_endpoint') or 'default'}\n"
        f"keepalive: {data.get('keepalive') or 'default'}\n"
        f"i1Ref: {data.get('i1_ref') or 'none'}\n"
        f"i1: {'set' if data.get('i1_raw') else 'none'}\n\n"
        "Если всё верно, отправьте /go. Для отмены используйте /cancel."
    )


@router.message(Command("go"), ConfigFlow.confirm)
async def confirm_and_generate(message: Message, state: FSMContext, client: GeneratorClient) -> None:
    await _generate_and_send(message, state, client)


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Используйте /config для генерации конфига.")


async def run() -> None:
    settings = Settings.from_env()
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    async with aiohttp.ClientSession() as session:
        use_remote = os.getenv("USE_REMOTE_GENERATOR", "true").lower() not in {"0", "false", "no"}
        if use_remote:
            client = GeneratorClient(settings.generator_api_base_url, session)
        else:
            client = LocalGenerator()
        dp["client"] = client

        bot = Bot(token=settings.bot_token)
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
