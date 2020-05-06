import sys
import os
from os.path import realpath

if __name__ == '__main__':
    sys.path.append(realpath('../'))
    os.chdir('../')
import re
import time
import threading
import pafy
import modules.globals as g
import modules.commands

from modules.picture import ThreadPic
from modules.utils import timecode_convert, get_current_date, seconds_convert, divide_chunks, send_message
from modules.tts import call_tts
from modules.regex import chat_msg
from modules.pixiv import Pixiv


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

                username = re.search(r"\w+", line).group(0)
                message = chat_msg.sub("", line)
                messagesplit = message.split()

                print(f"{username}: {message}")

                if all(x != username for x in self.notify_check_inprogress):
                    g.utils_queue.new_task(check_chat_notify, username)

                call_tts.new_task(call_tts.new_message, message, messagesplit, username)

                if g.logs:
                    strdate = get_current_date()
                    strdate = str(strdate).replace(':', '.', 3)
                    with open('data/log/' + date + '.txt', 'a+', encoding='utf8') as log:
                        log.write('\n')
                        log.write(f'[{strdate}] {username}: {message}')

                if message.startswith(g.prefix):
                    command = g.commands_dict.get(messagesplit[0][1:], None)
                    if command:
                        g.main_queue.new_task(command, username=username, messagesplit=messagesplit, message=message)


if __name__ == '__main__':
    pafy.set_api_key(g.google_key)
    g.max_duration = timecode_convert(g.max_duration)  # to seconds
    g.sr_cooldown = timecode_convert(g.sr_cooldown)
    g.s.connect((g.HOST, g.PORT))
    g.s.send(bytes("PASS " + g.PASS + "\r\n", "UTF-8"))
    g.s.send(bytes("NICK " + g.BOT + "\r\n", "UTF-8"))
    g.s.send(bytes("JOIN #" + g.CHANNEL + " \r\n", "UTF-8"))

    g.Main = ThreadMain("ThreadMain")
    Drawing = threading.Thread(target=ThreadPic)

    g.Main.start()
    Drawing.start()
    Pixiv.start()
    call_tts.start()
    g.db.start()
