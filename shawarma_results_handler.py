from lxml import html
import pymorphy2
import os
from concurrent.futures import ThreadPoolExecutor
from button_menu import ButtonsMenuBuilder
import random
import zlib
import re
import logging
import state
import traceback
from io import BytesIO

import asyncio
import aiohttp
import json
import base64

import xmlrpc.client

log = logging.getLogger(__name__)
ENCODING = "utf-8"

colors = [
    ("классический", "white"),
    ("сырный", "orange"),
    ("шпинатный", "green"),
    ("беконный", "red"),
    ("угольный", "black"),
]


def check_colors(lower_text):
    for color_tuple in colors:
        if color_tuple[0] in lower_text:
            return color_tuple[1]
    return None


async def handle_answers(user, answers, test, addition_info):
    global FACES_PUT_SERVICE_IP, FACES_PUT_SERVICE_PORT, BOT
    # Count result

    key_number = 143297  # Pseudo random result select key
    module = 1024

    # Find for known nomns and compute answers hash
    result_number = zlib.crc32(bytes(test.get_name(), "utf-8")) % module

    shawarma_class = "common"
    shawarma_color = False
    image_text = "Вот она, шаурма твоей мечты"
    for answer in answers:
        text = answer.get_text()
        lower_text = text.lower()
        if "шаверм" in lower_text:
            shawarma_class = "st_p"

        if "шаверма" in lower_text:
            image_text = "Вот она, шаверма твоей мечты"
        if ("шавуха" in lower_text) or ("шавка" in lower_text):
            image_text = "Вот она, шавуха твоей мечты"

        if shawarma_color == False:
            color_in_text = check_colors(lower_text)
            if not color_in_text is None:
                shawarma_color = color_in_text
        textHash = zlib.crc32(bytes(text, "utf-8")) % module
        result_number = (result_number + textHash) % module

    result_number = (result_number + (key_number % module)) % module
    message_id = await state.show_message(
        bot=BOT,
        user=user,
        text="Подождите, результат загружается...",
        stay_in_chat=True,
    )

    # Prepare face image (set None or download)
    face_image = None
    if not addition_info is None:
        async with aiohttp.ClientSession() as session:
            file_info = await BOT.get_file_info(addition_info[1])
            image_url = file_info.get("url", None)
            if not image_url is None:
                async with session.get(image_url) as resp:
                    face_image_bytes = await resp.read()
                    face_image = base64.b64encode(face_image_bytes).decode(ENCODING)
            await session.close()
    # Create session
    print("Shawarma params: ", shawarma_class, shawarma_color)
    async with aiohttp.ClientSession() as session:
        bmb = ButtonsMenuBuilder()
        bmb.add_action_button("Пройти ещё один тест", "return_to_root")
        request_data = {
            "bot_info": [BOT.token, BOT.name],
            "callback_message_id": message_id,
            "callback_chat_id": user.id,
            "callback_addition": {"buttons": bmb.get_to_send(), "text": image_text},
            "watermark": "tests_bot",
            "face_image": face_image,
            "shawarma_generator": [result_number, shawarma_class, shawarma_color],
        }
        async with await session.post(
            f"http://{FACES_PUT_SERVICE_IP}:{FACES_PUT_SERVICE_PORT}/shawarma_put",
            data=json.dumps(request_data),
        ) as response:
            response_dict = await response.text()
        await session.close()

    return None, None, None


def init(faces_put_service_ip, faces_put_service_port, bot):
    global FACES_PUT_SERVICE_IP, FACES_PUT_SERVICE_PORT, BOT

    FACES_PUT_SERVICE_IP = faces_put_service_ip
    FACES_PUT_SERVICE_PORT = faces_put_service_port
    BOT = bot