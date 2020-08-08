import vlc
import socket
import json
import _database

from pixivapi import Size
from _utils import RunInThread

CHANNEL = "ciremun"
BOT = "shtcd"
admin = "ciremun"
screenwidth = 385
screenheight = 560
pixiv_artratio = 1.3
prefix = '!'
banned_tags = ['Pokémon', 'how to draw', 'oshinagaki', 'subarashikihokkorinosekai', 'catalog']
pixiv_size = Size.MEDIUM
clear_folders = ['data/pixiv/', 'data/images/']
tts_voices = {'haruka': 'Microsoft Haruka Desktop - Japanese',
              'mizuki': 'VE_Japanese_Mizuki_22kHz',
              'yuri': 'VE_Russian_Yuri_22kHz',
              'ivy': 'IVONA 2 Ivy OEM'}
tts_default_vc = tts_voices['ivy']
tts = True
tts_volume = 0.07
tts_rate = 1.3
logs = False
sr = True
player_last_vol = 23
max_duration = '10:00'
sr_cooldown = '60'
sr_max_per_request = 5

np = ''
np_duration = ''
sr_url = ''
sr_user = ''
lastlink = ''
last_rand_img = ''
playlist = []
PlayerInstance = vlc.Instance('--novideo')
Player = PlayerInstance.media_player_new()
Player.audio_set_volume(player_last_vol)
HOST = "irc.twitch.tv"
PORT = 6667
s = socket.socket()
db = _database.db
sr_queue = RunInThread('sr')
sr_download_queue = RunInThread('srdl')
px_download_queue = RunInThread('pixivdl')
main_queue = RunInThread('main')
utils_queue = RunInThread('utils')
commands_dict = {}
tokens = json.load(open('tokens.json'))
Main = None
