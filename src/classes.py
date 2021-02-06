import queue
from typing import NamedTuple
from threading import Thread

class Message:

    def __init__(self, message, author):
        self.content = message
        self.parts = message.split()
        self.author = author
    
    def __str__(self):
        return self.content

class Song(NamedTuple):
    audio_link: str
    title: str
    duration: str
    user_duration: int
    link: str
    username: str

class QueueThread(Thread):

    def __init__(self, name):
        Thread.__init__(self, daemon=True)
        self.name = name
        self.q = queue.Queue()
        self.start()

    def run(self):
        while True:
            task = self.q.get()
            task['func'](*task['args'], **task['kwargs'])
            self.q.task_done()

    def new_task(self, func, *args, **kwargs):
        self.q.put({'func': func, 'args': args, 'kwargs': kwargs})
