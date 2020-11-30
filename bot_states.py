import state
import bot_db
from button_menu import ButtonsMenuBuilder, ButtonCallbackHandler
from io import BytesIO

import utils
import result_handler as ResultHandler
import bot_result_handlers
import postcards_results_handler
import shawarma_results_handler
import vanilla_results_handler
import push_notes
import logging

log = logging.getLogger(__name__)

# --------------------------------root state--------------------------------

RETURN_TO_ROOT_BUTTON_ACTION = "return_to_root"
CANCEL_BUTTON_ACTION = "cancel"


async def default_root_return_handler(bot, user, event, args):
    global root_state
    return state.callback_enter_state(
        root_state, bot, user, event, {"end_session": True}
    )


async def standart_buttons_callback_handler(bot, user, event, args):
    return await user.current_state.buttons_callback_handler.handle_event(
        bot, user, event, user.current_state
    )


ROOT_ADMINS_EDIT_BUTTON_ACTION = "root:admins_edit"
ROOT_TESTS_EDIT_BUTTON_ACTION = "root:tests_edit"
ROOT_TESTS_COMPLETE_BUTTON_ACTION = "root:tests_complete"
ROOT_START_TEST_BUTTON_ACTION = "root:start_test"
ROOT_GET_STATISTICS_BUTTON_ACTION = "root:get_statistics"
ROOT_GET_FAST_STATISTICS_BUTTON_ACTION = "root:get_fast_statistics"
ROOT_SEND_PUSH_NOTES = "root:send_push_notes"

current_edit_user = None


def lock_tests_edit(user):
    global current_edit_user
    if current_edit_user:
        return False

    current_edit_user = user
    return True


def unlock_tests_edit():
    global current_edit_user
    current_edit_user = None


async def on_root_enter(bot, user, event, args):
    global current_edit_user

    if current_edit_user == user:
        bot_db.update_tests()
        log.info("update tests")
        unlock_tests_edit()

    bmb = ButtonsMenuBuilder()
    if user.permissions < 2 or "test_mode" in args:
        print("root event")

        if user.permissions > 0:
            user.complete_tests = bot_db.tests_list.get_all_tests()
        else:
            user.complete_tests = bot_db.tests_list.get_published_tests()

        for test_index in range(len(user.complete_tests)):
            test = user.complete_tests[test_index]
            if user.permissions > 0:
                test_button_text = "%s (%d)" % (
                    test.get_name(),
                    test.get_publish_status(),
                )
            else:
                test_button_text = "%s" % (test.get_name())
            bmb.add_action_button(
                test_button_text,
                ROOT_START_TEST_BUTTON_ACTION,
                {"test_index": test_index},
            )
            if test_index != len(user.complete_tests) - 1:
                bmb.next_row()

        if user.permissions > 0:
            bmb.next_row()
            bmb.add_action_button(
                "Вернуться в главное меню", RETURN_TO_ROOT_BUTTON_ACTION
            )

        await state.show_message(
            bot=bot,
            user=user,
            text="Привет!\nУ меня есть несколько клевых тестов для тебя 😎",
            buttons=bmb.get_to_send(),
        )
    else:
        bmb.add_action_button("Список администраторов", ROOT_ADMINS_EDIT_BUTTON_ACTION)
        bmb.add_action_button("Ред. тесты", ROOT_TESTS_EDIT_BUTTON_ACTION)
        bmb.add_action_button("Выполнить тесты", ROOT_TESTS_COMPLETE_BUTTON_ACTION)
        bmb.next_row()
        bmb.add_action_button("Статистика", ROOT_GET_STATISTICS_BUTTON_ACTION)
        bmb.add_action_button(
            "Быстрая статистика", ROOT_GET_FAST_STATISTICS_BUTTON_ACTION
        )
        bmb.next_row()
        bmb.add_action_button("Разослать уведомление", ROOT_SEND_PUSH_NOTES)
        await state.show_message(
            bot=bot, user=user, text="Меню администратора", buttons=bmb.get_to_send()
        )

    if "end_session" in args:
        return None
    return state.callback_wait_for_input(bot, user, False)


async def admins_edit_start(bot, user, event, args):
    global admins_edit_state
    return state.callback_enter_state(admins_edit_state, bot, user, event)


async def tests_edit_start(bot, user, event, args):
    global tests_edit_state, current_edit_user

    if not lock_tests_edit(user):
        await state.show_message(
            bot=bot,
            user=user,
            text="В данный момент тесты редактируются другим администратором",
            force_new_message=True,
            stay_in_chat=True,
        )
        return state.callback_enter_state(root_state, bot, user, event)

    return state.callback_enter_state(tests_edit_state, bot, user, event)


async def tests_complete_mod_start(bot, user, event, args):
    global root_state
    return state.callback_enter_state(root_state, bot, user, event, {"test_mode": True})


async def start_test(bot, user, event, args):
    global test_state
    try:
        user.test = utils.array_element_normal(
            user.complete_tests, int(args["test_index"])
        )
        user.questions = user.test.get_questions()
        user.answers = []
    except Exception as e:
        return state.callback_enter_state(root_state, bot, user, event)

    if not user.test:
        return state.callback_enter_state(root_state, bot, user, event)

    user.question_index = 0

    return state.callback_enter_state(test_state, bot, user, event)


