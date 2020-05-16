import logging
import threading
import _utils as u
import _globals as g

from flask import Flask, render_template, url_for
from flask_socketio import SocketIO, emit
from PIL import Image


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
        emit('connect_', {'screenwidth': g.screenwidth, 'screenheight': g.screenheight})

    def run(self):
        self.socketio.run(self.app)

    def set_image(self, folder, filename):
        img = Image.open(f'data/{folder}{filename}')
        ri, rs = img.width / img.height, g.screenwidth / g.screenheight
        width, height = u.resizeimg(ri, rs, img.width, img.height, g.screenwidth, g.screenheight)
        self.socketio.emit('setimage', {'width': width, 'height': height, 'src': f'{folder}{filename}'})


flask_app = FlaskImageApp()
