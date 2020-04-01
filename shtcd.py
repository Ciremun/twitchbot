import socket  # twitch chat
import random
import re  # check string for link
import requests  # get image from link
import os  # manage files
import datetime  # get date for logs
import time
import threading
import pyglet  # images in window
import pyttsx3  # tts
from os import listdir
from os.path import isfile, join
from pixivapi import Client  # random pixiv arts
from pathlib import Path
from pixivapi import Size
from pixivapi import RankingMode
from pixivapi import BadApiResponse
import asyncio
import sqlite3  # database
import concurrent.futures
import youtube_dl  # !sr downloader
import vlc  # !sr player
from math import floor
import pygame  # meme sound player
import logging

startTime = time.time()
HOST = "irc.twitch.tv"
PORT = 6667
CHANNEL = "ciremun"  # twitch channel to listen
BOT = "shtcd"  # twtich bot username
with open('special/tokens.txt', 'r', encoding='utf8') as tokens:
    PASS = tokens.readline().strip()  # twitch bot token
    TOKEN_AUTH = tokens.readline().strip()  # discord token
    px_token = tokens.readline().strip()  # pixiv token
    channel_id = tokens.readline().strip()  # twitch channel id
    client_id = tokens.readline().strip()  # twitch registered app id
    client_auth = tokens.readline().strip()  # twitch app oauth key with channel_editor scope
