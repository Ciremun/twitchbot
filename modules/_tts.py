import queue
import threading
import pyttsx3
import _globals as g

from _regex import regex, re
from _utils import no_ban, send_message


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
        voices = {}
        voice = 'default'
        pos = 0
        parts = self.remove_links(parts)
        for counter, part in enumerate(parts):
            if part.startswith('vc:') and any(part[3:] == x for x in g.tts_voices.keys()):
                voice = part[3:]
                pos = counter
                continue
            if voices.get(pos) is None:
                voices[pos] = {voice: []}
            voices[pos][voice].append(part)
        for pos, pos_value in voices.items():
            voice, parts = next(iter(pos_value.items()))
            tts_key = g.tts_default_vc if voice == 'default' else g.tts_voices[voice]
            self.engine.setProperty('voice', tts_key)
            self.engine.say(' '.join(parts))
            self.engine.runAndWait()
        self.engine.setProperty('voice', g.tts_default_vc)

    @staticmethod
    def get_tts_vc_key(vc):  # get voice name by registry key
        for k, v in g.tts_voices.items():
            if v == vc:
                return k

    def send_set_tts_vc(self, message: object):
        tts_voices = g.tts_voices
        try:
            for k, v in tts_voices.items():
                if message.parts[2] == k:
                    g.tts_default_vc = v
                    return send_message(f'tts vc={k}')
            send_message(f'{message.author}, [{message.parts[2]}] not found, available: {", ".join(tts_voices.keys())}')
        except IndexError:
            send_message(f'tts vc={self.get_tts_vc_key(self.engine.getProperty("voice"))} available: '
                         f'{", ".join(tts_voices.keys())}')

    def change_volume(self, vol: float):
        self.engine.setProperty('volume', vol)
        send_message(f'tts vol={vol}')

    def change_rate(self, rate: int):
        self.engine.setProperty('rate', rate)
        send_message(f'tts rate={rate}')


call_tts = ThreadTTS("TTS")
