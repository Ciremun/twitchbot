import modules.globals as g

from modules.utils import checkbanlist, checkmodlist


def bot_command(func):  # add command functions to commands dict, check if user is mod/banned on call
    def wrapper(**kwargs):
        if checkbanlist(kwargs['username']):
            return
        return func(**kwargs)

    g.commands_dict[func.__code__.co_name[:-8]] = wrapper
    return wrapper


def moderator_command(func):
    def wrapper(**kwargs):
        if not checkmodlist(kwargs['username']):
            return
        return func(**kwargs)

    g.commands_dict[func.__code__.co_name[:-8]] = wrapper
    return wrapper
