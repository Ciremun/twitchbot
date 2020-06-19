# shtcd twitch bot
  
let viewers set images on stream, songrequests, tts, random pixiv arts  
extra: change twitch stream title&game, upload images to imgur  
set image: any image link, pixiv links  
songrequests: youtube link/id/query

## Install

### req

    ffmpeg>=1.4
    Pillow>=7.0.0
    pixiv-api>=0.3.1
    python-vlc>=3.0.7110
    requests>=2.22.0
    youtube-dl>=2020.5.3
    pafy>=0.5.5
    Flask>=1.1.2
    Flask-SocketIO>=4.3.0

requires ffmpeg and vlc, tested on Python 3.7.5, Windows 10

### tokens

create `tokens.json`  

`BotOAuth` (str): bot user OAuth token [twitchapps tmi](https://twitchapps.com/tmi/) helps obtain  
`ClientOAuth` (str): user OAuth token with `channel_editor` scope, [twitchapps tokengen](https://twitchapps.com/tokengen/) helps obtain  
`Client-ID` (str): twitch application Client ID, create app in [Twitch Developer Console](https://dev.twitch.tv/console/apps)  
`ChannelID` (int): twitch channel id, optional  
`GoogleKey` (str): generate [Google API](https://console.developers.google.com/apis/credentials) key for YouTube search  
`ImgurClientID` (str): [Register Imgur Application](https://api.imgur.com/oauth2/addclient) for Imgur uploads  
`PixivToken` (str): [Get Pixiv Token](https://pixiv-api.readthedocs.io/en/latest/)  

### images, text-to-speech

flask app running on `localhost:5000`  
`Chromium`: allow page Sound or click anywhere for tts  
`window.speechSynthesis.getVoices()` returns all the available voices  

### globals.py

`CHANNEL` (str): twitch username to listen  
`BOT` (str): twitch bot username  
`admin` (str): bot admin, twitch username  
`tts` (bool): enable/disable tts  
`tts_voices` (dict): dictionary of tts voices, keys are aliases, values are voiceURI  
`tts_default_vc` (str): startup tts voice, voiceURI  
`tts_volume` (numeric): startup tts volume in percent (0-1)  
`tts_rate` (numeric): startup tts rate (1-normal)  
`logs` (bool): enable/disable chat logging  
`sr` (bool): enable/disable songrequests  
`screenwidth` (int): pic window width in px  
`screenheight` (int): pic window height in px  
`prefix` (str): chat command prefix  
`banned_tags` (list of strings): exclude pixiv tags you dont want to see  
`pixiv_size` (pixivapi.Size): pixiv download size  
`pixiv_artratio` (numeric): max pixiv art width/height ratio  
`clear_folders` (list of strings): clear folders on !exit  
`player_last_vol` (int): startup songrequests volume (0-100)  
`max_duration` (str): songrequests non-mod max song duration, timecode string (ex. 10:00)  
`sr_cooldown` (str): songrequests non-mod cooldown, timecode string  
`sr_max_per_request` (int): max number of songs per request (ex. using srfp command)  

## Commands

### everyone

`change <link> [name]` - change display pic, add name to save  
`save <link> [name]` - save only  
`set <file>` - set saved pic  
`list [page]` - list saved pics  
`list links [page]` - list pics with saved link  
`olist` - your saved pics  
`orand [png/gif]` - set random image from olist  
`setrand [gif/png/pixiv]` - set random saved pic or pixiv art  
`search <file> [page]` - find image in list (e.g. gif, png) wrap in quotes for startswith search  
`link [file] [file]..` - get saved pic link, no args - last random pic link, filename  
`ren <file> <new filename>` - change saved pic filename  
`del <file> [file]..` - delete saved pic(s)  
`sr [link] [t:timecode]` - play music with youtube link/id/search, optional timecode  
`srq [page]` - current queue  
`srf [page]` - your favorites list  
`srfa [url] [t:timecode]` - favorite a song, optional timecode, no url - add now playing song  
`srfd <name/index> [name/index]..` - remove from favorites by name/list index  
`srfp <name/index> [name/index]..` - play songs from favorites (srf)  
`srfl <name/index> [index]..` - get song link(s)  
`np` - get current song link, name, time, duration  
`skip [name/index] [name/index]..` - skip your songrequest(s) by playlist index or name, no args - skip now playing song, bot moderators skip any song  
`tts [vc:name] [msg]` - message text-to-speech, vc:name to change voice dynamically, no args - get voices  
`info` - bot uptime  
`pipe <command> | <command>..` - run commands in chain, transfer result from one command to another, last command gives complete result, supported commands: sql, info, help, tts, notify  
`help [command]` - view bot commands help, no args - commands list, wrap command in quotes for startswith search  
`notify <username> <message>` - notify twitch user when they next type in chat  
`when [name]` - check when requested song is going to play (up to 5)  
`imgur <file>` - upload saved image to imgur, update link if exists (mods), get link, add to database  

### bot moderators

`ban <name> [name]..` - add user(s) to ignore-list  
`unban <name> [name]..` - remove user(s) from ignore-list  
`banlist` - get bot ignore-list  
`modlist` - get bot moderators list  
`sql <query>` - execute sql query and get result  
`title [query]` - change stream title, no args - get current title  
`game [query]` - change stream game, no args - get current game  
`ttscfg [vol/rate/vc/toggle] [value]` - get/change tts volume/speech rate/voice, toggle tts, no args - current tts config  
`sr` - enable/disable songrequests  
`src` - clear current playlist  
`srt <timecode>` - set time for current song  
`srv [value]` - get/change volume  
`srp` - play/pause  

### bot admin

`log` - enable/disable chat logging  
`mod/unmod` - remove/add user to bot modlist  
`exit` - clear folders, exit bot  
