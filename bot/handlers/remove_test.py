from aiogram.dispatcher import FSMContext
from aiogram.types import Message

from bot.init_bot import get_bot
from utils import logger


async def update_new_msg(
    chat_id: int,
    new_message: Message,
    state: FSMContext
):
    if new_message is None or chat_id is None:
        return
    bot = get_bot()
    data = await state.get_data()
    last_message_id = data.get("last_message_id")
    if last_message_id == new_message.message_id:
        return
    # Если у нового сообщения НЕТ клавиатуры НЕ убираем у старого
    if new_message.reply_markup is None:
        # Просто сохраняем новое сообщение как последнее
        await state.update_data(last_message_id=new_message.message_id)
        return

    # Если у нового сообщения ЕСТЬ клавиатура можно убрать у старого
    if last_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=last_message_id,
                reply_markup=None
            )

        except Exception as e:
            logger.warning(f'Ошибка при удалении клавиатуры у предыдущего сообщения: {e}')

    # Сохраняем ID нового сообщения как последнее
    await state.update_data(last_message_id=new_message.message_id)
