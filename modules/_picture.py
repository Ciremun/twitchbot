import logging
import threading
import _utils as u
import _globals as g

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from PIL import Image, UnidentifiedImageError


class FlaskImageApp(threading.Thread):

    app = Flask(__name__, static_folder='../data', template_folder='../data/special')
    socketio = SocketIO(app)
    log = logging.getLogger('werkzeug')
    log.disabled = True

    def __init__(self):
        threading.Thread.__init__(self) 

    @staticmethod
    @app.route('/')
    def hello_world():
        return render_template('index.html')

    @staticmethod
    @socketio.on('connect')
    def connect_():
        emit('connect_', {'screenwidth': g.screenwidth, 'screenheight': g.screenheight, 
             'tts_volume': g.tts_volume, 'tts_rate': g.tts_rate, 'tts_voice': g.tts_default_vc})

    @staticmethod
    @socketio.on('tts_PropertyResponse')
    def tts_PropertyResponse(data):
        u.send_message(f'{data["attr"]}={data["value"]}')

    @staticmethod
    @socketio.on('tts_getConfig')
    def tts_getConfigResponse(data):
        voice = u.get_tts_vc_key(data['vc'])
        u.send_message(f"{data['vol_rate']}, vc={voice}")

    def run(self):
        self.socketio.run(self.app)

    def set_image(self, folder, filename):
        try:
            img = Image.open(f'data/{folder}{filename}')
        except UnidentifiedImageError:
            return print(f'UnidentifiedImageError - data/{folder}{filename}')  
        ri, rs = img.width / img.height, g.screenwidth / g.screenheight
        width, height = u.resizeimg(ri, rs, img.width, img.height, g.screenwidth, g.screenheight)
        self.socketio.emit('setimage', {'width': width, 'height': height, 'src': f'{folder}{filename}'})

    def say_message(self, message, voice):
        self.socketio.emit('tts', {'message': message, 'voice': voice})

    def tts_setProperty(self, attr, value, response=True):
        self.socketio.emit('tts_setProperty', {'attr': attr, 'value': value, 'response': f'{response}'})

    def tts_getProperty(self, attr):
        self.socketio.emit('tts_getProperty', {'attr': attr})

    def tts_getConfig(self):
        self.socketio.emit('tts_getConfig')

flask_app = FlaskImageApp()
