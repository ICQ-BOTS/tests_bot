import result_handler as ResultHandler
import traceback
import logging
import postcards_results_handler
import shawarma_results_handler
import vanilla_results_handler

log = logging.getLogger(__name__)


async def rating_result_handle(user, answers, test, addition_info):
    log.info("rating_result_handle")
    rating = {}
    for answer in answers:
        value = answer.get_value()
        if value in rating:
            rating[value] += 1
        else:
            rating[value] = 1

    max_rating = max(rating.items(), key=lambda item: item[1])
    for test_result in test.get_results():
        if test_result.get_value() == max_rating[0]:
            return test_result.get_text(), test_result.get_image(), None

    return "Упс! Результат с категорией %s не найден" % (max_rating[0]), None, None


async def level_result_handle(user, answers, test, addition_info):
    log.info("level_result_handle")
    points_sum = 0
    for answer in answers:
        try:
            points_sum += int(answer.get_value())
        except:
            traceback.print_exc()
            return "Ошибка в значениях", None, None

    max_result = None

    for result in test.get_results():
        try:
            result_points = int(result.get_value())
            if result_points <= points_sum:
                if not max_result:
                    max_result = (result, result_points)
                elif result_points > max_result[1]:
                    max_result = (result, result_points)

        except:
            traceback.print_exc()
            return "Упс! Результат не найден", None, None

    if not max_result:
        return "Упс! Результат не найден", None, None

    return max_result[0].get_text(), max_result[0].get_image(), None


def init():
    ResultHandler.add_handler(
        ResultHandler.ResultsHandler("default", rating_result_handle)
    )
    ResultHandler.add_handler(
        ResultHandler.ResultsHandler("level", level_result_handle)
    )
    ResultHandler.add_handler(
        ResultHandler.ResultsHandler(
            "random_image", postcards_results_handler.handle_answers
        )
    )
    ResultHandler.add_handler(
        ResultHandler.ResultsHandler(
            "shawarma",
            shawarma_results_handler.handle_answers,
            image_request=[
                "Отправь свою фотографию, чтобы узнать, какая ты шаурма",
                "Пропустить",
            ],
        )
    )
    ResultHandler.add_handler(
        ResultHandler.ResultsHandler("vanilla", vanilla_results_handler.handle_answers)
    )