s = socket.socket()
s.connect((HOST, PORT))
s.send(bytes("PASS " + PASS + "\r\n", "UTF-8"))
s.send(bytes("NICK " + BOT + "\r\n", "UTF-8"))
s.send(bytes("JOIN #" + CHANNEL + " \r\n", "UTF-8"))
admin = "ciremun"  # bot admin
screenwidth = 390
screenheight = 990  # image window properties
pixiv_artratio = 1.3  # max pixiv art width/height ratio
res = 'special/'
drawfile = 'greenscreen.png'  # init image
prefix = '!'
banned_tags = ['Pokémon', 'how to draw', 'oshinagaki', 'subarashikihokkorinosekai']  # ban pixiv tags
clear_folders = ['sounds/sr/', 'pixiv/', 'images/']  # clear folders on !exit
tts_voices = {'Haruka': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_JA-JP_HARUKA_11.0',
              'Ivy': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\IVONA 2 Voice Ivy22',
              'ru': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\IVONA 2 Voice Tatyana22'}
tts_default_vc = tts_voices['Ivy']
tts = True
tts_volume = 0.07
logs = True
sr = True
player_last_vol = 40  # !sr volume
ytdl_rate = 4000000  # 4Mb/s !sr download rate
max_duration = '10:00'  # !sr max song duration (no limit for mods)
bot_ver = '0.7.8.1'
sad_emote = 'SadLoli'
love_emote = 'mikuHeart'

artid = ''
c = ''
conn = ''
np = ''
np_duration = ''
numba = ''
sr_url = ''
lastlink = ''
last_rand_img = ''
commands_list = ['change', 'save', 'set', 'setrand', 'list', 'search', 'link', 'sr', 'srq', 'srf', 'srf+', 'srf-',
                 'srfp', 'srfl', 'np', 'olist', 'orand', 'ren', 'del', 'cancel', 'help', 'tts:', 'info', 'pipe',
                 'notify']
mod_commands_list = ['ban', 'unban', 'banlist', 'modlist', 'tts', 'srp', 'srs', 'srt', 'srv', 'sql', 'title', 'game']
commands_list = [prefix + x for x in commands_list]
mod_commands_list = [prefix + x for x in mod_commands_list]
lock = threading.Lock()
as_loop = asyncio.get_event_loop()
playlist = []
PlayerInstance = vlc.Instance()
Player = PlayerInstance.media_player_new()
Player.audio_set_volume(player_last_vol)
volume_await = False


def send_message(message):  # bot message to twitch chat
    s.send(bytes("PRIVMSG #" + CHANNEL + " :" + message + "\r\n", "UTF-8"))


def call_draw(folder, selected):
    global res, drawfile
    res = folder
    drawfile = selected


def checkmodlist(username):  # check if user is mod
    if username == admin:
        return True
    result = db.check_if_mod(username)
    if result:
        return True
    return False


def checkbanlist(username):  # check if user is bad
    if username == admin:
        return False
    if checkmodlist(username):
        return False
    result = db.check_if_banned(username)
    if result:
        return True
    return False


def timecode_convert(timecode):
    """Get Seconds from timecode."""
    timecode = timecode.split(':')
    if len(timecode) == 1:
        return int(timecode[0])
    elif len(timecode) == 2:
        m, s = timecode[0], timecode[1]
        return int(m) * 60 + int(s)
    elif len(timecode) == 3:
        h, m, s = timecode[0], timecode[1], timecode[2]
        return int(h) * 3600 + int(m) * 60 + int(s)


max_duration = timecode_convert(max_duration)


def new_timecode(seconds, minutes, hours, duration):
    if duration <= 59:
        return f'{duration}s'
    elif duration <= 3599:
        if seconds <= 9:
            seconds = f'0{seconds}'
        return f'{minutes}:{seconds}'
    else:
        if minutes <= 9:
            minutes = f'0{minutes}'
        if seconds <= 9:
            seconds = f'0{seconds}'
        return f'{hours}:{minutes}:{seconds}'


def new_timecode_explicit(seconds, minutes, hours, duration):
    if duration <= 59:
        return f'{duration}s'
    elif duration <= 3599:
        return f'{minutes}m, {seconds}s'
    else:
        return f'{hours}h, {minutes}m, {seconds}s'


def default_player():
    huis_player.stopmusic()
    Player.play()


def seconds_convert(duration, explicit=False):
    h = floor(duration / 3600)
    m = floor(duration % 3600 / 60)
    s = floor(duration % 3600 % 60)
    if explicit:
        return new_timecode_explicit(s, m, h, duration)
    return new_timecode(s, m, h, duration)


async def download_clip(url, username, user_duration=None, yt_request=True, folder='sounds/sr/', ytsearch=False):
    name = ''.join(random.choices('qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10))
    name = while_is_file(folder, name, '.wav')
    home = folder + name + '.wav'
    ydl_opts = {
        'quiet': True,
        'nocheckcertificate': True,
        'max_downloads': '1',
        'cookiefile': 'special/cookies.txt',
        'ratelimit': ytdl_rate,
        'format': 'bestaudio/best',
        'outtmpl': home,
        'noplaylist': True,
        'continue_dl': True,
        'noprogress': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192', }]
    }
    if ytsearch:
        ydl_opts['playlist_items'] = '1'
        search_query = ''
        for i in url.split():
            search_query += i + '+'
        search_query = search_query[:-1]
        url = f'https://www.youtube.com/results?search_query={search_query}'
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        if ytsearch:
            title = info_dict['entries'][0].get('title', None)
            duration = info_dict['entries'][0].get('duration', 0)
            video_id = info_dict['entries'][0].get('id', None)
            url = f'https://youtu.be/{video_id}'
        else:
            title = info_dict.get('title', None)
            duration = info_dict.get('duration', 0)
        if yt_request and not ytsearch:
            sr_url = info_dict.get('id', None)
            sr_url = f'https://youtu.be/{sr_url}'
        else:
            sr_url = url
        if user_duration is not None:
            user_duration = timecode_convert(user_duration)
            if user_duration > duration:
                send_message(f'{username}, time exceeds duration! [{seconds_convert(duration)}] {sad_emote}')
                return
            if duration - user_duration > max_duration and not checkmodlist(username):
                send_message(f'{username}, {seconds_convert(user_duration)} > '
                             f'max duration[{seconds_convert(max_duration)}] {sad_emote}')
                return
        elif duration > max_duration and not checkmodlist(username):
            send_message(f'{username}, '
                         f'{seconds_convert(duration)} > max duration[{seconds_convert(max_duration)}] {sad_emote}')
            return
        ydl.prepare_filename(info_dict)
        ydl.download([url])
        if folder == 'sounds/favs/':
            if user_duration is None:
                db.add_srfavs(title, username, name + '.wav', 0, sr_url, duration)
                send_message(f'{username}, {title} - {sr_url} - added to favorites {love_emote}')
            else:
                db.add_srfavs(title, username, name + '.wav', user_duration, sr_url, duration)
                send_message(
                    f'{username}, {title} [{seconds_convert(user_duration)}] - {sr_url} - added to favorites {love_emote}')
            return
        duration = seconds_convert(duration)
        playlist.append((home, title, duration, user_duration, sr_url, username))
        if user_duration is not None:
            send_message(f'+ {title} [{seconds_convert(user_duration)}] - {sr_url} - #{len(playlist)}')
        else:
            send_message(f'+ {title} - {sr_url} - #{len(playlist)}')
        sr_queue.call_playmusic()


class AsyncioLoops:

    def __init__(self, loop):
        self.loop = loop
        asyncio.set_event_loop(self.loop)

        async def start():
            while True:
                await asyncio.sleep(0.1)

        def run_it_forever(loop):
            loop.run_forever()

        self.loop.create_task(start())
        thread = threading.Thread(target=run_it_forever, args=(self.loop,))
        thread.start()

    def call_playmusic(self):
        self.loop.create_task(playmusic())

    def call_download_clip(self, url, username, user_duration=None, yt_request=True, folder='sounds/sr/',
                           ytsearch=False):
        self.loop.create_task(download_clip(url, username, user_duration, yt_request, folder, ytsearch))


async def sr_start_playing():
    while not any(str(Player.get_state()) == x for x in ['State.Playing', 'State.Paused']):
        time.sleep(0.01)


async def playmusic():
    global np, np_duration, sr_url
    if pygame.mixer.music.get_busy():
        await asyncio.sleep(5)
        default_player()
        await sr_start_playing()
    if not playlist:
        return
    file = playlist.pop(0)
    Media = PlayerInstance.media_new(file[0])
    Media.get_mrl()
    Player.set_media(Media)
    Player.play()
    np, np_duration, sr_url = file[1], file[2], file[4]
    if file[3] is not None:
        Player.set_time(file[3] * 1000)
    await sr_start_playing()
    while any(str(Player.get_state()) == x for x in ['State.Playing', 'State.Paused']):
        time.sleep(2)


def while_is_file(folder, filename, form):
    path = Path(folder + filename + form)
    while path.is_file():
        filename = ''.join(random.choices('qwertyuiopasdfghjklzxcvbnm' + '1234567890', k=10))
        path = Path(folder + filename + form)
    return filename


class ThreadTTS(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.temper = []
        self.regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # check string for link
        self.name = name

    def run(self):
        global HOST, PORT, CHANNEL, BOT, PASS, admin, tts

        self.engine = pyttsx3.init()
        self.engine.setProperty('volume', tts_volume)
        self.engine.setProperty('rate', 160)
        self.engine.setProperty('voice', tts_default_vc)
        while True:
            time.sleep(0.1)
            for line in self.temper:
                self.temper.pop(0)
                message = line[0]
                username = line[1]
                messagesplit = message.split()
                if message.startswith(prefix):

                    if messagesplit[0][1:] == 'tts:' and not checkbanlist(username):
                        self.say_message(messagesplit[1:])

                elif tts and username != 'shtcd' and not checkbanlist(username):
                    self.say_message(messagesplit)

    def say_message(self, messagesplit):
        nolinkmsg = ''
        for i in messagesplit:
            if re.match(self.regex, i):
                continue
            else:
                nolinkmsg += i + ' '
                continue
        self.engine.say(nolinkmsg)
        self.engine.runAndWait()

    def get_tts_vc_key(self, vc):
        for k, v in tts_voices.items():
            if v == vc:
                return k
        return None

    def send_set_tts_vc(self, username, messagesplit):
        try:
            for k, v in tts_voices.items():
                if messagesplit[2] == k:
                    self.engine.setProperty('voice', v)
                    send_message(f'vc={k}')
                    return
            send_message(f'{username}, [{messagesplit[2]}] not found {sad_emote} , '
                         f'available: {", ".join(tts_voices.keys())}')
        except IndexError:
            send_message(f'{username}, vc={self.get_tts_vc_key(self.engine.getProperty("voice"))} available: '
                         f'{", ".join(tts_voices.keys())}')


class ThreadPixiv(threading.Thread):

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.client = Client()
        self.allranking = []
        self.artpath = Path('pixiv/')

    def download_art(self, obj, size, filename):
        obj.download(directory=self.artpath,
                     size=size, filename=filename
                     )

    def sort_pixiv_arts(self, arts_list, result_list):
        for i in arts_list:
            artratio = i.width / i.height
            if i.page_count > 1 or 'ContentType.MANGA' in str(
                    i.type) or artratio > pixiv_artratio or \
                    any(x in str(i.tags) for x in banned_tags):
                continue
            result_list.append(i)
        return result_list

    def random_setup(self):
        global artid, lastlink, last_rand_img
        try:
            ranking = random.choice(self.allranking)
            fetchmode = random.random()  # ranked or ranked related art 20/80
            if fetchmode > 0.2:
                related_offset = 0
                allrelated = []
                for _ in range(4):
                    related = self.client.fetch_illustration_related(ranking.id,
                                                                     offset=related_offset).get('illustrations')
                    allrelated = self.sort_pixiv_arts(related, allrelated)
                    related_offset += 30
                illustration = random.choice(list(allrelated))
            else:
                illustration = ranking
            print(f'art id: {illustration.id}')
            artid = str(illustration.id)
            lastlink = 'https://www.pixiv.net/en/artworks/{}'.format(artid)
            last_rand_img = artid + '.png'
            art = Path('pixiv/' + artid + '.png')
            if not art.is_file():
                self.download_art(illustration, Size.LARGE, artid)
                if not art.is_file():
                    os.rename('pixiv/' + artid + '.jpg', 'pixiv/' + artid + '.png')
            call_draw('pixiv/', artid + '.png')
        except BadApiResponse as pixiv_exception:  # reconnect
            print(pixiv_exception)
            if 'Status code: 400' in str(pixiv_exception):
                self.run()
            as_loop.create_task(self.random_pixiv_art())

    def save_setup(self, act, namesave, owner, artid, folder='custom/'):
        try:
            artid = str(artid)
            print(f'art id: {artid}')
            namesave = while_is_file(folder, namesave, '.png')
            namesave = while_is_file(folder, namesave, '_p0.png')
            savedart = self.client.fetch_illustration(int(artid))
            self.download_art(savedart, Size.ORIGINAL, namesave)
            if os.path.isdir('pixiv/' + namesave):
                mypath2 = 'pixiv/' + namesave
                onlyfiles = [f for f in listdir(mypath2) if isfile(join(mypath2, f))]
                i = 0
                while i <= len(onlyfiles) - 1:
                    os.rename('pixiv/' + namesave + '/' + str(onlyfiles[i]),
                              folder + namesave + str(onlyfiles[i])[:-4][-3:] + '.png')
                    if act != 'set':
                        db.add_link('https://www.pixiv.net/en/artworks/' + artid, namesave +
                                    onlyfiles[i][:-4][-3:] + '.png')
                        db.add_owner(namesave + onlyfiles[i][:-4][-3:] + '.png', owner)
                    if any(act == x for x in ['set', 'set+save+name']):
                        call_draw(folder, namesave + str(onlyfiles[i])[:-4][-3:] + '.png')
                        time.sleep(1.5)
                    i += 1
                os.rmdir('pixiv/' + namesave)
                if act == 'save':
                    send_message(f'{owner}, {namesave}.png saved {love_emote}')
                return
            art = Path('pixiv/' + namesave + '.png')
            filepath = 'pixiv/' + namesave + '.png'
            if not art.is_file():
                filepath = 'pixiv/' + namesave + '.jpg'
            os.rename(filepath, folder + namesave + '.png')
            if act != 'set':
                db.add_link('https://www.pixiv.net/en/artworks/' + artid, namesave + '.png')
                db.add_owner(namesave + '.png', owner)
            if act != 'save':
                call_draw(folder, namesave + '.png')
            else:
                send_message(f'{owner}, {namesave}.png saved {love_emote}')
        except BadApiResponse as pixiv_exception:  # reconnect
            if 'Status code: 404' in str(pixiv_exception):
                send_message(f'{owner}, {artid} not found {sad_emote}')
                return
            if 'Status code: 400' in str(pixiv_exception):
                self.run()
            as_loop.create_task(self.save_pixiv_art(act, namesave, owner, artid))
        except Exception as e:
            if 'RemoteDisconnected' in str(e):
                as_loop.create_task(self.save_pixiv_art(act, namesave, owner, artid))
                return

    async def random_pixiv_art(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await as_loop.run_in_executor(pool, self.random_setup)

    async def save_pixiv_art(self, act, namesave, owner, artid, folder='custom/'):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await as_loop.run_in_executor(pool, self.save_setup, act, namesave, owner, artid, folder)

    def run(self):
        try:
            self.allranking *= 0
            self.client.authenticate(px_token)
            print('pixiv auth √')
            rank_offset = 30
            ranking1 = self.client.fetch_illustrations_ranking(
                mode=RankingMode.DAY).get('illustrations')  # check 500 arts, filter by tags and ratio
            self.allranking = self.sort_pixiv_arts(ranking1, self.allranking)
            for i in range(16):
                print(f'\rpixiv load={int(i / 16 * 100) + 7}%', end='')
                ranking = self.client.fetch_illustrations_ranking(mode=RankingMode.DAY,
                                                                  offset=rank_offset).get('illustrations')
                self.allranking = self.sort_pixiv_arts(ranking, self.allranking)
                rank_offset += 30
            print()
        except BadApiResponse:
            time.sleep(30)
            self.run()


class ThreadPic:

    def __init__(self):
        global drawfile
        self.window = pyglet.window.Window(screenwidth, screenheight)
        self.bg = pyglet.resource.image('special/greenscreen.png')
        self.image = pyglet.resource.image('special/greenscreen.png')
        self.move = 0
        self.bg.width, self.bg.height = screenwidth, screenheight
        self.sprite = pyglet.sprite.Sprite(img=pyglet.resource.animation('special/sans.gif'))
        self.last = drawfile
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)

        @self.window.event
        def on_draw():
            self.window.clear()
            self.bg.blit(0, 0)
            if self.last.endswith('.gif'):
                self.sprite.draw()
            elif self.last.endswith('.png'):
                self.image.blit(0 + self.move, 0)

        pyglet.clock.schedule_interval(self.update, 1.0 / 60)
        pyglet.app.run()

    def update(self, dt):
        global drawfile
        if drawfile:
            if drawfile.endswith('.gif'):
                self.drawgif(drawfile)
                self.last = drawfile
                drawfile = ''
                if pygame.mixer.music.get_busy():
                    default_player()
            elif drawfile.endswith('.png'):
                if drawfile == 'huis.png':
                    if str(Player.get_state()) != 'State.Paused':
                        Player.pause()
                    huis_player.pmusic()
                    self.drawimg(drawfile)
                    self.last = drawfile
                    drawfile = ''
                else:
                    self.drawimg(drawfile)
                    self.last = drawfile
                    drawfile = ''
                    if pygame.mixer.music.get_busy():
                        default_player()

    def resizeimg(self, ri, rs, image):  # resize to fit window
        if rs > ri:
            resized = image.width * screenheight / image.height, screenheight
            return resized[0], resized[1]
        elif rs < ri:
            resized = screenwidth, image.height * screenwidth / image.width
            return resized[0], resized[1]
        else:
            imagescale = screenwidth / image.width
            image.width *= imagescale
            image.height *= imagescale
            return image.width, image.height

    def drawimg(self, selected):
        try:
            self.image = pyglet.resource.image(f'{res}{selected}')
        except pyglet.resource.ResourceNotFoundException:
            pyglet.resource.reindex()
            self.image = pyglet.resource.image(f'{res}{selected}')
        rs = screenwidth / screenheight
        ri = self.image.width / self.image.height
        self.image.width, self.image.height = self.resizeimg(ri, rs, self.image)
        self.move = self.window.width - self.image.width  # move to the right corner

    def drawgif(self, selected):
        try:
            self.sprite = pyglet.sprite.Sprite(img=pyglet.resource.animation(f'{res}{selected}'))
        except pyglet.resource.ResourceNotFoundException:
            pyglet.resource.reindex()
            try:
                self.sprite = pyglet.sprite.Sprite(img=pyglet.resource.animation(f'{res}{selected}'))
            except pyglet.image.ImageDecodeException:
                pass
        except pyglet.image.ImageDecodeException:
            pass
        sprscale = 1
        screenr = screenwidth / screenheight
        spriter = self.sprite.width / self.sprite.height
        if screenr > spriter:
            sprscale = screenheight / self.sprite.height
        elif screenr < spriter or screenr == spriter:
            sprscale = screenwidth / self.sprite.width
        self.sprite.scale = sprscale
        self.move = self.window.width - self.sprite.width
        self.sprite.x += self.move


class ThreadPlayer(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        self.initMixer()
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.music.load('sounds/huis.mp3')
        pygame.mixer.music.set_volume(0.02)

    def pmusic(self):
        pygame.mixer.music.play()

    def stopmusic(self):
        pygame.mixer.music.stop()

    def getmixerargs(self):
        pygame.mixer.init()
        freq, size, chan = pygame.mixer.get_init()
        return freq, size, chan

    def initMixer(self):
        BUFFER = 3072  # audio buffer size, number of samples since pygame 1.8.
        FREQ, SIZE, CHAN = self.getmixerargs()
        pygame.mixer.init(FREQ, SIZE, CHAN, BUFFER)


class ThreadMain(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global HOST, PORT, CHANNEL, BOT, PASS, admin, artid, lastlink, last_rand_img, logs, playlist, \
            player_last_vol, sr, numba, sr_url, volume_await

        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # check string for link

        timecode_re = re.compile(r'^(?:(?:(\d+):)?(\d+):)?(\d+)$')

        youtube_link_re = re.compile(
            r'http(?:s?)://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?')

        video_id_re = re.compile(r'^([/]?watch\?v)?=([\w-]{11})$')

        soundcloud_re = re.compile(r'^(https://)?(www.)?(m\.)?soundcloud\.com/([\w\-.]+/[\w\-.]+)$')

        soundcloud_id_re = re.compile(r'^/?[\w\-.]+/[\w\-.]+$')

        pixiv_re = re.compile(r'^(https://)?(www.)?pixiv\.net/(en)?(artworks)?/(\d+)?(artworks)?(/(\d+)?)?$')

        pixiv_src_re = re.compile(r'^(https://)?(www.)?i\.pximg\.net/[\w\-]+/\w+/\d+/\d+/\d+/\d+/\d+/\d+/(('
                                  r'\d+)_p\d+\w+\.\w+)?((\d+)_p\d+\.\w+)?$')

        notify_check_inprogress = []
        notify_list = []

        async def rename_command(username, messagesplit):  # rename function for image owners
            try:
                imagename = messagesplit[1].lower()
                newimagename = fixname(messagesplit[2].lower())
                moderator = checkmodlist(username)
                if not checkOwner(username, imagename) and not moderator:
                    onlyfiles = [f for f in listdir('custom/') if isfile(join('custom/', f))]
                    words = onlyfiles
                    if imagename not in words:
                        send_message(f'{username}, file not found {sad_emote}')
                        return
                    for element in words:
                        if element == imagename:
                            send_message(f'{username}, access denied {sad_emote}')
                else:
                    my_file = Path("custom/" + newimagename)
                    if my_file.is_file():
                        send_message("{}, {} already exists".format(username, newimagename))
                        return
                    if imagename[-4:] != newimagename[-4:] and not moderator:
                        send_message(f"{username}, sowwy, format change isn't allowed {sad_emote}")
                        return
                    try:
                        os.rename('custom/' + imagename, 'custom/' + newimagename)
                        db.update_link_filename(imagename, newimagename)
                        db.update_owner_filename(imagename, newimagename)
                        send_message('{}, {} --> {}'.format(username, imagename, newimagename))
                    except:
                        send_message(f'{username}, file not found {sad_emote}')
            except IndexError:
                send_message(f'{username}, {prefix}ren <filename> <new filename>')

        def send_list(list_str, list_arr, list_page_pos, list_type):
            if 490 >= len(list_str) > 0:
                send_message("{}".format(list_str))
                return
            if len(list_str) == 0:
                if list_type == "search":
                    send_message(f'{username}, no results {sad_emote}')
                    return
                else:
                    send_message(f'{username}, list is empty {sad_emote}')
                    return
            try:
                pagenum = int(messagesplit[list_page_pos])
                if pagenum <= 0 or pagenum > len(list_arr):
                    send_message(f'{username}, page not found {sad_emote}')
                    return
                send_message("{} {}/{}".format(list_arr[pagenum - 1], pagenum, len(list_arr)))
            except (IndexError, ValueError):
                if len(list_str) > 490 or len(list_str) <= 490:
                    send_message('{} 1/{}'.format(list_arr[0], len(list_arr)))

        def owner_list(user):  # list of images for image owners
            result = db.check_ownerlist(user)
            result = [item[0] for item in result]
            result = " ".join(result)
            allpages = divide_chunks(result, 480)
            send_list(result, allpages, 1, "list")

        def divide_chunks(string, length, lst=None, joinparam=' '):  # divide string into chunks
            chunk = []
            all_chunks = []
            if lst is None:
                lst = string.split()
            message_length = 0
            i = 0
            for element in lst:
                message_length += len(element) + 1
                if message_length + len(lst[i]) + 1 <= length:
                    chunk.append(element)
                else:
                    chunk = f'{joinparam}'.join(chunk) + f'{joinparam}' + element
                    all_chunks.append(chunk)
                    chunk = []
                    message_length = 0
                i += 1
            chunk = f'{joinparam}'.join(chunk)
            all_chunks.append(chunk)
            all_chunks = list(filter(None, all_chunks))
            return all_chunks

        def checklist(mode):  # check ban/mod list
            if mode == "modlist":
                result = db.check_moderators()
            else:
                result = db.check_banned()
            result = [item[0] for item in result]
            result = " ".join(result)
            allpages = divide_chunks(result, 480)
            send_list(result, allpages, 1, "list")

        def fixname(name):
            if name.startswith('.'):
                name = '•' + name[1:]
            name = name.replace('\\', '❤')
            name = name.replace('/', '❤')
            name = name.replace(':', ';')
            name = name.replace('*', '★')
            name = name.replace('?', '❓')
            name = name.replace('"', "'")
            name = name.replace('<', '«')
            name = name.replace('>', '»')
            name = name.replace('|', '│')
            return name

        def checkIfNoLink(act):
            mypath = 'custom/'
            onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
            result = db.get_links_filenames()
            lst_result = [i[0] for i in result]
            words = [x if set(x.split()).intersection(lst_result) else x + '*' for x in onlyfiles]
            if act == '!search':
                return words
            linkwords = [x for x in words if '*' not in x]
            return words, linkwords

        def getCurDate():
            nowdate = datetime.datetime.now()
            return nowdate

        nowdate = getCurDate()
        date = str(nowdate).replace(':', '.', 3)

        def checkOwner(username, imagename):  # check if user owns image
            result = db.check_owner(imagename, username)
            if result:
                return True
            return False

        def updatelastlink(selected):
            global lastlink
            result = db.get_link(selected)
            result = " ".join([item[0] for item in result])
            if result:
                lastlink = result
                return
            lastlink = f'no link saved {sad_emote}'
            return

        async def sr_favs_del(username, messagesplit, songs):
            response = []
            remove_song = []
            target_not_found = []
            song_removed_response = []
            for i in range(1, len(messagesplit)):
                await asyncio.sleep(0)
                try:
                    index = int(messagesplit[i]) - 1
                except ValueError:
                    target_not_found.append(messagesplit[i])
                    continue
                if not 0 <= index <= len(songs) - 1:
                    target_not_found.append(messagesplit[i])
                    continue
                user_duration = songs[index].get("user_duration")
                if user_duration is None:
                    user_duration = 0
                    song_removed_response.append(songs[index].get("title"))
                else:
                    song_removed_response.append(f'{songs[index].get("title")} '
                                                 f'[{seconds_convert(songs[index].get("user_duration"))}]')
                remove_song.append((songs[index].get("title"), username,
                                    songs[index].get("filename"),
                                    user_duration,
                                    songs[index].get("link"), songs[index].get("duration")))
                try:
                    os.remove('sounds/favs/' + songs[index].get("filename"))
                except:
                    pass
            db.remove_srfavs(remove_song)
            if song_removed_response:
                response.append(f'Favorites removed: {", ".join(song_removed_response)} {love_emote}')
            if target_not_found:
                response.append(f'Not found: {", ".join(target_not_found)} {sad_emote}')
            if response:
                response_str = ' '.join(response)
                if len(response_str) > 470:
                    response *= 0
                    if song_removed_response:
                        response.append(f'Favorites removed: {len(song_removed_response)} {love_emote}')
                    if target_not_found:
                        response.append(f'Not found: {len(target_not_found)} {sad_emote}')
                    send_message(f'{username}, {" ".join(response)}')
                else:
                    send_message(response_str)

        async def del_command(username, messagesplit):
            response_not_found, response_denied, response_deleted, remove_links, remove_owners = [], [], [], [], []
            file_deleted = False
            moderator = checkmodlist(username)
            for i in messagesplit[1:]:
                imagename = i.lower()
                if not checkOwner(username, imagename) and not moderator:
                    words = [f for f in listdir('custom/') if isfile(join('custom/', f))]
                    if not set(imagename.split()).intersection(words):
                        response_not_found.append(imagename)
                        continue
                    else:
                        response_denied.append(imagename)
                else:
                    try:
                        os.remove('custom/' + imagename)
                        remove_links.append((imagename,))
                        remove_owners.append((imagename,))
                        response_deleted.append(imagename)
                        file_deleted = True
                    except:
                        response_not_found.append(i.lower())
            response = []
            if file_deleted:
                db.remove_link(remove_links)
                db.remove_owner(remove_owners)
                response.append(f"Deleted: {', '.join(response_deleted)} {love_emote}")
            if response_denied:
                response.append(f"Access denied: {', '.join(response_denied)} {sad_emote}")
            if response_not_found:
                response.append(f"Not found: {', '.join(response_not_found)} {sad_emote}")
            response = f"{username}, {'; '.join(response)}"
            if len(response) <= 490:
                send_message(response)
            else:
                response = divide_chunks(response, 480)
                for i in response:
                    send_message(i)

        async def link_command(username, messagesplit):
            if len(messagesplit) > 1:
                links_filenames = [{'link': j[0], 'filename': j[1]} for j in db.get_links_and_filenames()]
                target_not_found = []
                response = []
                for i in messagesplit:
                    link = None
                    for lnk in links_filenames:
                        if i == lnk.get('filename'):
                            link = lnk.get('link')
                            break
                    if link is None:
                        target_not_found.append(i)
                    else:
                        response.append(f'{link} - {i}')
                if target_not_found:
                    response.append(f'Not found: {", ".join(target_not_found)} {sad_emote}')
                if response:
                    response_str = ', '.join(response)
                    if len(response_str) > 480:
                        response_arr = divide_chunks(response_str, 470, response, joinparam=', ')
                        for msg in response_arr:
                            send_message(msg)
                    else:
                        send_message(', '.join(response))
            else:
                link = db.get_link(messagesplit[0])
                if link:
                    send_message(f'{" , ".join([i[0] for i in link])} - {messagesplit[0]}')
                else:
                    send_message(f"{username}, {messagesplit[0]} not found {sad_emote}")

        async def delete_ban_mod(response, boolean, str1, str2, username):
            if response:
                response = ', '.join(response)
                if boolean:
                    response = f'{username}, {str1}, except: {response} - {str2}'
                else:
                    response = f'{username}, {response} - {str2}'
                if len(response) <= 490:
                    send_message(response)
                else:
                    response = divide_chunks(response, 400)
                    for i in response:
                        send_message(i)
            else:
                send_message('{}, {}'.format(username, str1))

        async def ban_mod_commands(username, messagesplit, str1, str2, check_func, db_call, check_func_result):
            response = []
            users = []
            boolean = False
            for i in messagesplit[1:]:
                user = i.lower()
                if check_func(user) == check_func_result:
                    response.append(user)
                else:
                    users.append((user,))
                    boolean = True
            db_call(users)
            await delete_ban_mod(response, boolean, str1, str2, username)

        def sr_get_list(username):
            if not playlist:
                send_message(f'{username}, playlist is empty {sad_emote}')
                return
            sr_list = [f'{x[1]} [{seconds_convert(x[3])}] #{i}' if x[3] is not None else f'{x[1]} #{i}' for i, x in
                       enumerate(playlist, start=1)]
            sr_str = ", ".join(sr_list)
            sr_list = divide_chunks(sr_str, 470, sr_list, joinparam=', ')
            send_list(sr_str, sr_list, 1, "list")

        async def volume_await_change(player_last_vol):
            global volume_await
            volume_await = True
            while Player.audio_get_volume() != player_last_vol:
                await asyncio.sleep(0.01)
                Player.audio_set_volume(player_last_vol)
            volume_await = False

        async def change_stream_settings(username, messagesplit, setting):
            channel_info = requests.get(f"https://api.twitch.tv/kraken/channels/{channel_id}",
                                        headers={"Client-ID": client_id,
                                                 "Accept": "application/vnd.twitchtv.v5+json"}).json()
            if setting == 'title':
                set_title = " ".join(messagesplit[1:])
                if not set_title:
                    send_message(f'Title: {channel_info["status"]}')
                else:
                    await change_status_game(set_title, channel_info["game"], username)
            elif setting == 'game':
                set_game = " ".join(messagesplit[1:])
                if not set_game:
                    send_message(f'Game: {channel_info["game"]}')
                else:
                    await change_status_game(channel_info["status"], set_game, username)

        async def change_status_game(channel_status, channel_game, username):
            requests.put(f"https://api.twitch.tv/kraken/channels/{channel_id}",
                         headers={"Client-ID": client_id,
                                  "Accept": "application/vnd.twitchtv.v5+json",
                                  "Authorization": client_auth},
                         data={"channel[status]": channel_status,
                               "channel[game]": channel_game})
            send_message(f'{username}, done {love_emote}')

        def np_response(mode):
            current_time_ms = Player.get_time()
            current_time = floor(current_time_ms / 1000)
            current_time = seconds_convert(current_time)
            send_message(f'{mode}: {np} - {sr_url} - {current_time}/{np_duration}')

        def try_timecode(url, messagesplit, username, timecode_pos=None, yt_request=True, folder='sounds/sr/',
                         ytsearch=False):
            try:
                if timecode_pos is None:
                    raise IndexError
                timecode = messagesplit[timecode_pos]
                if re.match(timecode_re, timecode):
                    sr_download_queue.call_download_clip(url, username, user_duration=timecode, yt_request=yt_request,
                                                         folder=folder, ytsearch=ytsearch)
                else:
                    send_message(f'{username}, timecode error {sad_emote}')
            except IndexError:
                sr_download_queue.call_download_clip(url, username, yt_request=yt_request, folder=folder,
                                                     ytsearch=ytsearch)

        def clear_folder(path):
            filelist = [f for f in os.listdir(path) if isfile(join(path, f))]
            for f in filelist:
                try:
                    os.remove(os.path.join(path, f))
                except:
                    pass

        def change_pixiv(pattern, group, group2, url, messagesplit, username):
            global numba
            try:
                imagename = fixname(messagesplit[2].lower())
                try:
                    pxid = int(pattern.sub(group, url))
                except ValueError:
                    pxid = int(pattern.sub(group2, url))
                asyncio.run_coroutine_threadsafe(Pixiv.save_pixiv_art('set+save+name', imagename,
                                                                      username, pxid), as_loop)
            except IndexError:
                try:
                    pxid = int(pattern.sub(group, url))
                except ValueError:
                    pxid = int(pattern.sub(group2, url))
                asyncio.run_coroutine_threadsafe(Pixiv.save_pixiv_art('set', numba,
                                                                      username, pxid, 'images/'), as_loop)
                db.update_imgcount(int(numba) + 1)

        def save_pixiv(pattern, group, group2, url, messagesplit, username):
            try:
                imagename = fixname(messagesplit[2].lower())
                try:
                    pxid = int(pattern.sub(group, url))
                except ValueError:
                    pxid = int(pattern.sub(group2, url))
                asyncio.run_coroutine_threadsafe(Pixiv.save_pixiv_art('save', imagename,
                                                                      username, pxid), as_loop)
            except IndexError:
                pass

        def sr_download(messagesplit, username, folder='sounds/sr/', link_pos=1, timecode_pos=None, ytsearch=False):
            if re.match(youtube_link_re, messagesplit[link_pos]):
                try_timecode(messagesplit[link_pos], messagesplit, username, timecode_pos=timecode_pos, folder=folder,
                             ytsearch=ytsearch)
            elif re.match(video_id_re, messagesplit[link_pos]):
                video_id = video_id_re.sub(r'\2', messagesplit[link_pos])
                url = f'https://www.youtube.com/watch?v={video_id}'
                try_timecode(url, messagesplit, username, timecode_pos=timecode_pos, folder=folder, ytsearch=ytsearch)
            elif re.match(soundcloud_re, messagesplit[link_pos]):
                try_timecode(messagesplit[link_pos], messagesplit, username, timecode_pos=timecode_pos,
                             yt_request=False, folder=folder, ytsearch=ytsearch)
            elif re.match(soundcloud_id_re, messagesplit[1]):
                soundcloud_id = soundcloud_re.sub(r'\4', messagesplit[link_pos])
                url = f'https://soundcloud.com/{soundcloud_id}'
                try_timecode(url, messagesplit, username, timecode_pos=timecode_pos, yt_request=False,
                             folder=folder, ytsearch=ytsearch)
            else:
                return False
            return True

        def get_srfavs_dictlist(username):
            result = db.check_srfavs_list(username)
            if not result:
                return False
            songs = []
            for song in result:
                if song[2] == 0:
                    user_duration = None
                else:
                    user_duration = song[2]
                song_dict = {
                    "title": song[0],
                    "filename": song[1],
                    "user_duration": user_duration,
                    "link": song[3],
                    "duration": song[4]
                }
                songs.append(song_dict)
            return songs

        def set_random_pic(lst, response):
            global last_rand_img
            if not lst:
                send_message(response)
                return
            selected = random.choice(lst)
            updatelastlink(selected)
            last_rand_img = selected
            call_draw('custom/', selected)

        def change_save_command(username, messagesplit, do_draw=False, do_save=False, do_save_response=False):
            url = messagesplit[1]
            if re.match(pixiv_re, url):
                if do_draw:
                    change_pixiv(pixiv_re, r'\5', r'\8', url, messagesplit, username)
                else:
                    save_pixiv(pixiv_re, r'\5', r'\8', url, messagesplit, username)
            elif re.match(pixiv_src_re, url):
                if do_draw:
                    change_pixiv(pixiv_src_re, r'\4', r'\6', url, messagesplit, username)
                else:
                    save_pixiv(pixiv_src_re, r'\4', r'\6', url, messagesplit, username)
            elif re.match(regex, url):
                content_type = requests.head(url, allow_redirects=True).headers.get('content-type').split(
                    '/')
                if content_type[0] != 'image':
                    send_message(f'{username}, unknown format {sad_emote}')
                    return
                if content_type[1] != 'gif':
                    file_format = '.png'
                else:
                    file_format = f'.{content_type[1]}'
                r = requests.get(url)
                try:
                    folder = 'custom/'
                    imagename = while_is_file(folder, fixname(messagesplit[2].lower()),
                                              f'{file_format}')
                    filepath = Path(f'{folder}{imagename}{file_format}')
                    do_save = True
                except IndexError:
                    folder = 'images/'
                    imagename = numba
                    db.update_imgcount(int(numba) + 1)
                    filepath = Path(f'{folder}{imagename}{file_format}')
                with open(filepath, 'wb') as download:
                    download.write(r.content)
                if filepath.is_file():
                    if do_draw:
                        call_draw(folder, f'{imagename}{file_format}')
                    if do_save:
                        db.add_link(url, f'{imagename}{file_format}')
                        db.add_owner(f'{imagename}{file_format}', username)
                    if do_save_response:
                        send_message(f'{username}, {imagename}{file_format} saved {love_emote}')
                else:
                    send_message(f'{username}, download error {sad_emote}')
            else:
                send_message(f"{username}, no link {sad_emote}")

        def die_command(username=None, messagesplit=None, message=None):
            if message[1:] == "die" and checkmodlist(username):
                call_draw('special/', 'greenscreen.png')

        def exit_command(username=None, messagesplit=None, message=None):
            if message[1:] == "exit" and username == admin:
                for folder in clear_folders:
                    clear_folder(folder)
                result = db.get_srfavs_filenames()
                result = [item[0] for item in result]
                favorites = [f for f in os.listdir('sounds/favs/') if isfile(join('sounds/favs/', f))]
                for f in favorites:
                    try:
                        if not set(f.split()).intersection(result):
                            os.remove(os.path.join('sounds/favs/', f))
                    except:
                        pass
                os._exit(0)

        def log_command(username=None, messagesplit=None, message=None):
            global logs
            if messagesplit[0][1:] == "log" and username == admin:
                if logs:
                    logs = False
                    send_message('logs off')
                else:
                    logs = True
                    send_message('logs on')

        def np_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "np" and not checkbanlist(username):
                if all(str(Player.get_state()) != x for x in ['State.Playing', 'State.Paused']):
                    send_message(f'{username}, nothing is playing {sad_emote}')
                elif str(Player.get_state()) == 'State.Paused':
                    np_response('Paused')
                else:
                    np_response('Now playing')

        def srv_command(username=None, messagesplit=None, message=None):
            global player_last_vol
            if sr and messagesplit[0][1:] == "srv" and checkmodlist(username):
                try:
                    value = int(messagesplit[1])
                    if 0 <= value <= 100:
                        player_last_vol = value
                        if any(str(Player.get_state()) == x
                               for x in ['State.Playing', 'State.Paused']):
                            Player.audio_set_volume(player_last_vol)
                        elif not volume_await:
                            as_loop.create_task(volume_await_change(player_last_vol))
                    else:
                        send_message(f'{username}, vol 0-100')
                except IndexError:
                    send_message(f'{prefix}sr vol={player_last_vol}')
                except ValueError:
                    send_message(f'{username}, vol 0-100')

        def srq_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srq" and not checkbanlist(username):
                sr_get_list(username)

        def srs_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srs" and checkmodlist(username):
                if all(str(Player.get_state()) != x for x in ['State.Playing', 'State.Paused']):
                    send_message(f'{username}, nothing is playing {sad_emote}')
                    return
                try:
                    if messagesplit[1]:
                        if not playlist:
                            send_message(f'{username}, playlist is empty {sad_emote}')
                            return
                        skipped_response = []
                        skip_songs = []
                        user_response = []
                        target_not_found = []
                        for i in range(1, len(messagesplit)):
                            try:
                                target = int(messagesplit[i])
                                if not 0 < target <= len(playlist):
                                    target_not_found.append(f'{target}')
                                else:
                                    if playlist[target - 1][3] is not None:
                                        skipped_response.append(
                                            f'{playlist[target - 1][1]} '
                                            f'[{seconds_convert(playlist[target - 1][3])}]'
                                        )
                                    else:
                                        skipped_response.append(f'{playlist[target - 1][1]}')
                                    skip_songs.append(playlist[target - 1])
                            except ValueError:
                                target = messagesplit[i]
                                title_skipped = False
                                for j in playlist:
                                    if any(target in x for x in [j[1], j[1].lower()]):
                                        skip_songs.append(j)
                                        if j[3] is not None:
                                            skipped_response.append(
                                                f'{j[1]} '
                                                f'[{seconds_convert(j[3])}]'
                                            )
                                        else:
                                            skipped_response.append(f'{j[1]}')
                                        title_skipped = True
                                if not title_skipped:
                                    target_not_found.append(target)
                        if skip_songs:
                            for i in skip_songs:
                                try:
                                    playlist.remove(i)
                                except ValueError:
                                    skipped_response = list(set(skipped_response))
                        if skipped_response:
                            user_response.append(f'Skip: {", ".join(skipped_response)}')
                        if target_not_found:
                            user_response.append(f'Not found: {", ".join(target_not_found)}')
                        if user_response:
                            user_response_str = " ".join(user_response)
                            if len(user_response_str) > 470:
                                user_response *= 0
                                if skipped_response:
                                    user_response.append(f'Skip: {len(skipped_response)}')
                                if target_not_found:
                                    user_response.append(f'Not found: {len(target_not_found)}')
                                send_message(f'{username}, {" ".join(user_response)}')
                            else:
                                send_message(user_response_str)
                except IndexError:
                    Player.stop()

        def src_command(username=None, messagesplit=None, message=None):
            global playlist
            if sr and messagesplit[0][1:] == "src" and checkmodlist(username):
                if not playlist:
                    send_message(f'{username} playlist is empty {sad_emote}')
                    return
                playlist *= 0
                send_message(f'queue wiped')

        def srp_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srp" and checkmodlist(username):
                if str(Player.get_state()) == 'State.Playing':
                    Player.pause()
                elif str(Player.get_state()) == 'State.Paused':
                    Player.play()
                else:
                    send_message(f'{username}, nothing is playing {sad_emote}')

        def srt_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srt" and checkmodlist(username):
                if all(str(Player.get_state()) != x for x in ['State.Playing', 'State.Paused']):
                    send_message(f'{username}, nothing is playing {sad_emote}')
                    return
                try:
                    timecode = messagesplit[1]
                    if re.match(timecode_re, timecode):
                        seconds = timecode_convert(timecode)
                        if seconds > timecode_convert(np_duration):
                            send_message(f'{username}, time exceeds duration! [{np_duration}]')
                        else:
                            Player.set_time(seconds * 1000)
                    else:
                        send_message(f'{username}, timecode error {sad_emote}')
                except IndexError:
                    send_message(f'{username}, no timecode {sad_emote}')

        def srf_plus_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srf+" and not checkbanlist(username):
                try:
                    url_or_timecode = messagesplit[1]
                    if re.match(timecode_re, url_or_timecode):
                        messagesplit.append(url_or_timecode)
                        messagesplit[1] = sr_url
                        sr_download(messagesplit, username, 'sounds/favs/', timecode_pos=2)
                        return
                    match = sr_download(messagesplit, username, 'sounds/favs/',
                                        link_pos=1, timecode_pos=2)
                    if not match:
                        timecode_pos = None
                        if re.match(timecode_re, messagesplit[-1]):
                            timecode_pos = len(messagesplit) - 1
                            messagesplit[1] = ' '.join(messagesplit[1:-1])
                        else:
                            messagesplit[1] = ' '.join(messagesplit[1:])
                        try_timecode(messagesplit[1], messagesplit, username,
                                     timecode_pos=timecode_pos,
                                     folder='sounds/favs/', ytsearch=True)
                except IndexError:
                    if all(str(Player.get_state()) != x for x in
                           ['State.Playing', 'State.Paused']):
                        send_message(f'{username}, nothing is playing {sad_emote}')
                    else:
                        messagesplit.append(sr_url)
                        sr_download(messagesplit, username, 'sounds/favs/', timecode_pos=3)

        def srf_minus_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srf-" and not checkbanlist(username):
                try:
                    if messagesplit[1]:
                        songs = get_srfavs_dictlist(username)
                        if not songs:
                            send_message(f'{username}, no favorite songs found {sad_emote}')
                            return
                        as_loop.create_task(sr_favs_del(username, messagesplit, songs))
                except IndexError:
                    send_message(f'{username}, {prefix}srf- <index1> <index2>..')

        def srfp_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srfp" and not checkbanlist(username):
                try:
                    if messagesplit[1]:
                        songs = get_srfavs_dictlist(username)
                        if not songs:
                            send_message(f'{username}, no favorite songs found {sad_emote}')
                            return
                        response = []
                        target_not_found = []
                        response_added = []
                        for i in range(1, len(messagesplit)):
                            try:
                                index = int(messagesplit[i])
                                if not 0 < index <= len(songs):
                                    target_not_found.append(messagesplit[i])
                                    continue
                                playlist.append(('sounds/favs/' + songs[index - 1].get("filename"),
                                                 songs[index - 1].get("title"),
                                                 seconds_convert(songs[index - 1].get("duration")),
                                                 songs[index - 1].get("user_duration"),
                                                 songs[index - 1].get("link"), username))
                                sr_queue.call_playmusic()
                                if songs[index - 1].get("user_duration") is not None:
                                    response_added.append(f'{songs[index - 1].get("title")} '
                                                          f'[{seconds_convert(songs[index - 1].get("user_duration"))}]'
                                                          f' - {songs[index - 1].get("link")} - #{len(playlist)}')
                                else:
                                    response_added.append(f'{songs[index - 1].get("title")} - '
                                                          f'{songs[index - 1].get("link")} - #{len(playlist)}')
                            except ValueError:
                                title = messagesplit[i]
                                title_found = False
                                for j in songs:
                                    if any(title in x for x in [j.get('title'), j.get('title').lower()]):
                                        playlist.append(('sounds/favs/' + j.get("filename"),
                                                         j.get("title"),
                                                         seconds_convert(j.get("duration")),
                                                         j.get("user_duration"), j.get("link"), username))
                                        title_found = True
                                        sr_queue.call_playmusic()
                                        if j.get("user_duration") is not None:
                                            response_added.append(f'{j.get("title")} '
                                                                  f'[{seconds_convert(j.get("user_duration"))}]'
                                                                  f' - '
                                                                  f'{j.get("link")} - #{len(playlist)}')
                                        else:
                                            response_added.append(f'{j.get("title")} - {j.get("link")} - '
                                                                  f'#{len(playlist)}')
                                if not title_found:
                                    target_not_found.append(title)
                        if response_added:
                            response.append(f"+ {'; '.join(response_added)}")
                        if target_not_found:
                            response.append(f"Not found: {', '.join(target_not_found)}")
                        if response:
                            response_str = ' '.join(response)
                            if len(response_str) > 470:
                                response *= 0
                                if response_added:
                                    response.append(f"Added: {len(response_added)}")
                                if target_not_found:
                                    response.append(f"Not found: {len(target_not_found)}")
                                send_message(' '.join(response))
                            else:
                                send_message(response_str)
                except IndexError:
                    send_message(f'{username}, {prefix}srfp <word/index>')

        def srfl_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srfl" and not checkbanlist(username):
                try:
                    if messagesplit[1]:
                        songs = get_srfavs_dictlist(username)
                        if not songs:
                            send_message(f'{username}, no favorite songs found {sad_emote}')
                            return
                        target_not_found = []
                        response = []
                        for i in range(1, len(messagesplit)):
                            try:
                                index = int(messagesplit[i])
                                if not 0 < index <= len(songs):
                                    send_message(f'{username}, invalid index [{index}] {sad_emote}')
                                    continue
                                response.append(f'{username}, {songs[index - 1].get("title")} - '
                                                f'{songs[index - 1].get("link")}')
                            except ValueError:
                                title = messagesplit[i]
                                title_found = False
                                for j in songs:
                                    if any(title in x for x in [j.get('title'), j.get('title').lower()]):
                                        response.append(f'{j.get("title")} - {j.get("link")}')
                                        title_found = True
                                if not title_found:
                                    target_not_found.append(title)
                        if target_not_found:
                            response.append(f'Not found: {", ".join(target_not_found)} {sad_emote}')
                        if response:
                            response_str = ' ; '.join(response)
                            if len(response_str) > 470:
                                response_arr = divide_chunks(response_str, 470, response, joinparam=' ; ')
                                for msg in response_arr:
                                    send_message(msg)
                            else:
                                send_message(' ; '.join(response))
                except IndexError:
                    send_message(f'{username}, {prefix}srfl <word/index>')

        def srf_command(username=None, messagesplit=None, message=None):
            if sr and messagesplit[0][1:] == "srf" and not checkbanlist(username):
                songs = get_srfavs_dictlist(username)
                if not songs:
                    send_message(f'{username}, no favorite songs found {sad_emote}')
                    return
                songs_arr = [f'{songs[i - 1].get("title")} '
                             f'[{seconds_convert(songs[i - 1].get("user_duration"))}] - #{i}'
                             if songs[i - 1].get("user_duration") is not None
                             else f'{songs[i - 1].get("title")} - #{i}'
                             for i in range(1, len(songs) + 1)]
                songs_str = ", ".join(songs_arr)
                songs_arr = divide_chunks(songs_str, 470, lst=songs_arr, joinparam=', ')
                send_list(songs_str, songs_arr, 1, "list")

        def songrequest_command(username=None, messagesplit=None, message=None):
            global sr
            if sr and messagesplit[0][1:] == "sr" and message != f"{prefix}sr" and not checkbanlist(username):
                match = sr_download(messagesplit, username, timecode_pos=2)
                if not match:
                    if re.match(timecode_re, messagesplit[-1]):
                        query = ' '.join(messagesplit[1:-1])
                        sr_download_queue.call_download_clip(
                            query, username, user_duration=messagesplit[-1], ytsearch=True)
                    else:
                        query = ' '.join(messagesplit[1:])
                        sr_download_queue.call_download_clip(
                            query, username, user_duration=None, ytsearch=True)
            elif message == f"{prefix}sr" and not checkbanlist(username):
                if checkmodlist(username):
                    if sr:
                        sr = False
                        send_message(f'{prefix}sr off {sad_emote}')
                    else:
                        sr = True
                        send_message(f'{prefix}sr on {love_emote}')
                elif sr:
                    send_message(f'{username}, {prefix}sr <youtube/soundcloud link> - play audio')

        def sql_command(username=None, messagesplit=None, message=None, pipe=False):
            if messagesplit[0][1:] == 'sql' and checkmodlist(username):
                try:
                    if messagesplit[1]:
                        result = db.sql_query(" ".join(messagesplit[1:]))
                        if result:
                            result = [' - '.join(str(j) for j in i) for i in result]
                            result_str = " , ".join(result)
                            if pipe:
                                return result_str.split()
                            if len(result_str) > 480:
                                result_arr = divide_chunks(result_str, 470, result, joinparam=' , ')
                                for i in result_arr:
                                    send_message(i)
                            else:
                                send_message(result_str)
                        elif not result and 'select' == messagesplit[1].lower():
                            if pipe:
                                return f'{username}, no results {sad_emote}'.split()
                            send_message(f'{username}, no results {sad_emote}')
                        elif not result:
                            if pipe:
                                return f'{username}, done {love_emote}'.split()
                            send_message(f'{username}, done {love_emote}')
                except IndexError:
                    if pipe:
                        return f'{username}, no query {sad_emote}'.split()
                    send_message(f'{username}, no query {sad_emote}')

        def cancel_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == 'cancel' and not checkbanlist(username):
                if not playlist:
                    send_message(f'{username}, playlist is empty {sad_emote}')
                    return
                try:
                    if messagesplit[1]:
                        playlist_cancelled = []
                        playlist_to_del = []
                        playlist_not_found = []
                        username_in_playlist = False
                        for i in range(1, len(messagesplit)):
                            song_cancelled_title = False
                            try:
                                target = int(messagesplit[i])
                                if not 0 < target <= len(playlist):
                                    playlist_not_found.append(f'{target}')
                                    continue
                                if username in playlist[target - 1][5]:
                                    playlist_to_del.append(playlist[target - 1])
                                    if playlist[target - 1][3] is not None:
                                        playlist_cancelled.append(
                                            f'{playlist[target - 1][1]} '
                                            f'[{seconds_convert(playlist[target - 1][3])}]'
                                        )
                                    else:
                                        playlist_cancelled.append(playlist[target - 1][1])
                                    username_in_playlist = True
                            except ValueError:
                                target = messagesplit[i]
                                for j in playlist:
                                    if any(target in x for x in [j[1], j[1].lower()]) and username == j[5]:
                                        if j[3] is not None:
                                            playlist_cancelled.append(f'{j[1]} [{seconds_convert(j[3])}]')
                                        else:
                                            playlist_cancelled.append(j[1])
                                        playlist_to_del.append(j)
                                        song_cancelled_title = True
                                        username_in_playlist = True
                                if not song_cancelled_title:
                                    playlist_not_found.append(target)
                        if playlist_to_del:
                            for i in playlist_to_del:
                                try:
                                    playlist.remove(i)
                                except ValueError:
                                    playlist_cancelled = list(set(playlist_cancelled))
                        if not username_in_playlist:
                            send_message(f'{username}, nothing to cancel {sad_emote}')
                            return
                        response = []
                        if playlist_cancelled:
                            response.append(f'Cancelled: {", ".join(playlist_cancelled)} {love_emote}')
                        if playlist_not_found:
                            response.append(f'Not found: {", ".join(playlist_not_found)} {sad_emote}')
                        if response:
                            responsestr = " ".join(response)
                            if len(responsestr) > 480:
                                response *= 0
                                if playlist_cancelled:
                                    response.append(f'Cancelled: {len(playlist_cancelled)}')
                                if playlist_not_found:
                                    response.append(f'Not found: {len(playlist_not_found)} {sad_emote}')
                                send_message(f'{username}, {" ".join(response)}')
                            else:
                                send_message(f'{username}, {responsestr}')
                except IndexError:
                    song_cancelled = False
                    for i in playlist:
                        if username == i[5]:
                            if i[3] is not None:
                                send_message(f'{username}, Cancelled: {i[1]} [{seconds_convert(i[3])}] '
                                             f'{love_emote}')
                            else:
                                send_message(f'{username}, Cancelled: {i[1]} {love_emote}')
                            song_cancelled = True
                            playlist.remove(i)
                            break
                    if not song_cancelled:
                        send_message(f'{username}, nothing to cancel {sad_emote}')

        def ban_user_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "ban" and message != f"{prefix}ban" and checkmodlist(username):
                as_loop.create_task(ban_mod_commands(username, messagesplit, 'users banned', 'already banned',
                                                     checkbanlist, db.add_ban, True))

        def unban_user_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "unban" and message != f"{prefix}unban" and checkmodlist(username):
                as_loop.create_task(ban_mod_commands(username, messagesplit,
                                                     'users unbanned', f'not in the list {sad_emote}',
                                                     checkbanlist, db.remove_ban, False))

        def mod_user_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "mod" and message != f"{prefix}mod" and username == admin:
                as_loop.create_task(ban_mod_commands(username, messagesplit, 'users modded', 'already modded',
                                                     checkmodlist, db.add_mod, True))

        def unmod_user_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "unmod" and message != f"{prefix}unmod" and username == admin:
                as_loop.create_task(ban_mod_commands(username, messagesplit,
                                                     'users unmodded', f'not in the list {sad_emote}',
                                                     checkmodlist, db.remove_mod, False))

        def set_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "set" and message != f"{prefix}set" and not checkbanlist(username):
                selected = messagesplit[1].lower()
                if selected.endswith('.png') or selected.endswith('.gif'):
                    my_file = Path("custom/" + selected)
                    if my_file.is_file():
                        call_draw('custom/', selected)
                    else:
                        send_message(f'{username}, {selected} not found {sad_emote} ')
                else:
                    send_message('{}, names include extensions [png/gif]'.format(username))

        def setrand_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "setrand" and not checkbanlist(username):
                try:
                    randsrc = messagesplit[1]
                    if not any(x == randsrc for x in ['png', 'gif', 'link', 'pixiv']):
                        send_message(f'{username}, {prefix}setrand [png/gif/pixiv]')
                    elif randsrc == 'gif':
                        onlygif = [f for f in listdir('custom/') if f.endswith('.gif')]
                        set_random_pic(onlygif, f'{username}, gif not found {sad_emote}')
                    elif randsrc == 'png':
                        onlypng = [f for f in listdir('custom/') if f.endswith('.png')]
                        set_random_pic(onlypng, f'{username}, png not found {sad_emote}')
                    elif randsrc == 'pixiv':
                        asyncio.run_coroutine_threadsafe(Pixiv.random_pixiv_art(), as_loop)
                except IndexError:
                    onlyfiles = [f for f in listdir('custom/') if isfile(join('custom/', f))]
                    set_random_pic(onlyfiles, f'{username}, {prefix}list is empty {sad_emote}')

        def search_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "search" and message != f'{prefix}search' and not checkbanlist(
                    username):
                words = checkIfNoLink('!search')
                if messagesplit[1].startswith(("'", '"')) and messagesplit[1].endswith(("'", '"')):
                    search_words = [x for x in words if x.startswith(messagesplit[1][1:-1])]
                else:
                    search_words = [x for x in words if messagesplit[1].lower() in x]
                str1 = ' '.join(search_words)
                allpages = divide_chunks(str1, 480)
                send_list(str1, allpages, 2, "search")

        def list_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "list" and not checkbanlist(username):
                words, linkwords = checkIfNoLink('!list')
                linkstr1 = ' '.join(linkwords)
                linkallpages = divide_chunks(linkstr1, 480)
                str1 = ' '.join(words)
                allpages = divide_chunks(str1, 480)
                try:
                    pagenum = int(messagesplit[2])
                    if messagesplit[0][1:] == "list" and messagesplit[1] == "links":
                        send_list(linkstr1, linkallpages, 2, "list")
                except IndexError:
                    try:
                        if messagesplit[0][1:] == "list" and messagesplit[1] == "links":
                            send_list(linkstr1, linkallpages, 2, "list")
                            return
                        send_list(str1, allpages, 1, "list")
                    except IndexError:
                        send_list(str1, allpages, 1, "list")

        def banlist_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "banlist" and checkmodlist(username):
                checklist("banlist")

        def modlist_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "modlist" and checkmodlist(username):
                checklist("modlist")

        def link_chat_command(username=None, messagesplit=None, message=None):
            if message == f"{prefix}link" and not checkbanlist(username):
                if lastlink:
                    send_message('{}, {} - {}'.format(username, lastlink, last_rand_img))
                else:
                    send_message(f'nothing here {sad_emote}')
            elif messagesplit[0][1:] == "link" and message != f"{prefix}link" and not checkbanlist(username):
                as_loop.create_task(link_command(username, messagesplit[1:]))

        def save_command(username=None, messagesplit=None, message=None):
            if message == f'{prefix}save' and not checkbanlist(username):
                if re.match(regex, lastlink):
                    messagesplit.append(lastlink)
                    messagesplit.append(''.join(random.choices(
                        'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10)))
                    change_save_command(username, messagesplit, do_save_response=True)
                else:
                    send_message(f'{username}, nothing to save {sad_emote}')
            elif messagesplit[0][1:] == "save" and message != f"{prefix}save" and not checkbanlist(username):
                try:
                    if messagesplit[2]:
                        change_save_command(username, messagesplit, do_save_response=True)
                except IndexError:
                    messagesplit.append(''.join(random.choices(
                        'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10)))
                    change_save_command(username, messagesplit, do_save_response=True)

        def olist_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "olist" and not checkbanlist(username):
                owner_list(username)

        def del_chat_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "del" and message != f"{prefix}del" and not checkbanlist(username):
                as_loop.create_task(del_command(username, messagesplit))

        def ren_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "ren" and message != f"{prefix}ren" and not checkbanlist(username):
                as_loop.create_task(rename_command(username, messagesplit))

        def info_command(username=None, messagesplit=None, message=None, pipe=False):
            if messagesplit[0][1:] == "info" and not checkbanlist(username):
                response = f'shtcd {bot_ver}, uptime: {seconds_convert(floor(time.time() - startTime), explicit=True)}'
                if pipe:
                    return response.split()
                send_message(response)

        def orand_command(username=None, messagesplit=None, message=None):
            global last_rand_img
            if messagesplit[0][1:] == "orand" and not checkbanlist(username):
                result = db.check_ownerlist(username)
                try:
                    if not result:
                        send_message(f'{username}, nothing to set {sad_emote}')
                        return
                    result = [item[0] for item in result]
                    randsrc = messagesplit[1]
                    if all(randsrc != x for x in ['gif', 'png']):
                        send_message(f'{username}, png/gif only')
                    elif randsrc == 'gif':
                        onlygif = [f for f in result if f.endswith('.gif')]
                        set_random_pic(onlygif, f'{username}, gif not found {sad_emote}')
                    elif randsrc == 'png':
                        onlypng = [f for f in result if f.endswith('.png')]
                        set_random_pic(onlypng, f'{username}, png not found {sad_emote}')
                except IndexError:
                    selected = random.choice(result)
                    updatelastlink(selected)
                    last_rand_img = selected
                    call_draw('custom/', selected)

        def help_chat_command(username=None, messagesplit=None, message=None, pipe=False):
            if messagesplit[0][1:] == 'help' and not checkbanlist(username):
                try:
                    help_command_quoted = False
                    help_command = " ".join(messagesplit[1:])
                    command = messagesplit[1]
                    if command.startswith(("'", '"')) and command.endswith(("'", '"')):
                        command = command[1:-1]
                    if help_command.startswith(("'", '"')) and help_command.endswith(("'", '"')):
                        help_command = help_command[1:-1]
                        help_command_quoted = True
                    if not set(command.split()).intersection(commands_list + mod_commands_list +
                                                             [i[1:] for i in commands_list] +
                                                             [i[1:] for i in mod_commands_list]):
                        if pipe:
                            return f'{username}, unknown command {sad_emote}'.split()
                        send_message(f'{username}, unknown command {sad_emote}')
                        return
                    response = []
                    if help_command_quoted:
                        for i in commands_desc:
                            if i.startswith(help_command) or i[1:].startswith(help_command):
                                response.append(i)
                    else:
                        for i in commands_desc:
                            if help_command in i:
                                response.append(i)
                    if response:
                        response_str = ", ".join(response)
                        if pipe:
                            return response_str.split()
                        if len(response_str) > 480:
                            response_arr = divide_chunks(response_str, 470, response, joinparam=', ')
                            for i in response_arr:
                                send_message(i)
                        else:
                            send_message(response_str)
                    else:
                        if pipe:
                            return f'{username}, no results {sad_emote}'.split()
                        send_message(f'{username}, no results {sad_emote}')
                except IndexError:
                    if pipe:
                        return f'Public command list: {", ".join(i[1:] for i in commands_list)} ; ' \
                               f'Mod: {", ".join(i[1:] for i in mod_commands_list)}'.split()
                    send_message(f'Public command list: {", ".join(i[1:] for i in commands_list)} ; '
                                 f'Mod: {", ".join(i[1:] for i in mod_commands_list)}')

        def title_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "title" and checkmodlist(username):
                as_loop.create_task(change_stream_settings(username, messagesplit, 'title'))

        def game_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "game" and checkmodlist(username):
                as_loop.create_task(change_stream_settings(username, messagesplit, 'game'))

        def change_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "change" and message != f"{prefix}change" and not checkbanlist(username):
                change_save_command(username, messagesplit, do_draw=True)

        def pipe_command(username=None, messagesplit=None, message=None):
            if messagesplit[0][1:] == "pipe" and message != f"{prefix}pipe" and not checkbanlist(username):
                pipesplit = " ".join(messagesplit[1:]).split(' | ')
                if len(pipesplit) < 2:
                    send_message(f'{username}, you need at least two commands {sad_emote}')
                    return
                pipesplit = [f'{prefix}{i}' for i in pipesplit]
                result = pipesplit[0].split()[1:]

                def lookahead(iterable):
                    """Pass through all values from the given iterable, augmented by the
                    information if there are more values to come after the current one
                    (True), or if it is the last value (False).
                    """
                    it = iter(iterable)
                    last = next(it)
                    for val in it:
                        yield last, False
                        last = val
                    yield last, True

                pipe = True
                for i, last_item in lookahead(pipesplit):
                    i = i.split()
                    if last_item:
                        pipe = False
                        if i[0][1:] == 'tts':
                            i[0] += ':'
                        if i[1:]:
                            result.insert(0, " ".join(i[1:]))
                            #  insert last command args to specify users, append to tts
                    command = commands_dict.get(i[0][1:], None)
                    if command is None:
                        send_message(f'{username}, {i[0][1:]} - unknown command {sad_emote}')
                        return
                    try:
                        result.insert(0, i[0])  # insert command string at the beginning, so it looks like chat message
                        result = command(username, result, " ".join(result), pipe=pipe)
                        if result is None and not last_item:
                            send_message(f'{username}, {i[0][1:]} - mod command {sad_emote}')
                            return
                    except TypeError:
                        send_message(f'{username}, {i[0][1:]} - unsupported command {sad_emote}')
                        return

        def tts_cfg_command(username=None, messagesplit=None, message=None):
            global tts
            if messagesplit[0] == f'{prefix}tts' and checkmodlist(username):
                try:
                    if messagesplit[1] == 'vc':
                        call_tts.send_set_tts_vc(username, messagesplit)
                    elif messagesplit[1] == 'vol':
                        try:
                            call_tts.engine.setProperty('volume', float(messagesplit[2]))
                            send_message('{}, vol={}'.format(username, float(messagesplit[2])))
                        except IndexError:
                            send_message('{}, vol={}'.format(username, call_tts.engine.getProperty('volume')))
                    elif messagesplit[1] == 'rate':
                        try:
                            call_tts.engine.setProperty('rate', int(messagesplit[2]))
                            send_message('{}, rate={}'.format(username, float(messagesplit[2])))
                        except IndexError:
                            send_message('{}, rate={}'.format(username, call_tts.engine.getProperty('rate')))
                    elif messagesplit[1] == 'cfg':
                        send_message(f"vol={call_tts.engine.getProperty('volume')}, rate="
                                     f"{call_tts.engine.getProperty('rate')}, "
                                     f"vc={call_tts.get_tts_vc_key(call_tts.engine.getProperty('voice'))}")
                except IndexError:
                    if tts:
                        tts = False
                        send_message(f'tts off {sad_emote}')
                    else:
                        tts = True
                        send_message(f'tts on {love_emote}')

        def tts_command(username=None, messagesplit=None, message=None, pipe=False):
            call_tts.temper.append([" ".join(messagesplit), username])

        def notify_command(username=None, messagesplit=None, message=None, pipe=False):
            if messagesplit[0][1:] == "notify" and message != f"{prefix}notify" and not checkbanlist(username):
                if not 4 <= len(messagesplit[1]) <= 25:
                    send_message(f'{username}, username must be between 4 and 25 characters {sad_emote}')
                    return
                notify_message = " ".join(messagesplit[2:])
                if not notify_message:
                    send_message(f'{username}, no notify message {sad_emote}')
                    return
                notify_list.append({'recipient': messagesplit[1].lower(),
                                    'message': notify_message,
                                    'date': time.time(),
                                    'sender': username})

        async def check_chat_notify(username):
            nonlocal notify_list
            if notify_list and any(d['recipient'] == username for d in notify_list):
                notify_check_inprogress.append(username)
                response = []
                for i in notify_list:
                    if i['recipient'] == username:
                        response.append(f'{i["sender"]}: {i["message"]} '
                                        f'({seconds_convert(floor(time.time() - i["date"]), explicit=True)} ago)')
                if response:
                    response_str = f'{username}, {"; ".join(response)}'
                    if len(response_str) > 480:
                        for i in divide_chunks(response_str, 480, response, joinparam='; '):
                            send_message(i)
                            await asyncio.sleep(1)
                    else:
                        send_message(response_str)
                notify_list = [d for d in notify_list if d['recipient'] != username]
                notify_check_inprogress.remove(username)

        numba = str(db.get_imgcount()[0][0])

        while True:
            line = str(s.recv(1024))
            if "End of /NAMES list" in line:
                break

        username = ''
        readbuffer = ''
        chat_msg = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")

        commands_dict = {
            'die': die_command,
            'exit': exit_command,
            'log': log_command,
            'np': np_command,
            'srv': srv_command,
            'srq': srq_command,
            'srs': srs_command,
            'src': src_command,
            'srp': srp_command,
            'srt': srt_command,
            'srf+': srf_plus_command,
            'srf-': srf_minus_command,
            'srfp': srfp_command,
            'srfl': srfl_command,
            'srf': srf_command,
            'sr': songrequest_command,
            'sql': sql_command,
            'cancel': cancel_command,
            'ban': ban_user_command,
            'unban': unban_user_command,
            'mod': mod_user_command,
            'unmod': unmod_user_command,
            'set': set_command,
            'setrand': setrand_command,
            'search': search_command,
            'list': list_command,
            'banlist': banlist_command,
            'modlist': modlist_command,
            'link': link_chat_command,
            'save': save_command,
            'olist': olist_command,
            'del': del_chat_command,
            'ren': ren_command,
            'info': info_command,
            'orand': orand_command,
            'help': help_chat_command,
            'title': title_command,
            'game': game_command,
            'change': change_command,
            'pipe': pipe_command,
            'tts': tts_cfg_command,
            'tts:': tts_command,
            'notify': notify_command
        }

        commands_desc = [f'change «link» - change, {prefix}change «link» «name» - change+save',
                         f'save «link» «name» - save only',
                         f'set «name» - set downloaded pic',
                         f'setrand [gif/png] - set random saved pic',
                         f'setrand pixiv - set random pixiv art',
                         f'list [page] - check saved pics',
                         f'list links [page] - check pics with saved link',
                         f'search «name» [page] - find image in {prefix}list [e.g. gif, png], wrap query in '
                         f'quotes to search using "startswith()"',
                         f'link «name» «name2»... - get saved pic link',
                         f'link - last {prefix}setrand/{prefix}o random pic link+name',
                         f'ban «name» «name2».. - add user to ignore-list',
                         f'unban «name» «name2».. - remove user from ignore-list',
                         f'banlist - get bot ignore-list',
                         f'ren - change saved pic filename',
                         f'del - delete saved pic(s)',
                         f'modlist - get bot mod-list',
                         f'tts - enable/disable tts',
                         f'tts cfg - current tts config',
                         f'tts vol/rate/vc [value] - get/change tts volume/speech rate/voice',
                         f'sr <yt/scld> [timecode] - play music with youtube link/id/search, '
                         f'soundcloud links, optional timecode(start time)',
                         f'srq [page] - current queue',
                         f'srf [page] - your favorites list',
                         f'srf+ [url] [timecode] - favorite a song, optional timecode, np song if no url',
                         f'srf- «index1» «index2».. - remove from favorites by list index',
                         f'srfp «word/index» [word2/index2].. - play songs from favorites ({prefix}srf)',
                         f'srfl «index1» «index2».. - get song link',
                         f'src - clear current playlist',
                         f'srt - set time for current song',
                         f'srs [word/index] [word2/index2].. - pure {prefix}srs = skip current song, word/index = '
                         f'queue song',
                         f'srv [value] - get/change volume',
                         f'srp - play/pause',
                         f'olist - list of your saved pics',
                         f'orand [png/gif] - set random image from {prefix}olist',
                         f'die - set greenscreen.png, mod command',
                         f'log - enable/disable chat logging, admin command',
                         f'mod/unmod - add user to mod-list, admin command',
                         f'exit - clear image/sr folders, taskkill bot',
                         f'help [command] - view bot commands help, pure {prefix}help = commands list, wrap command in '
                         f'quotes to search using "startswith()"',
                         f'np - get current song link, name, time, duration',
                         f'cancel [word/index] [word2/index2].. - cancel your songrequest(s), pure {prefix}cancel = '
                         f'cancel nearest to play',
                         f'sql <query> - execute sql query and get result PogChamp',
                         f'tts: <msg> - say message, even when tts is off',
                         f'title <query> - change stream title',
                         f'game <query> - change stream game',
                         f'info - get bot version, uptime',
                         f'pipe - run commands in chain, transfer result from one command to another, '
                         f'last command gives complete result, supported commands: '
                         f'{", ".join([k for k, v in commands_dict.items() if k != "pipe" and "pipe" in v.__code__.co_varnames])}; '
                         f'usage: {prefix}pipe <command1> | <command2>..']

        commands_desc = [prefix + x for x in commands_desc]

        while True:
            try:
                readbuffer += s.recv(1024).decode('utf-8')
            except UnicodeDecodeError:
                pass
            temper = readbuffer.split("\r\n")
            readbuffer = temper.pop()
            for line in temper:
                if line.startswith("PING :tmi.twitch.tv"):
                    s.send(bytes("PONG\r\n", "UTF-8"))
                    continue

                username = re.search(r"\w+", line).group(0)
                message = chat_msg.sub("", line)
                messagesplit = message.split()

                print(f"{username}: {message}")

                call_tts.temper.append([message, username])

                if all(x != username for x in notify_check_inprogress):
                    as_loop.create_task(check_chat_notify(username))

                if logs:
                    strdate = getCurDate()
                    strdate = str(strdate).replace(':', '.', 3)
                    with open('log/' + date + '.txt', 'a+', encoding='utf8') as log:
                        log.write('\n')
                        log.write('[' + strdate + '] ' + username + ": " + message)

                if message.startswith(prefix):
                    command = commands_dict.get(messagesplit[0][1:], None)
                    if command is None:
                        continue
                    command(username=username, messagesplit=messagesplit, message=message)


class ThreadDB(threading.Thread):

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        global c
        global conn
        conn = sqlite3.connect('db/picturebot.db', check_same_thread=False)
        c = conn.cursor()

    def add_owner(self, filename, owner):
        with conn:
            try:
                lock.acquire(True)
                c.execute('INSERT INTO owners (filename, owner) VALUES (:filename, :owner)',
                          {'filename': filename, 'owner': owner})
            finally:
                lock.release()

    def remove_owner(self, filename):
        with conn:
            try:
                lock.acquire(True)
                c.executemany('DELETE FROM owners WHERE filename = ?', filename)
            finally:
                lock.release()

    def add_srfavs(self, song, owner, filename, user_duration, link, duration):
        with conn:
            try:
                lock.acquire(True)
                c.execute('INSERT INTO srfavs (song, owner, filename, user_duration, link, duration) '
                          'VALUES (:song, :owner, :filename, :user_duration, :link, :duration)',
                          {'song': song, 'owner': owner, 'filename': filename, 'user_duration': user_duration,
                           'link': link, 'duration': duration})
            finally:
                lock.release()

    def remove_srfavs(self, data):
        with conn:
            try:
                lock.acquire(True)
                c.executemany("DELETE FROM srfavs WHERE song = ? and owner = ? and filename = ? and "
                              "user_duration = ? and link = ? and duration = ?", data)
            finally:
                lock.release()

    def check_srfavs_list(self, owner):
        try:
            lock.acquire(True)
            c.execute('SELECT song, filename, user_duration, link, duration FROM srfavs WHERE owner = :owner',
                      {'owner': owner})
            return c.fetchall()
        finally:
            lock.release()

    def get_srfavs_filenames(self):
        try:
            lock.acquire(True)
            c.execute('SELECT filename FROM srfavs')
            return c.fetchall()
        finally:
            lock.release()

    def check_owner(self, filename, owner):
        try:
            lock.acquire(True)
            c.execute('SELECT owner FROM owners WHERE filename = :filename AND owner = :owner', {'filename': filename,
                                                                                                 'owner': owner})
            return c.fetchall()
        finally:
            lock.release()

    def check_ownerlist(self, owner):
        try:
            lock.acquire(True)
            c.execute('SELECT filename FROM owners WHERE owner = :owner', {'owner': owner})
            return c.fetchall()
        finally:
            lock.release()

    def update_owner_filename(self, filename, new_filename):
        with conn:
            try:
                lock.acquire(True)
                c.execute('UPDATE owners SET filename = :new_filename WHERE filename = :filename',
                          {'filename': filename,
                           'new_filename':
                               new_filename})
            finally:
                lock.release()

    def add_link(self, link, filename):
        with conn:
            try:
                lock.acquire(True)
                c.execute('INSERT INTO links (link, filename) VALUES (:link, :filename)',
                          {'link': link, 'filename': filename})
            finally:
                lock.release()

    def remove_link(self, filename):
        with conn:
            try:
                lock.acquire(True)
                c.executemany('DELETE FROM links WHERE filename = ?', filename)
            finally:
                lock.release()

    def update_link_filename(self, filename, new_filename):
        with conn:
            try:
                lock.acquire(True)
                c.execute('UPDATE links SET filename = :new_filename WHERE filename = :filename', {'filename': filename,
                                                                                                   'new_filename':
                                                                                                       new_filename})
            finally:
                lock.release()

    def check_filename_has_link(self, filename):
        try:
            lock.acquire(True)
            c.execute('SELECT filename FROM links WHERE filename = :filename', {'filename': filename})
            return c.fetchall()
        finally:
            lock.release()

    def get_links_filenames(self):
        try:
            lock.acquire(True)
            c.execute('SELECT filename FROM links')
            return c.fetchall()
        finally:
            lock.release()

    def get_links_and_filenames(self):
        try:
            lock.acquire(True)
            c.execute('SELECT link, filename FROM links')
            return c.fetchall()
        finally:
            lock.release()

    def get_link(self, filename):
        try:
            lock.acquire(True)
            c.execute('SELECT link FROM links WHERE filename = :filename', {'filename': filename})
            return c.fetchall()
        finally:
            lock.release()

    def get_imgcount(self):
        try:
            lock.acquire(True)
            c.execute('SELECT count FROM imgcount')
            return c.fetchall()
        finally:
            lock.release()

    def update_imgcount(self, count):
        global numba
        numba = int(numba) + 1
        numba = str(numba)
        with conn:
            try:
                lock.acquire(True)
                c.execute('UPDATE imgcount SET count = :count', {'count': count})
            finally:
                lock.release()

    def check_if_mod(self, username):
        try:
            lock.acquire(True)
            c.execute('SELECT username FROM moderators WHERE username = :username', {'username': username})
            return c.fetchall()
        finally:
            lock.release()

    def check_moderators(self):
        try:
            lock.acquire(True)
            c.execute('SELECT username FROM moderators')
            return c.fetchall()
        finally:
            lock.release()

    def add_mod(self, username):
        with conn:
            try:
                lock.acquire(True)
                c.executemany("INSERT INTO moderators (username) VALUES (?)", username)
            finally:
                lock.release()

    def remove_mod(self, username):
        with conn:
            try:
                lock.acquire(True)
                c.executemany("DELETE FROM moderators WHERE username = ?", username)
            finally:
                lock.release()

    def check_if_banned(self, username):
        try:
            lock.acquire(True)
            c.execute('SELECT username FROM banned WHERE username = :username', {'username': username})
            return c.fetchall()
        finally:
            lock.release()

    def check_banned(self):
        try:
            lock.acquire(True)
            c.execute('SELECT username FROM banned')
            return c.fetchall()
        finally:
            lock.release()

    def add_ban(self, username):
        with conn:
            try:
                lock.acquire(True)
                c.executemany("INSERT INTO banned (username) VALUES (?)", username)
            finally:
                lock.release()

    def remove_ban(self, username):
        with conn:
            try:
                lock.acquire(True)
                c.executemany("DELETE FROM banned WHERE username = ?", username)
            finally:
                lock.release()

    def sql_query(self, query):
        with conn:
            try:
                lock.acquire(True)
                try:
                    c.execute(query)
                except Exception as e:
                    return [(str(e),)]
                return c.fetchall()
            finally:
                lock.release()


Main = ThreadMain("ThreadMain")
Drawing = threading.Thread(target=ThreadPic)
Pixiv = ThreadPixiv("ThreadPixiv")
AsyncioLoop = AsyncioLoops(as_loop)
call_tts = ThreadTTS("calltts")
db = ThreadDB("ThreadDB")
huis_player = ThreadPlayer('ThreadPlayer')
sr_queue_loop = asyncio.new_event_loop()
sr_queue = AsyncioLoops(sr_queue_loop)
sr_download_loop = asyncio.new_event_loop()
sr_download_queue = AsyncioLoops(sr_download_loop)

Main.start()
Drawing.start()
Pixiv.start()
call_tts.start()
db.start()
huis_player.start()

Main.join()
Drawing.join()
Pixiv.join()
call_tts.join()
db.join()
huis_player.join()
