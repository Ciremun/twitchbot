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


@app.route('/')
def hello_world():
    return render_template('index.html')


@sio.on('connect')
def connect_():
    sio.emit('connect_', {'width': cfg['width'], 
                          'height': cfg['height'], 
                          'tts_volume': g.tts_volume, 
                          'tts_rate': g.tts_rate, 
                          'tts_vc': g.tts_vc,
                          'player_volume': g.sr_volume})


@sio.on('connect_')
def client_connect():
    print('socket connect')


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
def player_get_attr(message):
    for key, value in message.items():
        setattr(Player, key, value)


@sio.on('player_end')
def player_end():
    Player.state = 'State.Ended'


@sio.on('player_play')
def player_play():
    Player.state = 'State.Playing'


@sio.on('player_pause')
def player_pause():
    Player.state = 'State.Paused'


@sio.on('player_stop')
def player_stop():
    Player.state = 'State.Stopped'


def set_image(folder, filename):
    try:
        img = Image.open(f'flask/images/{folder}{filename}')
    except UnidentifiedImageError:
        return print(f'UnidentifiedImageError - flask/images/{folder}{filename}')
    ri, rs = img.width / img.height, cfg['width'] / cfg['height']
    width, height = u.resizeimg(ri, rs, img.width, img.height, cfg['width'], cfg['height'])
    sio.emit('setimage', {'width': width, 'height': height, 'src': f'images/{folder}{filename}'})


def run():
    sio.run(app, host='127.0.0.1', port=cfg['flaskPort'])


class Player:

    state = None
    time = None

    @staticmethod
    def get_time():
        sio.emit('player_get_time')
        for _ in range(1500):
            if Player.time is not None:
                player_time = Player.time
                Player.time = None
                return player_time
            time.sleep(0.01)
        return 0

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
        return any(Player.state == x for x in ['State.Playing', 'State.Paused'])


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