async def get_statistics(bot, user, event, args):
    workbook = bot_db.get_statistics()
    file = utils.get_next_file_name("statistics/statistics_%d.xlsx")
    workbook.save(file)

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("Спасибо!", RETURN_TO_ROOT_BUTTON_ACTION)
    await state.show_message(
        bot=bot,
        user=user,
        text="Статистика по тестам:",
        buttons=bmb.get_to_send(),
        force_new_message=True,
        stay_in_chat=True,
        file=open(file, "rb"),
    )
    return state.callback_wait_for_input(bot, user, False)


async def get_fast_statistics(bot, user, event, args):
    if user.permissions == 0:
        return state.callback_enter_state(root_state, bot, user, event)
    return state.callback_enter_state(fast_statistics, bot, user, event)


def get_users(db_users):
    for user_row in db_users:
        yield user_row[0]


async def send_push_notes(bot, user, event, args):
    if user.permissions == 0:
        return state.callback_enter_state(
            root_state, bot, user, event, {"end_session": True}
        )

    await state.show_message(
        bot=bot,
        user=user,
        text="Введите сообщение, которое нужно разослать или q для отмены",
        force_new_message=True,
        stay_in_chat=True,
    )
    text = await root_state.wait_for_text_input_loop(bot, user)
    if text == "q":
        return state.callback_enter_state(
            root_state, bot, user, event, {"end_session": True}
        )

    note_array = text.split(";")

    bmb = ButtonsMenuBuilder()
    if len(note_array) == 2:
        bmb.add_action_button(note_array[1], RETURN_TO_ROOT_BUTTON_ACTION)

    response = await bot.send_text(chat_id=user.id, text="Начинаю рассылку")

    push_notes.start_send(
        event_loop,
        bot,
        note_array[0],
        callback_user_id=user.id,
        buttons=bmb.get_to_send(),
        indicator_msg_id=response["msgId"],
        users_list=get_users(bot_db.get_users()),
    )

    state.clear_last_message(user)
    return state.callback_enter_state(
        root_state, bot, user, event, {"end_session": True}
    )


# --------------------------------root state--------------------------------

# ----------------------------admins edit state--------------------------------


async def on_admins_edit_enter(bot, user, event, args):
    global admins_edit_state, current_edit_user

    current_edit_user = user

    list_text = "Администраторы:"
    for admin_row in bot_db.get_admins_list():
        list_text += "\n" + admin_row[0]

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("На главную", RETURN_TO_ROOT_BUTTON_ACTION)
    await state.show_message(
        bot=bot, user=user, text=list_text, buttons=bmb.get_to_send()
    )

    return state.callback_wait_for_input(bot, user, False)


# ----------------------------admins edit state--------------------------------

# ----------------------------tests edit state--------------------------------

TESTS_EDIT_ADD_BUTTON_ACTION = "tests_edit:add"
TESTS_EDIT_EDIT_BUTTON_ACTION = "tests_edit:edit"
TESTS_EDIT_REMOVE_BUTTON_ACTION = "tests_edit:remove"


async def on_tests_edit_enter(bot, user, event, args):
    global tests_edit_state
    list_text = "Список тестов:"
    tests_list = bot_db.load_tests_list_clone()
    number = 1
    for test in tests_list.get_all_tests():
        list_text += "\n%d. %s (%d)" % (number, test.data[1], test.get_publish_status())
        number += 1

    user.edit_tests = tests_list

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("Добавить тест", TESTS_EDIT_ADD_BUTTON_ACTION)
    bmb.add_action_button("Ред. тест", TESTS_EDIT_EDIT_BUTTON_ACTION)
    bmb.add_action_button("Удалить тест", TESTS_EDIT_REMOVE_BUTTON_ACTION)
    bmb.next_row()
    bmb.add_action_button("Завершить редактирование", RETURN_TO_ROOT_BUTTON_ACTION)
    await state.show_message(
        bot=bot, user=user, text=list_text, buttons=bmb.get_to_send()
    )

    return state.callback_wait_for_input(bot, user, False)


async def tests_edit_add_test(bot, user, event, args):
    global tests_edit_state
    response_text = await tests_edit_state.wait_for_text_input_loop(
        bot, user, "Введите имя добавляемого теста"
    )
    bot_db.add_test(response_text)
    return state.callback_enter_state(tests_edit_state, bot, user)


async def tests_edit_edit_test(bot, user, event, args):
    global tests_edit_state, one_test_edit_state

    response_text = await tests_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер теста"
    )
    try:
        user.edit_test = utils.array_element_normal(
            user.edit_tests.get_all_tests(), int(response_text) - 1
        )
        if not user.edit_test:
            await state.show_message(
                bot,
                user,
                force_new_message=True,
                text="Некорректный номер теста",
                stay_in_chat=True,
            )
            return state.callback_enter_state(tests_edit_state, bot, user)

        return state.callback_enter_state(one_test_edit_state, bot, user)
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер теста",
            stay_in_chat=True,
        )
        return state.callback_enter_state(tests_edit_state, bot, user)


