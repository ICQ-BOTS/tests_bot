import os
from concurrent.futures import ThreadPoolExecutor
import random
import re
import logging
from io import BytesIO
from PIL import Image, ImageDraw

import asyncio

import xmlrpc.client

log = logging.getLogger(__name__)


async def handle_answers(user, answers, test, addition_info):
    global nouns, postcards_server

    data_image = postcards_server.get_random_vanilla_postcard(user.id, 1)
    return "", None, Image.open(BytesIO(data_image.data))


def init(postcards_ip, postcards_port):
    global postcards_server

    postcards_server = xmlrpc.client.ServerProxy(
        f"http://{postcards_ip}:{postcards_port}"
    )
