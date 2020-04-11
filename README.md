# shtcd twitch bot
  
let viewers set images on stream + songrequests + tts + change stream title, game  
supports png, jpg, gif, webp, pixiv links  
songrequests: youtube link/id/query, soundcloud links  

# Install

## req.txt

```
ffmpeg>=1.4
Pillow>=7.0.0
pixiv-api>=0.3.1
pygame>=1.9.6
pyglet>=1.4.10
python-vlc>=3.0.7110
pyttsx3>=2.81
requests>=2.22.0
youtube-dl>=2020.1.24
```

requires ffmpeg and vlc, tested on Python 3.7.5, Windows 10

## tokens
`special/tokens` - tokens file  
`twitch bot token` - read chat commands, tts  
`pixiv token` - set/download random pixiv arts  
`twitch channel id`, `client id`, `client OAuth with channel_editor scope` - edit stream title/game  

## global variables

`CHANNEL` (string) - twitch channel to listen  
`BOT` (string) - twtich bot username  
`admin` (string) - bot admin, twitch username  
`tts` (boolean) - enable/disable tts  
`tts_voices` (dict) - dictionary of tts voices, keys are names, values are voice registry keys  
`tts_default_vc` (string) - startup tts voice (e.g. tts_voices[key])  
`tts_volume` (numeric) - startup tts volume in percent (e.g. 0.35 - 35%)  
`logs` (boolean) - enable/disable chat logging  
`sr` (boolean) - enable/disable songrequests  
`screenwidth` (int) - pic window width in px  
`screenheight` (int) - pic window height in px  
`res` (string) - init image folder  
`drawfile` (string) - init image  
`prefix` (string) - chat command prefix  
`banned_tags` (list of strings) - exclude pixiv tags you dont want to see  
`pixiv_artratio` (numeric) - max pixiv art width/height ratio  
`clear_folders` (list of strings) - clear folders on !exit  
`player_last_vol` (int) - startup songrequests volume, 0 - 100  
`ytdl_rate` (int) - songrequests download speed in bytes/s  
`max_duration` (string) - songrequests max duration, no limit for bot moderators, timecode string (e.g. 10:00 - ten minutes)  

# commands

### everyone
`change <link> [name]` - change display pic, add name to save  
`save <link> [name]` - save only  
`set <name>` - set saved pic  
`list [page]` - list saved pics  
`list links [page]` - list pics with saved link  
`olist` - list of your saved pics  
`orand [png/gif]` - set random image from olist  
`setrand [gif/png/pixiv]` - set random saved pic or pixiv art  
`search <name> [page]` - find image in list (e.g. gif, png) wrap in qutoes for startswith search  
`link [name] [name2]...` - get saved pic link, no args - last random pic link, filename  
`ren <name> <new name>` - change saved pic filename  
`del <name> [name2]..` - delete saved pic(s)  
`sr <yt/scld> [timecode]` - play music with youtube link/id/search, soundcloud links, optional timecode(start time)  
`srq [page]` - current queue  
`srf [page]` - your favorites list  
`srfa [url] [timecode]` - favorite a song, optional timecode, no url - add now playing song  
`srfd <index1> [index2]..` - remove from favorites by list index  
`srfp <word/index> [word2/index2]..` - play songs from favorites (srf)  
`srfl <index1> [index2]..` - get song link(s)  
`np` - get current song link, name, time, duration  
`cancel [word/index] [word2/index2]..` - cancel your songrequest(s)  
`tts: <msg>` - say message, even when tts is off  
`info` - bot uptime  
`pipe <command1> | <command2>..` - run commands in chain, transfer result from one command to another, last command gives complete result, supported commands: sql, info, help, tts, notify  
`help [command]` - view bot commands help, no args - commands list, wrap command in qutoes for startswith search  
### bot moderators
`ban <name> [name2]..` - add user(s) to ignore-list  
`unban <name> [name2]..` - remove user(s) from ignore-list  
`banlist` - get bot ignore-list  
`modlist` - get bot moderators list  
`sql <query>` - execute sql query and get result  
`title [query]` - change stream title, no args - get current title  
`game [query]` - change stream game, no args - get current game  
`tts` - enable/disable tts  
`tts cfg` - current tts config  
`tts vol/rate/vc [value]` - get/change tts volume/speech rate/voice  
`sr` - enable/disable songrequests  
`src` - clear current playlist  
`srt` - set time for current song  
`srs [word/index] [word2/index2]..` - skip queue song by name/index, no args - skip now playing song  
`srv [value]` - get/change volume  
`srp` - play/pause  
`die` - set greenscreen.png  
### bot admin
`log` - enable/disable chat logging  
`mod/unmod` - remove/add user to bot modlist  
`exit` - clear folders, exit bot  
