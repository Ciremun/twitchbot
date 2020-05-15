import threading
import _globals as g

from _utils import no_ban

def bot_command(*, name, check_func=no_ban):
    def decorator(func):
        def wrapper(message, **kwargs):
            if not check_func(message.author):
                return False
            return func(message, **kwargs)
        g.commands_dict[name] = wrapper
        return wrapper
    return decorator


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
