import json
from mailru_im_async_bot.event import EventType

import state as State

async def command(bot, event):
	await bot.send_text(chat_id=event.message_author['user_id'], text=f"command {event.text}")


async def run(bot, event):
	await bot.send_text(chat_id=event.message_author['user_id'], text=f"run")


async def hello(bot, event, user):
	await bot.send_text(chat_id=event.message_author['user_id'], text=f"1 ответ на {event.text}")
	response = await user.wait_response()
	await bot.send_text(chat_id=event.message_author['user_id'], text=f"2 ответ на {response.text}")
	response = await user.wait_response()
	await bot.send_text(chat_id=event.message_author['user_id'], text=f"3 ответ на {response.text}")

async def buttons_get_cb(bot, event):
	#print('button click by %s'%(user.id))
	await bot.send_text(
		chat_id=event.message_author['user_id'],
		text="hello with buttons.",
		inline_keyboard_markup="[{}]".format(json.dumps([
			{"text": "action 1", "callback_data": "call_back_id_2", "url": "http://mail.ru"},
			{"text": "action 2", "callback_data": "call_back_id_2"},
			{"text": "action 3", "callback_data": "call_back_id_3"}
		])))


async def buttons_answer_cb(bot, event, user):
	if event.data['callback_data'] == "call_back_id_2":
		await bot.answer_callback_query(
			query_id=event.data['query_id'],
			text="hey! it's a working button 2.",
			show_alert=True
		)

	elif event.data['callback_data'] == "call_back_id_3":
		await bot.answer_callback_query(
			query_id=event.data['query_id'],
			text="hey! it's a working button 3.",
			show_alert=False
		)




#Точка входа пользователя
async def handle_session_start(bot, event, user):
	await State.start_session(bot, user, event)
	

	return
	await bot.send_text(chat_id=event.message_author['user_id'], text="Меню")
	response = await user.wait_response()
	if response.type == EventType.CALLBACK_QUERY:
		await bot.send_text(chat_id=event.message_author['user_id'], text=f"была нажата кнопка {response.data['callback_data']}")
	else:
		await bot.send_text(chat_id=event.message_author['user_id'], text=f"2 ответ на {response.text}")