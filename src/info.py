import src.config as g

prefix = g.prefix

commands_list = [prefix + x for x in
                 ['change', 'save', 'set', 'setrand', 'list', 'search', 'link', 'sr', 'srq', 'srf', 'srfa', 'srfd',
                  'srfp', 'srfl', 'np', 'olist', 'orand', 'ren', 'del', 'skip', 'help', 'tts', 'info', 'pipe',
                  'notify', 'when', 'imgur']]
mod_commands_list = [prefix + x for x in
                     ['ban', 'unban', 'banlist', 'modlist', 'ttscfg', 'srp', 'srt', 'src', 'srv', 'sql', 'title', 'game']]

pipe_commands = ['sql', 'info', 'help', 'tts', 'notify']

commands_desc = [prefix + x for x in [f'change <link> - change display pic, add name to save',
                                      f'save <link> [name] - save only',
                                      f'set <name> - set saved pic',
                                      f'setrand [gif/png/pixiv] - set random saved pic or pixiv art',
                                      f'list [page] - check saved pics',
                                      f'list links [page] - check pics with saved link',
                                      f'search <name> [page] - find image in list (e.g. gif, png) '
                                      f'wrap in quotes for startswith search',
                                      f'link [name] [name2]... - '
                                      f'get saved pic link, no args - last random pic link, filename',
                                      f'ban <name> [name2].. - add user to ignore-list',
                                      f'unban <name> [name2].. - remove user from ignore-list',
                                      f'banlist - get bot ignore-list',
                                      f'ren <name> <new name> - change saved pic filename',
                                      f'del <name> [name2].. - delete saved pic(s)',
                                      f'modlist - get bot mod-list',
                                      f'tts [vc:name] [msg] - message text-to-speech, vc:name to change voice dynamically, no args - get voices',
                                      f'ttscfg [vol/rate/vc/toggle] [value] - get/change tts volume/speech rate/voice, toggle tts, no args - current tts config',
                                      f'sr <yt/scld> [t:timecode] - play music with youtube link/id/search, '
                                      f'soundcloud links, optional timecode(start time)',
                                      f'srq [page] - current queue',
                                      f'srf [page] - your favorites list',
                                      f'srfa [url] [t:timecode] - favorite a song, optional timecode, np song if no url',
                                      f'srfd <word/index> [word/index].. - remove from favorites by word/list index',
                                      f'srfp <word/index> [word2/index2].. - play songs from favorites ({prefix}srf)',
                                      f'srfl <index1> <index2>.. - get song link',
                                      f'src - clear current playlist',
                                      f'srt <timecode> - set time for current song',
                                      f'srv [value] - get/change volume',
                                      f'srp - play/pause',
                                      f'olist - list of your saved pics',
                                      f'orand [png/gif] - set random image from {prefix}olist',
                                      f'log - enable/disable chat logging, admin command',
                                      f'mod/unmod - add user to mod-list, admin command',
                                      f'exit - clear folders, exit bot',
                                      f'help [command] - view bot commands help, no args - commands list, '
                                      f'wrap command in quotes for startswith search',
                                      f'np - get current song link, name, time, duration',
                                      f'skip [name/index] [name/index].. - skip your songrequest(s) by playlist index or word, ' 
                                      f'no args - skip now playing song, moderators skip any song',
                                      f'sql <query> - execute sql query and get result',
                                      f'title <query> - change stream title',
                                      f'game <query> - change stream game',
                                      f'info - get bot version, uptime',
                                      f'pipe <command1> | <command2>.. - run commands in chain, '
                                      f'transfer result from one command to another, '
                                      f'last command gives complete result, supported commands: '
                                      f'{", ".join([x for x in pipe_commands])}',
                                      f'notify <username> <message> - notify twitch user when they next type in chat',
                                      f'when - check when requested song is going to play, list all / search by name',
                                      f'imgur <file> - upload saved image to imgur, update link if exists (mods), get link, add to database']]
