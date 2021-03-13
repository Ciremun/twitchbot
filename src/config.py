import socket
import json
import time
import sys
import os
from pathlib import Path
from os.path import join, dirname


from dotenv import load_dotenv
from pixivapi import Size
from youtube_dl import YoutubeDL

start_time = time.time()

channel = None
bot = None
prefix = None
admin = None
width = None
height = None
clear_folders = []
chat_log = None
pixiv_max_art_ratio = None
pixiv_banned_tags = []
tts = None
tts_vc = None
tts_voices = {}
tts_volume = None
tts_rate = None
sr = None
sr_volume = None
sr_max_song_duration = None
sr_user_cooldown = None
sr_max_songs_per_request = None
ydl_opts = {}
flaskPort = None
BotOAuth = None
ClientOAuth = None
ClientID = None
ChannelID = None
GoogleKey = None
ImgurClientID = None
PixivToken = None

cfg = json.load(open('config.json'))

load_dotenv(join(dirname(__name__), '.env'))
keys = {
    "BotOAuth":      os.environ.get('BotOAuth'),
    "ClientOAuth":   os.environ.get('ClientOAuth'),
    "ClientID":      os.environ.get('ClientID'),
    "ChannelID":     os.environ.get('ChannelID'),
    "GoogleKey":     os.environ.get('GoogleKey'),
    "ImgurClientID": os.environ.get('ImgurClientID'),
    "PixivToken":    os.environ.get('PixivToken'),
    "PixivClientID": os.environ.get('PixivClientID'),
    "PixivClientSecret": os.environ.get('PixivClientSecret')
}

for p, value in {**cfg, **keys}.items():
    setattr(sys.modules[__name__], p, value)

twitch_host = "irc.twitch.tv"
twitch_port = 6667
twitch_socket = socket.socket()
pixiv_size = Size.MEDIUM
np = ''
np_duration = '0'
sr_url = ''
sr_user = ''
last_link = ''
last_rand_img = ''
playlist = []
sr_cooldowns = {}
notify_in_progress = []
notify_list = []
prefix_len = len(prefix)

ydl = YoutubeDL(ydl_opts)

for folder in ['flask/images/', 'flask/images/pixiv/', 'flask/images/temp/', 'flask/images/user/']:
    Path(folder).mkdir(exist_ok=True)