async def tests_edit_remove_test(bot, user, event, args):
    global tests_edit_state
    response_text = await tests_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер теста"
    )
    try:
        utils.array_element_normal(
            user.edit_tests.get_all_tests(), int(response_text) - 1
        ).remove()
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер теста",
            stay_in_chat=True,
        )

    return state.callback_enter_state(tests_edit_state, bot, user)


# ----------------------------tests edit state--------------------------------

# ----------------------------one test edit state--------------------------------

ONE_TEST_EDIT_ADD_RESULT_BUTTON_ACTION = "one_test_edit:add_result_button"
ONE_TEST_EDIT_EDIT_RESULT_BUTTON_ACTION = "one_test_edit:edit_result_button"
ONE_TEST_EDIT_REMOVE_RESULT_BUTTON_ACTION = "one_test_edit:remove_result_button"

ONE_TEST_EDIT_ADD_QUESTION_BUTTON_ACTION = "one_test_edit:add_question_button"
ONE_TEST_EDIT_EDIT_QUESTION_BUTTON_ACTION = "one_test_edit:edit_question_button"
ONE_TEST_EDIT_REMOVE_QUESTION_BUTTON_ACTION = "one_test_edit:remove_question_button"


ONE_TEST_EDIT_CHANGE_HANDLER_BUTTON_ACTION = "one_test_edit:change_handler"
ONE_TEST_EDIT_CHANGE_PUBLIC_STATUS_BUTTON_ACTION = "one_test_edit:change_public_status"


def one_test_edit_user_reset(user):
    user.edit_test = None
    user.edit_results = None
    user.edit_questions = None


async def on_one_test_edit_enter(bot, user, event, args):
    try:

        edit_test = user.edit_test

        if not edit_test:
            return state.callback_enter_state(tests_edit_state, bot, user, event)

        edit_test.load_info()

        message_text = "Редактирование: %s" % (edit_test.get_name())

        message_text += "\n\nРезультаты теста: "
        edit_results = edit_test.get_results()
        counter = 1
        for edit_result in edit_results:
            message_text += "\n%d. %s (%s)" % (
                counter,
                edit_result.get_formatted_text(),
                edit_result.get_value(),
            )
            counter += 1

        user.edit_results = edit_results

        message_text += "\n\nВопросы: "
        edit_questions = edit_test.get_questions()
        counter = 1
        for question in edit_questions:
            message_text += "\n%d. %s" % (counter, question.get_formatted_text())
            for answer in question.answers:
                message_text += "\n- %s (%s)" % (
                    answer.get_formatted_text(),
                    answer.get_value(),
                )
            message_text += "\n"
            counter += 1

        user.edit_questions = edit_questions

        bmb = ButtonsMenuBuilder()
        bmb.add_action_button(
            "Добавить\nрезультат", ONE_TEST_EDIT_ADD_RESULT_BUTTON_ACTION
        )
        bmb.add_action_button(
            "Ред.\nрезультат", ONE_TEST_EDIT_EDIT_RESULT_BUTTON_ACTION
        )
        bmb.add_action_button(
            "Удалить\nрезультат", ONE_TEST_EDIT_REMOVE_RESULT_BUTTON_ACTION
        )
        bmb.next_row()
        bmb.add_action_button(
            "Добавить\nвопрос", ONE_TEST_EDIT_ADD_QUESTION_BUTTON_ACTION
        )
        bmb.add_action_button("Ред.\nвопрос", ONE_TEST_EDIT_EDIT_QUESTION_BUTTON_ACTION)
        bmb.add_action_button(
            "Удалить\nвопрос", ONE_TEST_EDIT_REMOVE_QUESTION_BUTTON_ACTION
        )
        bmb.next_row()
        bmb.add_action_button(
            "Обработчик: %s" % (edit_test.get_handle_module()),
            ONE_TEST_EDIT_CHANGE_HANDLER_BUTTON_ACTION,
        )
        bmb.next_row()
        if edit_test.get_publish_status() == 0:
            change_public_status_text = "Опубликовать"
        else:
            change_public_status_text = "Снять с публикации"
        bmb.add_action_button(
            change_public_status_text, ONE_TEST_EDIT_CHANGE_PUBLIC_STATUS_BUTTON_ACTION
        )

        bmb.next_row()
        bmb.add_action_button("Завершить редактирование", CANCEL_BUTTON_ACTION)
        await state.show_message(
            bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
        )
        return state.callback_wait_for_input(bot, user, False, args)
    except:
        # print('exception')
        one_test_edit_user_reset(user)
        return state.callback_enter_state(tests_edit_state, bot, user, event)


