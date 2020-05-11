import queue
import threading
import pyttsx3
import _globals as g

from _regex import regex, re
from _utils import checkbanlist, send_message, get_tts_vc_key


class ThreadTTS(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.engine = None
        self.q = queue.Queue()

    def run(self):

        self.engine = pyttsx3.init()
        self.engine.setProperty('volume', g.tts_volume)
        self.engine.setProperty('rate', 160)
        self.engine.setProperty('voice', g.tts_default_vc)
        while True:
            task = self.q.get(block=True)
            task['func'](*task['args'], **task['kwargs'])
            self.q.task_done()

    def new_task(self, func, *args, **kwargs):
        self.q.put({'func': func, 'args': args, 'kwargs': kwargs})

    def remove_links(self, messagesplit):
        return [x for x in messagesplit if not re.match(regex, x)]

    def new_message(self, message: str, messagesplit: list, username: str):
        if message.startswith('tts:') and not checkbanlist(username):
            self.say_message(messagesplit[1:])
        elif g.tts and username != g.BOT and not message.startswith(g.prefix) and not checkbanlist(username):
            self.say_message(messagesplit)

    def say_message(self, messagesplit):
        f_messagesplit = self.remove_links(messagesplit)
        self.engine.say(' '.join(f_messagesplit))
        self.engine.runAndWait()

    def send_set_tts_vc(self, username, messagesplit):
        tts_voices = g.tts_voices
        try:
            for k, v in tts_voices.items():
                if messagesplit[2] == k:
                    self.engine.setProperty('voice', v)
                    send_message(f'tts vc={k}')
                    return
            send_message(f'{username}, [{messagesplit[2]}] not found, available: {", ".join(tts_voices.keys())}')
        except IndexError:
            send_message(f'tts vc={get_tts_vc_key(self.engine.getProperty("voice"))} available: '
                         f'{", ".join(tts_voices.keys())}')

    def change_volume(self, vol: float):
        self.engine.setProperty('volume', vol)
        send_message(f'tts vol={vol}')

    def change_rate(self, rate: int):
        self.engine.setProperty('rate', rate)
        send_message(f'tts rate={rate}')


call_tts = ThreadTTS("calltts")
