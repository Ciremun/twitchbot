from flask import Flask, render_template, request
from flask_socketio import SocketIO
import logging
import threading
import time
import _globals as g

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
        self.socketio.emit('setimage', {'folder': folder, 'filename': filename})
    
flask_app = FlaskImageApp()