async def one_test_edit_add_result(bot, user, event, args):
    global one_test_edit_state
    (
        test_result_text,
        edit_result_image,
    ) = await one_test_edit_state.wait_for_multiple_data_input_loop(
        bot, user, "Введите текст результата", required_type="image"
    )
    test_result_value = await one_test_edit_state.wait_for_text_input_loop(
        bot, user, "Введите значение результата"
    )
    bot_db.add_test_result(
        user.edit_test.get_id(), test_result_text, edit_result_image, test_result_value
    )
    return state.callback_enter_state(one_test_edit_state, bot, user)


async def one_test_edit_edit_result(bot, user, event, args):
    global one_test_edit_state, test_result_edit_state
    response_text = await one_test_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер результата теста"
    )
    try:
        user.edit_test_result = utils.array_element_normal(
            user.edit_test.get_results(), int(response_text) - 1
        )
        if not user.edit_test_result:
            await state.show_message(
                bot,
                user,
                force_new_message=True,
                text="Некорректный номер результата",
                stay_in_chat=True,
            )
            return state.callback_enter_state(one_test_edit_state, bot, user)

        return state.callback_enter_state(test_result_edit_state, bot, user)
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер результата",
            stay_in_chat=True,
        )
        return state.callback_enter_state(one_test_edit_state, bot, user)


async def one_test_edit_remove_result(bot, user, event, args):
    global one_test_edit_state
    response_text = await one_test_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер результата"
    )
    try:
        utils.array_element_normal(
            user.edit_test.get_results(), int(response_text) - 1
        ).remove()
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер результата",
            stay_in_chat=True,
        )

    return state.callback_enter_state(one_test_edit_state, bot, user)


async def one_test_edit_add_question(bot, user, event, args):
    global one_test_edit_state
    (
        question_text,
        question_image,
    ) = await one_test_edit_state.wait_for_multiple_data_input_loop(
        bot, user, "Введите текст вопроса", required_type="image"
    )
    bot_db.add_question(user.edit_test.get_id(), question_text, question_image)
    return state.callback_enter_state(one_test_edit_state, bot, user)


async def one_test_edit_edit_question(bot, user, event, args):
    global one_test_edit_state, question_edit_state

    response_text = await one_test_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер вопроса"
    )
    try:
        user.edit_question = utils.array_element_normal(
            user.edit_test.get_questions(), int(response_text) - 1
        )
        if not user.edit_question:
            await state.show_message(
                bot,
                user,
                force_new_message=True,
                text="Некорректный номер вопроса",
                stay_in_chat=True,
            )
            return state.callback_enter_state(one_test_edit_state, bot, user)

        return state.callback_enter_state(question_edit_state, bot, user)
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер вопроса",
            stay_in_chat=True,
        )
        return state.callback_enter_state(one_test_edit_state, bot, user)


async def one_test_edit_remove_question(bot, user, event, args):
    global one_test_edit_state
    response_text = await tests_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер вопроса"
    )
    try:
        utils.array_element_normal(
            user.edit_test.questions, int(response_text) - 1
        ).remove()
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер вопроса",
            stay_in_chat=True,
        )

    return state.callback_enter_state(one_test_edit_state, bot, user)


async def one_test_edit_change_handler(bot, user, event, args):
    user.edit_test.set_handler_module(
        ResultHandler.handlers[
            (
                ResultHandler.get_index_by_handler_name(
                    user.edit_test.get_handle_module()
                )
                + 1
            )
            % ResultHandler.get_handlers_count()
        ].name
    )
    user.edit_test.update_info()
    return state.callback_enter_state(one_test_edit_state, bot, user, event)


async def one_test_edit_change_public_status(bot, user, event, args):
    user.edit_test.set_publish_status((user.edit_test.get_publish_status() + 1) % 2)
    user.edit_test.update_info()
    return state.callback_enter_state(one_test_edit_state, bot, user, event)


async def one_test_edit_cancel(bot, user, event, args):
    global tests_edit_state
    one_test_edit_user_reset(user)
    return state.callback_enter_state(tests_edit_state, bot, user, event)


# ----------------------------one test edit state--------------------------------

# ----------------------------question edit state--------------------------------

QUESTION_EDIT_CHANGE_TEXT_BUTTON_ACTION = "question_edit:change_text"
QUESTION_EDIT_ADD_ANSWER_BUTTON_ACTION = "question_edit:add_answer"
QUESTION_EDIT_EDIT_ANSWER_BUTTON_ACTION = "question_edit:edit_answer"
QUESTION_EDIT_REMOVE_ANSWER_BUTTON_ACTION = "question_edit:remove_answer"


def edit_question_user_reset(user):
    user.edit_question = None


