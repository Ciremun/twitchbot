import asyncio
import vlc
import socket
import modules.database
from pixivapi import Size
from modules.utils import AsyncioLoop

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

np = ''
np_duration = ''
sr_url = ''
lastlink = ''
last_rand_img = ''
commands_list = [prefix + x for x in
                 ['change', 'save', 'set', 'setrand', 'list', 'search', 'link', 'sr', 'srq', 'srf', 'srfa', 'srfd',
                  'srfp', 'srfl', 'np', 'olist', 'orand', 'ren', 'del', 'cancel', 'help', 'tts:', 'info', 'pipe',
                  'notify']]
mod_commands_list = [prefix + x for x in
                     ['ban', 'unban', 'banlist', 'modlist', 'tts', 'srp', 'srs', 'srt', 'src', 'srv', 'sql',
                      'title',
                      'game']]
as_loop = asyncio.get_event_loop()
playlist = []
PlayerInstance = vlc.Instance()
Player = PlayerInstance.media_player_new()
Player.audio_set_volume(player_last_vol)
volume_await = False
HOST = "irc.twitch.tv"
PORT = 6667
s = socket.socket()
db = modules.database.db
my_loop = AsyncioLoop(as_loop)
sr_queue = AsyncioLoop(asyncio.new_event_loop())
sr_download_queue = AsyncioLoop(asyncio.new_event_loop())
commands_dict = {}
PASS, px_token, channel_id, client_id, client_auth = '', '', '', '', ''
Main = None
