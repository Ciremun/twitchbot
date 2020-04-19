import threading
import pyttsx3
import time
import modules.globals as g

from modules.globals import tts_volume, tts_default_vc, prefix, BOT, tts_voices
from modules.utils import checkbanlist, send_message, get_tts_vc_key
from modules.regex import *


class ThreadTTS(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.temper = []
        self.name = name
        self.engine = None

    def run(self):

        self.engine = pyttsx3.init()
        self.engine.setProperty('volume', tts_volume)
        self.engine.setProperty('rate', 160)
        self.engine.setProperty('voice', tts_default_vc)
        while True:
            time.sleep(0.1)
            for line in self.temper:
                self.temper.pop(0)
                message = line[0]
                username = line[1]
                messagesplit = message.split()

                if message.startswith('tts:') and not checkbanlist(username):
                    self.say_message(messagesplit[1:])

                elif g.tts and username != BOT and not message.startswith(prefix) and not checkbanlist(username):
                    self.say_message(messagesplit)

    def say_message(self, messagesplit):
        for i in messagesplit:
            if re.match(regex, i):
                messagesplit.remove(i)
        self.engine.say(' '.join(messagesplit))
        self.engine.runAndWait()

    def send_set_tts_vc(self, username, messagesplit):
        try:
            for k, v in tts_voices.items():
                if messagesplit[2] == k:
                    self.engine.setProperty('voice', v)
                    send_message(f'vc={k}')
                    return
            send_message(f'{username}, [{messagesplit[2]}] not found, available: {", ".join(tts_voices.keys())}')
        except IndexError:
            send_message(f'{username}, vc={get_tts_vc_key(self.engine.getProperty("voice"))} available: '
                         f'{", ".join(tts_voices.keys())}')


call_tts = ThreadTTS("calltts")
