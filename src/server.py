import logging
import time
import sys
import re

from flask import Flask, render_template, Blueprint
from PIL import Image, UnidentifiedImageError
from flask_socketio import SocketIO

import src.utils as u
import src.config as g
from .config import cfg
from .classes import Message

module = sys.modules[__name__]
app = Flask(__name__, static_folder='../flask', template_folder='../flask/templates')
sio = SocketIO(app)
player_state = None
player_time = None
connected = False


def socket_connected(func):
    def wrapper(*args, **kwargs):
        if connected:
            return func(*args, **kwargs)
        print('socket not connected')
    return wrapper


@app.route('/')
def hello_world():
    return render_template('index.html')


@sio.on('connect')
def connect_():
    sio.emit('connect_', {'width': cfg['width'], 'height': cfg['height'], 
            'tts_volume': cfg['tts_volume'], 'tts_rate': cfg['tts_rate'], 'tts_vc': cfg['tts_vc']})


@sio.on('connect_')
def client_connect():
    global connected
    connected = True


@sio.on('tts_attr_response')
def tts_attr_response(message):
    u.send_message(f'{message["attr"]}: {message["value"]}')


@sio.on('tts_get_cfg')
def tts_cfg_response(message):
    voice = None
    for k, v in g.tts_voices.items():
        if v == message['tts_vc']:
            voice = k
    u.send_message(f"vol: {message['tts_vol']}, rate: {message['tts_rate']}, vc: {voice}")


@sio.on('player_get_attr')
def player_get_state_response(message):
    for key, value in message.items():
        setattr(module, key, value)


def set_image(folder, filename):
    try:
        img = Image.open(f'flask/images/{folder}{filename}')
    except UnidentifiedImageError:
        return print(f'UnidentifiedImageError - flask/images/{folder}{filename}')
    ri, rs = img.width / img.height, cfg['width'] / cfg['height']
    width, height = u.resizeimg(ri, rs, img.width, img.height, cfg['width'], cfg['height'])
    sio.emit('setimage', {'width': width, 'height': height, 'src': f'images/{folder}{filename}'})


def getattr_sync(attr: str):
    while True:
        value = getattr(module, attr)
        if value is None:
            time.sleep(0.01)
            continue
        setattr(module, attr, None)
        return value


def run():
    sio.run(app, host='127.0.0.1', port=cfg['flaskPort'])


class Player:

    @staticmethod
    @socket_connected
    def get_state():
        sio.emit('player_get_state')
        return getattr_sync('player_state')

    @staticmethod
    @socket_connected
    def get_time():
        sio.emit('player_get_time')
        return getattr_sync('player_time')

    @staticmethod
    def set_time(seconds: int):
        sio.emit('player_set_time', {'seconds': seconds})

    @staticmethod
    def set_volume(sr_volume: float):
        sio.emit('player_set_volume', {'sr_volume': sr_volume})

    @staticmethod
    def set_media(url: str):
        sio.emit('player_set_media', {'url': url})

    @staticmethod
    def play():
        sio.emit('player_play')

    @staticmethod
    def pause():
        sio.emit('player_pause')

    @staticmethod
    def stop():
        sio.emit('player_stop')

    @staticmethod
    def active_state():
        player_state = Player.get_state()
        return any(player_state == x for x in ['State.Playing', 'State.Paused'])


class TextToSpeech:
    
    @staticmethod
    def _say_message(message, voice):
        sio.emit('tts', {'message': message, 'voice': voice})

    @staticmethod
    def set_attr(attr, value, response=True):
        sio.emit('tts_set_attr', {'attr': attr, 'value': value, 'response': response})

    @staticmethod
    def get_attr(attr):
        sio.emit('tts_get_attr', {'attr': attr})

    @staticmethod
    def get_cfg():
        sio.emit('tts_get_cfg')

    @staticmethod
    def say_message(parts: list):
        voices = {}
        voice = 'default'
        pos = 0
        parts = [x for x in parts if not re.match(u.link_re, x)]
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
            tts_voiceuri = g.tts_vc if voice == 'default' else g.tts_voices[voice]
            TextToSpeech._say_message(' '.join(parts), tts_voiceuri)
        TextToSpeech.set_attr('tts_voice', g.tts_vc, response=False)

    @staticmethod
    def get_set_tts_voice(message: Message):
        try:
            for k, v in g.tts_voices.items():
                if message.parts[2] == k:
                    g.tts_vc = v
                    return u.send_message(f'tts vc: {k}')
            u.send_message(f'{message.author}, [{message.parts[2]}] not found, available: {", ".join(g.tts_voices.keys())}')
        except IndexError:
            tts_vc = None
            for k, v in g.tts_voices.items():
                if v == g.tts_vc:
                    tts_vc = k
            u.send_message(f'tts vc: {tts_vc} available: {", ".join(g.tts_voices.keys())}')
