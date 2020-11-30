class ResultsHandler:
    def __init__(self, name, handle_function, image_request=None):
        self.name = name
        self.handle_function = handle_function
        self.image_request = image_request

    async def handle(self, user, test, answers, addition_info):
        print("ResultsHandler::handle ", self.handle_function)
        return await self.handle_function(user, test, answers, addition_info)


handlers = []


def add_handler(handler):
    global handlers
    handlers.append(handler)


def get_handler_by_name(name):
    global handlers
    for handler in handlers:
        if handler.name == name:
            return handler

    return None


def get_handlers_count():
    return len(handlers)


def get_index_by_handler_name(handler_name):
    global handlers
    for index in range(len(handlers)):
        if handlers[index].name == handler_name:
            return index
    return -1
