import xmlrpc.client
import logging
import asyncio
import time

log = logging.getLogger(__name__)


async def send(
    loop,
    bot,
    text,
    users_list,
    callback_user_id,
    indicator_msg_id,
    buttons,
    current_index=0,
):
    global FUNCTION_TIMEOUT, DELAY_S

    if current_index == 0:
        await bot.send_text(
            chat_id=callback_user_id, text=text, inline_keyboard_markup=buttons
        )

    seconds = int(round(time.time()))
    timout_seconds = seconds + FUNCTION_TIMEOUT
    log.info(f"Start new task  |   Now: {seconds}; Timeout: {timout_seconds}")

    users_list_length = len(users_list)
    for index in range(current_index, users_list_length):
        user_id = users_list[index]

        log.info(f"send to {user_id}")
        response = await bot.send_text(
            chat_id=user_id, text=text, inline_keyboard_markup=buttons
        )
        await asyncio.sleep(DELAY_S)

        log.info(f"{response}")

        sended_count = index + 1
        if sended_count % 100 == 0:
            await bot.edit_text(
                msg_id=indicator_msg_id,
                chat_id=callback_user_id,
                text=f"Прогресс: {sended_count} / {users_list_length}",
            )

        current_seconds = int(round(time.time()))
        if int(round(time.time())) > timout_seconds:

            loop.create_task(
                send(
                    loop,
                    bot,
                    text,
                    users_list,
                    callback_user_id,
                    indicator_msg_id,
                    buttons,
                    index + 1,
                )
            )
            return

    await bot.edit_text(
        msg_id=indicator_msg_id,
        chat_id=callback_user_id,
        text="Все сообщения были высланы",
    )


# def generator():
#    for i in range(10000):
#        yield "752290089"


def start_send(
    loop, bot, text, users_list, callback_user_id, indicator_msg_id, buttons=None
):
    users_list = list(users_list)

    millis = int(round(time.time() * 1000))

    loop.create_task(
        send(loop, bot, text, users_list, callback_user_id, indicator_msg_id, buttons)
    )


def init(task_timeout, push_notes_delay_ms):
    global FUNCTION_TIMEOUT, DELAY_S
    FUNCTION_TIMEOUT = int(task_timeout * 0.9)
    DELAY_S = push_notes_delay_ms / 1000
