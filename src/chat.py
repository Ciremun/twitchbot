import re
import time
from threading import Thread

import src.config as g
from .utils import timecode_convert, seconds_convert, divide_chunks, send_message, chat_msg_re, check_chat_notify
from .qthreads import main_queue, utils_queue
from .commands import commands, pipe_command
from .classes import Message
from .pixiv import Pixiv
from .log import logger


class ChatThread(Thread):

    def __init__(self, name):
        Thread.__init__(self)
        self.name = name
        g.twitch_socket.connect((g.twitch_host, g.twitch_port))
        g.twitch_socket.send(bytes(f"PASS {g.BotOAuth}\r\n", "UTF-8"))
        g.twitch_socket.send(bytes(f"NICK {g.bot}\r\n", "UTF-8"))
        g.twitch_socket.send(bytes(f"JOIN #{g.channel}\r\n", "UTF-8"))

    def run(self):

        while True:
            line = str(g.twitch_socket.recv(1024))
            if "End of /NAMES list" in line:
                break

        readbuffer = ''

        while True:
            try:
                readbuffer += g.twitch_socket.recv(1024).decode('utf-8')
            except UnicodeDecodeError:
                pass
            temper = readbuffer.split("\r\n")
            readbuffer = temper.pop()
            for line in temper:
                if line.startswith("PING :tmi.twitch.tv"):
                    g.twitch_socket.send(bytes("PONG\r\n", "UTF-8"))
                    continue

                message = Message(chat_msg_re.sub("", line), re.search(r"\w+", line).group(0))
                if g.chat_log:
                    logger.info(f"{message.author}: {message}")

                print(f"{message.author}: {message}")

                utils_queue.new_task(check_chat_notify, message.author)

                if message.content.startswith(g.prefix):
                    if '|' in message.content:
                        main_queue.new_task(pipe_command, message)
                        continue
                    command = commands.get(message.parts[0][len(g.prefix):])
                    if command:
                        main_queue.new_task(command, message)