async def on_question_edit_enter(bot, user, event, args):
    global one_test_edit_state

    edit_question = user.edit_question
    if not edit_question:
        return state.callback_enter_state(one_test_edit_state, bot, user, event)

    edit_question.load_info()

    message_text = edit_question.get_formatted_text()
    edit_answers = edit_question.get_answers()
    counter = 1
    for edit_answer in edit_answers:
        message_text += "\n%d. %s (%s)" % (
            counter,
            edit_answer.get_formatted_text(),
            edit_answer.get_value(),
        )
        counter += 1

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button(
        "Изменить текст вопроса", QUESTION_EDIT_CHANGE_TEXT_BUTTON_ACTION
    )
    bmb.next_row()
    bmb.add_action_button(
        "Добавить вариант ответа", QUESTION_EDIT_ADD_ANSWER_BUTTON_ACTION
    )
    bmb.next_row()
    bmb.add_action_button(
        "Ред. вариант ответа", QUESTION_EDIT_EDIT_ANSWER_BUTTON_ACTION
    )
    bmb.next_row()
    bmb.add_action_button(
        "Удалить вариант ответа", QUESTION_EDIT_REMOVE_ANSWER_BUTTON_ACTION
    )
    bmb.next_row()
    bmb.add_action_button("Сохранить изменения и выйти", CANCEL_BUTTON_ACTION)

    await state.show_message(
        bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
    )
    return state.callback_wait_for_input(bot, user, False, args)


async def question_edit_change_text(bot, user, event, args):
    global question_edit_state
    (
        question_text,
        question_image,
    ) = await test_result_edit_state.wait_for_multiple_data_input_loop(
        bot, user, "Введите текст вопроса", required_type="image"
    )
    user.edit_question.set_text(question_text)
    user.edit_question.set_image(question_image)
    user.edit_question.update_info()
    return state.callback_enter_state(question_edit_state, bot, user)


async def question_edit_add_answer(bot, user, event, args):
    global question_edit_state
    (
        answer_text,
        answer_image,
    ) = await question_edit_state.wait_for_multiple_data_input_loop(
        bot, user, "Введите текст ответа", required_type="image"
    )
    answer_value = await question_edit_state.wait_for_text_input_loop(
        bot, user, "Введите значение ответа"
    )
    bot_db.add_answer(
        user.edit_question.get_id(), answer_text, answer_image, answer_value
    )
    return state.callback_enter_state(question_edit_state, bot, user)


async def question_edit_edit_answer(bot, user, event, args):
    global question_edit_state, answer_edit_state
    response_text = await one_test_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер ответа"
    )
    try:
        user.edit_answer = utils.array_element_normal(
            user.edit_question.answers, int(response_text) - 1
        )
        if not user.edit_answer:
            await state.show_message(
                bot,
                user,
                force_new_message=True,
                text="Некорректный номер ответа",
                stay_in_chat=True,
            )
            return state.callback_enter_state(question_edit_state, bot, user)

        return state.callback_enter_state(answer_edit_state, bot, user)
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер ответа",
            stay_in_chat=True,
        )
        return state.callback_enter_state(question_edit_state, bot, user)


async def question_edit_remove_answer(bot, user, event, args):
    global question_edit_state
    response_text = await tests_edit_state.wait_for_text_input_loop(
        bot, user, "Введите номер ответа"
    )
    try:
        utils.array_element_normal(
            user.edit_question.answers, int(response_text) - 1
        ).remove()
    except:
        await state.show_message(
            bot,
            user,
            force_new_message=True,
            text="Некорректный номер ответа",
            stay_in_chat=True,
        )

    return state.callback_enter_state(question_edit_state, bot, user)


async def question_edit_cancel(bot, user, event, args):
    global one_test_edit_state
    edit_question_user_reset(user)
    return state.callback_enter_state(one_test_edit_state, bot, user, event)


# ----------------------------question edit state--------------------------------

# ----------------------------Test result edit state--------------------------------

TEST_RESULT_EDIT_CHANGE_TEXT_BUTTON_ACTION = "test_result_edit:change_text"
TEST_RESULT_EDIT_CHANGE_VALUE_BUTTON_ACTION = "answer_edit:change_value"


def test_result_edit_reset(user):
    user.edit_test_result = None


async def on_test_result_edit_enter(bot, user, event, args):
    global test_result_edit_state

    edit_test_result = user.edit_test_result
    if not edit_test_result:
        return state.callback_enter_state(one_test_edit_state, bot, user, event)

    edit_test_result.load_info()

    message_text = "%s; %s" % (
        edit_test_result.get_formatted_text(),
        edit_test_result.get_value(),
    )

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("Изменить текст", TEST_RESULT_EDIT_CHANGE_TEXT_BUTTON_ACTION)
    bmb.add_action_button(
        "Изменить значение", TEST_RESULT_EDIT_CHANGE_VALUE_BUTTON_ACTION
    )
    bmb.next_row()
    bmb.add_action_button("Сохранить изменения и выйти", CANCEL_BUTTON_ACTION)

    await state.show_message(
        bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
    )
    return state.callback_wait_for_input(bot, user, False, args)


async def test_result_edit_change_text(bot, user, event, args):
    global test_result_edit_state
    (
        result_text,
        result_image,
    ) = await test_result_edit_state.wait_for_multiple_data_input_loop(
        bot, user, "Введите текст результата", required_type="image"
    )
    user.edit_test_result.set_text(result_text)
    user.edit_test_result.set_image(result_image)
    user.edit_test_result.update_info()
    return state.callback_enter_state(test_result_edit_state, bot, user, event)


