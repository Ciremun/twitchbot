# shtcd twitch bot
  
set images, songrequests, tts, random pixiv arts  
change twitch stream title, game, upload images to imgur  
set image: any image link, pixiv links  
songrequests: youtube link/id/search  

## Install

### requirements

#### Python 3

    Pillow>=8.0.0
    pixiv-api>=0.3.6
    requests>=2.24.0
    youtube-dl>=2020.9.20
    Flask>=1.1.2
    Flask-SocketIO>=4.3.1
    gevent>=20.9.0
    gevent-websocket>=0.10.1

#### keys.json

create `keys.json`  

`BotOAuth`      (str): bot user OAuth token [twitchapps tmi](https://twitchapps.com/tmi/) helps obtain  
`ClientOAuth`   (str): user OAuth token with `channel_editor` scope, [twitchapps tokengen](https://twitchapps.com/tokengen/) helps obtain  
`Client-ID`     (str): twitch application Client ID, create app in [Twitch Developer Console](https://dev.twitch.tv/console/apps)  
`GoogleKey`     (str): [Google API](https://console.developers.google.com/apis/credentials) key for YouTube search  
`ImgurClientID` (str): [Imgur Client-ID](https://api.imgur.com/oauth2/addclient) for Imgur uploads  
`PixivToken`    (str): [Pixiv token](https://pixiv-api.readthedocs.io/en/latest/) for Pixiv arts  
`ChannelID`     (int): twitch channel id, optional  

#### images, text-to-speech, songrequests

server running on `localhost:5000`  
text-to-speech is not working inside OBS, use `localhost:5000/tts`  
`Chromium`: allow page Sound or click anywhere for tts  
`window.speechSynthesis.getVoices()` returns all the available voice URI  

### config.json

`channel`                  (str): twitch username to listen  
`bot`                      (str): twitch bot username  
`prefix`                   (str): chat command prefix  
`admin`                    (str): bot admin, twitch username  
`width`                    (int): image frame width in px  
`height`                   (int): image frame height in px  
`clear_folders`            (list of strings): clear folders on !exit  
`chat_log`                 (bool): toggle chat logging  
`pixiv_max_art_ratio`      (numeric): max pixiv art width/height ratio  
`pixiv_banned_tags`        (list of strings): exclude pixiv tags you dont want to see  
`tts`                      (bool): toggle tts  
`tts_vc`                   (str): startup tts voice, voiceURI  
`tts_voices`               (dict): dictionary of tts voices, keys are aliases, values are voiceURI  
`tts_volume`               (numeric): startup tts volume (0-1)  
`tts_rate`                 (numeric): startup tts rate (1-normal)  
`sr`                       (bool): toggle songrequests  
`sr_volume`                (int): startup songrequests volume (0-1)  
`sr_max_song_duration`     (str): songrequests non-mod max song duration, timecode string (ex. 10:00)  
`sr_user_cooldown`         (str): songrequests non-mod cooldown, timecode string  
`sr_max_songs_per_request` (int): max number of songs per request (ex. using srfp command)  
`ydl_opts:cookiefile`      (str): youtube session HTTP cookie file, optional  
`flaskPort`                (int): flask app port  

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
`<command> | <command>..` - pipe, run commands in chain, transfer result from one command to another, last command gives complete result, supported commands: sql, info, help, tts, notify  
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
`sr` - toggle songrequests  
`src` - clear current playlist  
`srt <t:timecode>` - set time for current song  
`srv [value]` - get/change volume  
`srp` - play/pause  

### bot admin

`log` - toggle chat logging  
`mod/unmod` - remove/add user to bot modlist  
`exit` - clear folders, exit bot  
