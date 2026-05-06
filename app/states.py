from aiogram.fsm.state import State, StatesGroup


class ConfigFlow(StatesGroup):
    mode = State()
    template = State()
    dns = State()
    presets = State()
    peer_endpoint = State()
    keepalive = State()
    i1_ref = State()
    i1_raw = State()
    confirm = State()
