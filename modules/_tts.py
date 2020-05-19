import queue
import threading
import _globals as g

from _regex import regex, re
from _utils import no_ban, send_message, get_tts_vc_key
from _picture import flask_app


class ThreadTTS(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.q = queue.Queue()

    def run(self):
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
        for pos_value in voices.values():
            voice, parts = next(iter(pos_value.items()))
            tts_voiceuri = g.tts_default_vc if voice == 'default' else g.tts_voices[voice]
            flask_app.say_message(' '.join(parts), tts_voiceuri)
        flask_app.tts_setProperty('tts_voice', g.tts_default_vc, response=False)

    def send_set_tts_vc(self, message: object):
        tts_voices = g.tts_voices
        try:
            for k, v in tts_voices.items():
                if message.parts[2] == k:
                    g.tts_default_vc = v
                    return send_message(f'tts vc={k}')
            send_message(f'{message.author}, [{message.parts[2]}] not found, available: {", ".join(tts_voices.keys())}')
        except IndexError:
            send_message(f'tts vc={get_tts_vc_key(g.tts_default_vc)} available: '
                         f'{", ".join(tts_voices.keys())}')


call_tts = ThreadTTS("TTS")
