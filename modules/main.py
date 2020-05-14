import sys
import os
from os.path import realpath
if os.getcwd().endswith('modules'):
    sys.path.append(realpath('../'))
    os.chdir('../')
import re
import time
import threading
import pafy
import _globals as g
import _commands

from _picture import flask_app
from _utils import Message, timecode_convert, get_current_date, seconds_convert, divide_chunks, send_message
from _tts import call_tts
from _regex import chat_msg
from _pixiv import Pixiv


class ThreadMain(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.notify_check_inprogress = []
        self.notify_list = []
        self.sr_cooldowns = {}
        self.start_time = time.time()

    def run(self):
        readbuffer = ''
        nowdate = get_current_date()
        date = str(nowdate).replace(':', '.', 3)

        def check_chat_notify(username):
            if any(d['recipient'] == username for d in self.notify_list):
                self.notify_check_inprogress.append(username)
                response = []
                for i in self.notify_list:
                    if i['recipient'] == username:
                        response.append(f'{i["sender"]}: {i["message"]} '
                                        f'[{seconds_convert(time.time() - i["date"], explicit=True)} ago]')
                if response:
                    response_str = f'{username}, {"; ".join(response)}'
                    if len(response_str) > 480:
                        for i in divide_chunks(response_str, 480, response, joinparam='; '):
                            send_message(i)
                            time.sleep(1)
                    else:
                        send_message(response_str)
                self.notify_list = [d for d in self.notify_list if d['recipient'] != username]
                self.notify_check_inprogress.remove(username)

        while True:
            line = str(g.s.recv(1024))
            if "End of /NAMES list" in line:
                break

        while True:
            try:
                readbuffer += g.s.recv(1024).decode('utf-8')
            except UnicodeDecodeError:
                pass
            temper = readbuffer.split("\r\n")
            readbuffer = temper.pop()
            for line in temper:
                if line.startswith("PING :tmi.twitch.tv"):
                    g.s.send(bytes("PONG\r\n", "UTF-8"))
                    continue

                message = Message(chat_msg.sub("", line), re.search(r"\w+", line).group(0))

                print(f"{message.author}: {message}")

                if all(x != message.author for x in self.notify_check_inprogress):
                    g.utils_queue.new_task(check_chat_notify, message.author)

                call_tts.new_task(call_tts.new_message, message)

                if g.logs:
                    strdate = get_current_date()
                    strdate = str(strdate).replace(':', '.', 3)
                    with open('data/log/' + date + '.txt', 'a+', encoding='utf8') as log:
                        log.write('\n')
                        log.write(f'[{strdate}] {message.author}: {message}')

                if message.content.startswith(g.prefix):
                    command = g.commands_dict.get(message.parts[0][1:], None)
                    if command:
                        g.main_queue.new_task(command, message)


if __name__ == '__main__':
    pafy.set_api_key(g.google_key)
    g.max_duration = timecode_convert(g.max_duration)  # to seconds
    g.sr_cooldown = timecode_convert(g.sr_cooldown)
    g.s.connect((g.HOST, g.PORT))
    g.s.send(bytes("PASS " + g.PASS + "\r\n", "UTF-8"))
    g.s.send(bytes("NICK " + g.BOT + "\r\n", "UTF-8"))
    g.s.send(bytes("JOIN #" + g.CHANNEL + " \r\n", "UTF-8"))

    g.Main = ThreadMain("ThreadMain")

    g.Main.start()
    flask_app.start()
    Pixiv.start()
    call_tts.start()
    g.db.start()
