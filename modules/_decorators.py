import threading
import _globals as g

from _utils import checkbanlist, checkmodlist


def bot_command(func):  # add command functions to commands dict, check if user is mod/banned on call
    def wrapper(**kwargs):
        if checkbanlist(kwargs['username']):
            return False
        return func(**kwargs)
    g.commands_dict[func.__code__.co_name[:-8]] = wrapper
    return wrapper


def moderator_command(func):
    def wrapper(**kwargs):
        if not checkmodlist(kwargs['username']):
            return False
        return func(**kwargs)
    g.commands_dict[func.__code__.co_name[:-8]] = wrapper
    return wrapper


lock = threading.Lock()


def conn_query(func):
    def wrapper(self, *args, **kwargs):
        with self.conn:
            try:
                lock.acquire(True)
                return func(self, *args, **kwargs)
            finally:
                lock.release()
    return wrapper


def regular_query(func):
    def wrapper(self, *args, **kwargs):
        try:
            lock.acquire(True)
            return func(self, *args, **kwargs)
        finally:
            lock.release()
    return wrapper
