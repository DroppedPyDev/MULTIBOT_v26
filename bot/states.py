from aiogram.fsm.state import State, StatesGroup


class CloudStates(StatesGroup):
    waiting_folder_name = State()
    waiting_search_query = State()
