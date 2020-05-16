import queue
import threading
import pyttsx3
import _globals as g

from _regex import regex, re
from _utils import no_ban, send_message, get_tts_vc_key


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

    def remove_links(self, parts: list):
        return [x for x in parts if not re.match(regex, x)]

    def say_message(self, parts: list):
        parts = self.remove_links(parts)
        self.engine.say(' '.join(parts))
        self.engine.runAndWait()

    def send_set_tts_vc(self, message: object):
        tts_voices = g.tts_voices
        try:
            for k, v in tts_voices.items():
                if message.parts[2] == k:
                    self.engine.setProperty('voice', v)
                    send_message(f'tts vc={k}')
                    return
            send_message(f'{message.author}, [{message.parts[2]}] not found, available: {", ".join(tts_voices.keys())}')
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
