import logging
import threading
import time
import _utils as u
import _globals as g

from flask import Flask, render_template
from flask_socketio import SocketIO
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
        return render_template('index.html', screenwidth=g.screenwidth, screenheight=g.screenheight)

    def run(self):
        self.socketio.run(self.app)

    def set_image(self, folder, filename):
        img = Image.open(f'data/{folder}{filename}')
        ri, rs = img.width / img.height, g.screenwidth / g.screenheight
        width, height = u.resizeimg(ri, rs, img.width, img.height, g.screenwidth, g.screenheight)
        self.socketio.emit('setimage', {'folder': folder, 'filename': filename, 'imgwidth': width, 'imgheight': height})
    
flask_app = FlaskImageApp()