async def test_result_edit_change_value(bot, user, event, args):
    global test_result_edit_state
    answer_text = await test_result_edit_state.wait_for_text_input_loop(
        bot, user, "Введите значение результата"
    )
    user.edit_test_result.set_value(answer_text)
    user.edit_test_result.update_info()
    return state.callback_enter_state(test_result_edit_state, bot, user, event)


async def test_result_edit_cancel(bot, user, event, args):
    global one_test_edit_state
    test_result_edit_reset(user)
    return state.callback_enter_state(one_test_edit_state, bot, user, event)


# ----------------------------Test result edit state--------------------------------

# ----------------------------Answer edit state--------------------------------

ANSWER_EDIT_CHANGE_TEXT_BUTTON_ACTION = "answer_edit:change_text"
ANSWER_EDIT_CHANGE_VALUE_BUTTON_ACTION = "answer_edit:change_value"


def edit_answer_user_reset(user):
    user.edit_answer = None


async def on_answer_edit_enter(bot, user, event, args):
    global answer_edit_state
    edit_answer = user.edit_answer
    if not edit_answer:
        return state.callback_enter_state(one_test_edit_state, bot, user, event)

    edit_answer.load_info()

    message_text = "%s; %s" % (
        edit_answer.get_formatted_text(),
        edit_answer.get_value(),
    )

    bmb = ButtonsMenuBuilder()
    bmb.add_action_button("Изменить текст", ANSWER_EDIT_CHANGE_TEXT_BUTTON_ACTION)
    bmb.add_action_button("Изменить значение", ANSWER_EDIT_CHANGE_VALUE_BUTTON_ACTION)
    bmb.next_row()
    bmb.add_action_button("Сохранить изменения и выйти", CANCEL_BUTTON_ACTION)

    await state.show_message(
        bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
    )
    return state.callback_wait_for_input(bot, user, False, args)


async def answer_edit_change_text(bot, user, event, args):
    global answer_edit_state
    (
        answer_text,
        answer_image,
    ) = await answer_edit_state.wait_for_multiple_data_input_loop(
        bot, user, "Введите текст ответа", required_type="image"
    )
    user.edit_answer.set_text(answer_text)
    user.edit_answer.set_image(answer_image)
    user.edit_answer.update_info()
    return state.callback_enter_state(answer_edit_state, bot, user, event)


async def answer_edit_change_value(bot, user, event, args):
    global answer_edit_state
    answer_text = await answer_edit_state.wait_for_text_input_loop(
        bot, user, "Введите значение ответа"
    )
    user.edit_answer.set_value(answer_text)
    user.edit_answer.update_info()
    return state.callback_enter_state(answer_edit_state, bot, user, event)


async def answer_edit_cancel(bot, user, event, args):
    global question_edit_state
    edit_answer_user_reset(user)
    return state.callback_enter_state(question_edit_state, bot, user, event)


# ----------------------------Answer edit state--------------------------------

# ----------------------------Test select state--------------------------------

TEST_ANSWER_BUTTON_ACTION = "test:answer"


async def on_test_complete_enter(bot, user, event, args):
    global test_state
    # print('enter test state')

    if "completed_test" in user.state_params:
        del user.state_params["completed_test"]
        return state.callback_enter_state(root_state, bot, user, event)

    bmb = ButtonsMenuBuilder()
    if user.question_index < len(user.test.questions):
        new_question = user.questions[user.question_index]
        message_text = new_question.get_text() + "\n"

        user.current_answers_list = new_question.answers
        # print('question: ', new_question.has_image_answers())

        # if new_question.has_image_answers():
        for answer_index in range(len(user.current_answers_list)):
            if (user.test.get_id() != 3) and (user.test.get_id() != 4):
                answer = user.current_answers_list[answer_index]
                answer_letter = utils.ru_char_from_index(answer_index)
                message_text += (
                    "\n" + answer_letter + ") " + answer.get_formatted_text()
                )
                bmb.add_action_button(
                    answer_letter,
                    TEST_ANSWER_BUTTON_ACTION,
                    {"answer_index": answer_index},
                )
                bmb.next_row()
            else:
                answer = user.current_answers_list[answer_index]
                bmb.add_action_button(
                    utils.ru_char_from_index(answer_index) + ") " + answer.get_text(),
                    TEST_ANSWER_BUTTON_ACTION,
                    {"answer_index": answer_index},
                )
                bmb.next_row()

        # print(message_text)

        bmb.add_action_button("Вернуться на главную", CANCEL_BUTTON_ACTION)
        await state.show_message(
            bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
        )
    else:
        print("Handle results")
        result_handler = ResultHandler.get_handler_by_name(
            user.test.get_handle_module()
        )
        addition_info = None
        if not result_handler.image_request is None:
            abmb = ButtonsMenuBuilder()
            abmb.add_action_button(result_handler.image_request[1], "cancel")
            await state.show_message(
                bot=bot,
                user=user,
                text=result_handler.image_request[0],
                buttons=abmb.get_to_send(),
            )

            user_input_event = await test_state.wait_for_input(
                bot,
                user,
                False,
                forward_args={},
                call_on_event=False,
            )
            if utils.is_button_click(user_input_event):
                await state.send_query_response(bot, user_input_event)
            else:
                state.clear_last_message(user)

            addition_info = utils.get_attachment_from_event(user_input_event, "image")

        (
            message_text,
            message_image,
            data_image,
        ) = await result_handler.handle(user, user.answers, user.test, addition_info)

        print("Handle")
        # long response handler
        if (message_text is None) and (message_image is None) and (data_image is None):
            print("All is None")
            bot_db.add_user_test_complete(user.id, user.test.get_id())
            return None

        if data_image:
            # file_name = utils.get_next_file_name('temp/random_result_%d.jpg')
            byte_io = BytesIO()
            data_image.save(byte_io, "JPEG")
            # f = open(file_name, 'rb')
            byte_io.seek(0)
            byte_io.name = "generated_image.jpg"
            upload_response = await bot.send_file(chat_id=TRASH_CHAT, file=byte_io)
            log.info(f"Upload response: {upload_response}")
            message_image = upload_response.get("fileId", None)
            log.info(f"Image id: {message_image}")
            data_image = None

        # print('Handle results 2')
        bot_db.add_user_test_complete(user.id, user.test.get_id())
        # print('Handle results 3')
        bmb.add_action_button("Пройти ещё один тест", CANCEL_BUTTON_ACTION)
        # print('Handle results 4')
        await state.show_message(
            bot=bot,
            user=user,
            text=message_text,
            message_image=message_image,
            buttons=bmb.get_to_send(),
            # stay_in_chat=True,
        )
        # print('Handle results 5')
        user.state_params["completed_test"] = True

    return state.callback_wait_for_input(bot, user, False, args)


