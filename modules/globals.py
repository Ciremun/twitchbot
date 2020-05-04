import vlc
import socket
import modules.database

from pixivapi import Size
from modules.utils import RunInThread

CHANNEL = "ciremun"  # twitch channel to listen
BOT = "shtcd"  # twtich bot username
admin = "ciremun"  # bot admin
screenwidth = 390
screenheight = 990  # image window width/height in px
pixiv_artratio = 1.3  # max pixiv art width/height ratio
res = 'data/custom/'  # init image folder
drawfile = 'rempls.gif'  # init image
prefix = '!'
banned_tags = ['Pokémon', 'how to draw', 'oshinagaki', 'subarashikihokkorinosekai']  # ban pixiv tags
pixiv_size = Size.MEDIUM
clear_folders = ['data/sounds/sr/', 'data/pixiv/', 'data/images/']  # clear folders on !exit
tts_voices = {'haruka': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_JA-JP_HARUKA_11.0',
              'mizuki': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\VE_Japanese_Mizuki_22kHz',
              'yuri': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\VE_Russian_Yuri_22kHz',
              'ivy': r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\Ivy RSI Harpo 22kHz'}
tts_default_vc = tts_voices['ivy']
tts = False
tts_volume = 0.35
logs = False
sr = True
player_last_vol = 40  # !sr volume
ytdl_rate = 4000000  # 4Mb/s !sr download rate
max_duration = '10:00'  # !sr max song duration (no limit for mods)
sr_cooldown = '60'
sr_max_per_request = 5

np = ''
np_duration = ''
sr_url = ''
lastlink = ''
last_rand_img = ''
playlist = []
PlayerInstance = vlc.Instance()
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
commands_dict = {}
PASS, px_token, channel_id, client_id, client_auth = '', '', '', '', ''
Main = None
