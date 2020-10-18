import socket
import json
import time
from pathlib import Path

from pixivapi import Size
from youtube_dl import YoutubeDL

start_time = time.time()

cfg = json.load(open('config.json'))
sr_volume = cfg['sr_volume']
pixiv_max_art_ratio = cfg['pixiv_max_art_ratio']
pixiv_banned_tags = cfg['pixiv_banned_tags']
tts = cfg['tts']
tts_vc = cfg['tts_vc']
tts_volume = cfg['tts_volume']
tts_rate = cfg['tts_rate']
sr = cfg['sr']
sr_volume = cfg['sr_volume']
tts_voices = cfg['tts_voices']
sr_max_song_duration = ''
sr_user_cooldown = ''

keys = json.load(open('keys.json'))
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
prefix_len = len(cfg['prefix'])

ydl = YoutubeDL(cfg['ydl_opts'])

for folder in ['flask/images/', 'flask/images/pixiv/', 'flask/images/temp/', 'flask/images/user/']:
    Path(folder).mkdir(exist_ok=True)