async def test_answer(bot, user, event, args):
    global test_state

    # print('test_answer: ', args['answer_index'])
    # print('question: ', user.questions[user.question_index])
    user.answers.append(
        user.questions[user.question_index].answers[args["answer_index"]]
    )
    user.question_index += 1

    # print('end')

    return state.callback_enter_state(test_state, bot, user, event)


# ----------------------------Test select state--------------------------------

# ----------------------------Fast statistics state--------------------------------


async def on_fast_statistics_enter(bot, user, event, args):
    # print('enter test state')

    bmb = ButtonsMenuBuilder()

    tests, common = bot_db.get_fast_statistics()

    message_text = "Ститстика прохождений тестов:"

    for key, value in tests.items():
        message_text += "\n%s: %d (%d уникальных)" % (
            value.test_name,
            value.count,
            value.users,
        )

    bmb.add_action_button("Спасибо!", CANCEL_BUTTON_ACTION)

    message_text += "\n\nВсего: %d (%d уникальных)" % (common.count, common.users)
    await state.show_message(
        bot=bot, user=user, text=message_text, buttons=bmb.get_to_send()
    )
    return state.callback_wait_for_input(bot, user, False, args)


# ----------------------------Fast statistics state--------------------------------

# send


def init(
    el,
    bot,
    trash_chat,
    postcards_ip,
    postcards_port,
    put_face_ip,
    put_face_port,
    db_host,
    db_port,
):
    global TRASH_CHAT, root_state, admins_edit_state, tests_edit_state, one_test_edit_state, question_edit_state, test_result_edit_state, answer_edit_state, test_state, fast_statistics, event_loop
    TRASH_CHAT = trash_chat
    event_loop = el
    bot_db.connect(db_host, db_port)
    bot_db.update_tests()

    postcards_results_handler.init(postcards_ip, postcards_port)
    vanilla_results_handler.init(postcards_ip, postcards_port)
    shawarma_results_handler.init(put_face_ip, put_face_port, bot)
    bot_result_handlers.init()
    # root state

    root_state = state.State("root", on_root_enter, standart_buttons_callback_handler)
    root_state.buttons_callback_handler = ButtonCallbackHandler()
    root_state.buttons_callback_handler.add_action(
        ROOT_ADMINS_EDIT_BUTTON_ACTION, admins_edit_start
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_TESTS_EDIT_BUTTON_ACTION, tests_edit_start
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_TESTS_COMPLETE_BUTTON_ACTION, tests_complete_mod_start
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_START_TEST_BUTTON_ACTION, start_test
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_GET_STATISTICS_BUTTON_ACTION, get_statistics
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_GET_FAST_STATISTICS_BUTTON_ACTION, get_fast_statistics
    )
    root_state.buttons_callback_handler.add_action(
        ROOT_SEND_PUSH_NOTES, send_push_notes
    )

    root_state.buttons_callback_handler.add_action(
        RETURN_TO_ROOT_BUTTON_ACTION, default_root_return_handler
    )

    # admins edit state

    admins_edit_state = state.State(
        "admins edit", on_admins_edit_enter, standart_buttons_callback_handler
    )
    admins_edit_state.buttons_callback_handler = ButtonCallbackHandler()
    admins_edit_state.buttons_callback_handler.add_action(
        RETURN_TO_ROOT_BUTTON_ACTION, default_root_return_handler
    )

    # tests edit state

    tests_edit_state = state.State(
        "tests edit", on_tests_edit_enter, standart_buttons_callback_handler
    )
    tests_edit_state.buttons_callback_handler = ButtonCallbackHandler()
    tests_edit_state.buttons_callback_handler.add_action(
        TESTS_EDIT_ADD_BUTTON_ACTION, tests_edit_add_test
    )
    tests_edit_state.buttons_callback_handler.add_action(
        TESTS_EDIT_EDIT_BUTTON_ACTION, tests_edit_edit_test
    )
    tests_edit_state.buttons_callback_handler.add_action(
        TESTS_EDIT_REMOVE_BUTTON_ACTION, tests_edit_remove_test
    )

    tests_edit_state.buttons_callback_handler.add_action(
        RETURN_TO_ROOT_BUTTON_ACTION, default_root_return_handler
    )

    # one test edit state

    one_test_edit_state = state.State(
        "one test edit", on_one_test_edit_enter, standart_buttons_callback_handler
    )
    one_test_edit_state.buttons_callback_handler = ButtonCallbackHandler()
    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_ADD_RESULT_BUTTON_ACTION, one_test_edit_add_result
    )
    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_EDIT_RESULT_BUTTON_ACTION, one_test_edit_edit_result
    )
    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_REMOVE_RESULT_BUTTON_ACTION, one_test_edit_remove_result
    )

    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_ADD_QUESTION_BUTTON_ACTION, one_test_edit_add_question
    )
    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_EDIT_QUESTION_BUTTON_ACTION, one_test_edit_edit_question
    )
    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_REMOVE_QUESTION_BUTTON_ACTION, one_test_edit_remove_question
    )

    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_CHANGE_HANDLER_BUTTON_ACTION, one_test_edit_change_handler
    )
    one_test_edit_state.buttons_callback_handler.add_action(
        ONE_TEST_EDIT_CHANGE_PUBLIC_STATUS_BUTTON_ACTION,
        one_test_edit_change_public_status,
    )
    one_test_edit_state.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, one_test_edit_cancel
    )

    # question edit state

    question_edit_state = state.State(
        "question edit", on_question_edit_enter, standart_buttons_callback_handler
    )
    question_edit_state.buttons_callback_handler = ButtonCallbackHandler()

    question_edit_state.buttons_callback_handler.add_action(
        QUESTION_EDIT_CHANGE_TEXT_BUTTON_ACTION, question_edit_change_text
    )
    question_edit_state.buttons_callback_handler.add_action(
        QUESTION_EDIT_ADD_ANSWER_BUTTON_ACTION, question_edit_add_answer
    )
    question_edit_state.buttons_callback_handler.add_action(
        QUESTION_EDIT_EDIT_ANSWER_BUTTON_ACTION, question_edit_edit_answer
    )
    question_edit_state.buttons_callback_handler.add_action(
        QUESTION_EDIT_REMOVE_ANSWER_BUTTON_ACTION, question_edit_remove_answer
    )
    question_edit_state.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, question_edit_cancel
    )

    # Test result edit state

    test_result_edit_state = state.State(
        "Test result edit", on_test_result_edit_enter, standart_buttons_callback_handler
    )
    test_result_edit_state.buttons_callback_handler = ButtonCallbackHandler()

    test_result_edit_state.buttons_callback_handler.add_action(
        TEST_RESULT_EDIT_CHANGE_TEXT_BUTTON_ACTION, test_result_edit_change_text
    )
    test_result_edit_state.buttons_callback_handler.add_action(
        TEST_RESULT_EDIT_CHANGE_VALUE_BUTTON_ACTION, test_result_edit_change_value
    )
    test_result_edit_state.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, test_result_edit_cancel
    )

    # Answer edit state

    answer_edit_state = state.State(
        "Answer edit", on_answer_edit_enter, standart_buttons_callback_handler
    )
    answer_edit_state.buttons_callback_handler = ButtonCallbackHandler()

    answer_edit_state.buttons_callback_handler.add_action(
        ANSWER_EDIT_CHANGE_TEXT_BUTTON_ACTION, answer_edit_change_text
    )
    answer_edit_state.buttons_callback_handler.add_action(
        ANSWER_EDIT_CHANGE_VALUE_BUTTON_ACTION, answer_edit_change_value
    )
    answer_edit_state.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, answer_edit_cancel
    )

    # Test select state

    test_state = state.State(
        "Test complete", on_test_complete_enter, standart_buttons_callback_handler
    )
    test_state.buttons_callback_handler = ButtonCallbackHandler()

    test_state.buttons_callback_handler.add_action(
        TEST_ANSWER_BUTTON_ACTION, test_answer
    )
    test_state.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, default_root_return_handler
    )

    # Fast statistics

    fast_statistics = state.State(
        "Fast statistics", on_fast_statistics_enter, standart_buttons_callback_handler
    )
    fast_statistics.buttons_callback_handler = ButtonCallbackHandler()

    fast_statistics.buttons_callback_handler.add_action(
        CANCEL_BUTTON_ACTION, default_root_return_handler
    )

    state.set_root_state(root_state)
