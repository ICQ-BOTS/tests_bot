from lxml import html
import pymorphy2
import os
from concurrent.futures import ThreadPoolExecutor
import random
import zlib
import re
import logging
from io import BytesIO
from PIL import Image, ImageDraw

import asyncio

import xmlrpc.client

log = logging.getLogger(__name__)

morph = pymorphy2.MorphAnalyzer()


def find_word_description(descriptions_list, word):
    for description in descriptions_list:
        if description["word"] == word:
            return description
    return None


def find_pos(array, POS):
    for element in array:
        if element.tag.POS == POS:
            return element
    return array[0]


class TestTestAnswer:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text

    def get_name(self):
        return self.text


async def handle_answers(user, answers, test, addition_info):
    global nouns, postcards_server
    # print('Start handle random picture answers')

    key_number = 143297  # Pseudo random result select key
    module = len(nouns) * 59

    # Find for known nomns and compute answers hash
    result_number = zlib.crc32(bytes(test.get_name(), "utf-8")) % module
    known_nouns = []
    for answer in answers:
        text = answer.get_text()
        words = re.findall(r"\w+", text)
        for word in words:
            word_morph = find_pos(morph.parse(word), "NOUN")
            if not word_morph:
                continue

            form_attribs = {"nomn"}

            if (not ("Pltm" in word_morph.tag)) and (not ("Sgtm" in word_morph.tag)):
                form_attribs.add("sing")
            word_normal = word_morph.inflect(form_attribs)
            if not word_normal:
                continue

            description = find_word_description(nouns, word_normal.word)
            if description:
                known_nouns.append(description)

        textHash = zlib.crc32(bytes(text, "utf-8")) % module
        result_number = (result_number + textHash) % module

    # print(f'Hash {result_number}')
    # print(f'Founded known nouns {known_nouns}')

    result_number = (result_number + (key_number % module)) % module

    # --------------------------------Choice noun--------------------------------

    # 80%, that noun will be const
    if random.random() < 0.8:
        random.seed(result_number)

        if known_nouns:
            noun_description = random.choice(known_nouns)
        else:
            noun_description = random.choice(nouns)

        # Return true random
        random.seed()
    else:
        noun_description = random.choice(nouns)

    print("NOUN ID: ", noun_description["id"])
    data_image = postcards_server.get_random_noun_postcard(
        user.id, noun_description["id"]
    )
    return "", None, Image.open(BytesIO(data_image.data))


def get_postcards_server():
    global postcards_server
    return postcards_server


def init(postcards_ip, postcards_port):
    global postcards_server, nouns

    postcards_server = xmlrpc.client.ServerProxy(
        f"http://{postcards_ip}:{postcards_port}"
    )
    nouns_ids_dict = postcards_server.get_nouns_ids_dict()

    nouns = []

    for noun, id in nouns_ids_dict.items():
        noun_description = {}
        noun_description["word"] = noun
        noun_description["id"] = id
        word = noun
        morph_source = find_pos(morph.parse(word), "NOUN")
        noun_description["morph"] = morph_source
        nouns.append(noun_description)

    # print(nouns)
