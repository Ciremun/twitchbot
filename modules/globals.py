import vlc
import socket
import modules.database

from pixivapi import Size
from modules.utils import RunInThread

CHANNEL = "ciremun"
BOT = "shtcd"
admin = "ciremun"
screenwidth = 390
screenheight = 645
pixiv_artratio = 1.3
res = 'data/custom/'
drawfile = 'rempls.gif'
prefix = '!'
banned_tags = ['Pokémon', 'how to draw', 'oshinagaki', 'subarashikihokkorinosekai', 'catalog']
pixiv_size = Size.MEDIUM
clear_folders = ['data/sounds/sr/', 'data/pixiv/', 'data/images/']
tts_voices = {'haruka': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_JA-JP_HARUKA_11.0',
              'mizuki': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\VE_Japanese_Mizuki_22kHz',
              'yuri': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\VE_Russian_Yuri_22kHz',
              'ivy': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\Ivy RSI Harpo 22kHz'}
tts_default_vc = tts_voices['ivy']
tts = False
tts_volume = 0.15
logs = False
sr = True
player_last_vol = 23
ytdl_rate = 4000000
max_duration = '10:00'
sr_cooldown = '60'
sr_max_per_request = 5

np = ''
np_duration = ''
sr_url = ''
lastlink = ''
last_rand_img = ''
playlist = []
PlayerInstance = vlc.Instance('--novideo')
Player = PlayerInstance.media_player_new()
Player.audio_set_volume(player_last_vol)
HOST = "irc.twitch.tv"
PORT = 6667
s = socket.socket()
db = modules.database.db
sr_queue = RunInThread('sr')
sr_download_queue = RunInThread('srdl')
px_download_queue = RunInThread('pixivdl')
main_queue = RunInThread('main')
utils_queue = RunInThread('utils')
commands_dict = {}
PASS, px_token, channel_id, client_id, client_auth, google_key, imgur_client_id = [' '.join(token.split()[1:]) for token in open('data/special/tokens')]
Main = None
