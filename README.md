# [Тестики](https://icq.im/testik_bot)

<a href="https://icq.im/testik_bot"><img src="https://github.com/ICQ-BOTS/tests_bot/blob/main/tests.png" width="100" height="100"></a>


# Оглавление 
 - [Описание](https://github.com/ICQ-BOTS/tests_bot#описание)
 - [Установка](https://github.com/ICQ-BOTS/tests_bot#установка)
 - [Скриншоты работы](https://github.com/ICQ-BOTS/tests_bot#скриншоты-работы)

# Описание
Это твое одеяло. Я буду напоминать тебе каждый день, как я по тебе скучаю.

- База данных: tarantool 2.6
- python3.6

# Установка

1. Установка всех зависимостей 
```bash
pip3 install -r requirements.txt
```

2. Запуск space tarantool.
```bash
tarantoolctl start init.lua
```
> Файл из папки scheme нужно перекинуть в /etc/tarantool/instances.available

3. Вставляем свои данные в config.ini

4. Запуск бота!
```bash
python3 tests_bot.py
```

# Скриншоты работы
<img src="https://github.com/ICQ-BOTS/tests_bot/blob/main/img/1.png" width="400">
<img src="https://github.com/ICQ-BOTS/tests_bot/blob/main/img/2.png" width="400">