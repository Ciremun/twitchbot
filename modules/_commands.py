import _info as info

from _utils import *
from _pixiv import Pixiv
from _tts import call_tts
from _decorators import bot_command
from _info import commands_list, mod_commands_list


@bot_command(name='exit')
def exit_command(message):
    if message.content[1:] == "exit" and message.author == g.admin:
        for folder in g.clear_folders:
            clear_folder(folder)
        os._exit(0)


@bot_command(name='log')
def log_command(message):
    if message.author == g.admin:
        if g.logs:
            g.logs = False
            send_message('logs off')
        else:
            g.logs = True
            send_message('logs on')


@bot_command(name='np')
def np_command(message):
    if not player_good_state():
        send_message(f'{message.author}, nothing is playing')
    elif str(g.Player.get_state()) == 'State.Paused':
        np_response('Paused')
    else:
        np_response('Now playing')


@bot_command(name='srv', check_func=is_mod)
def srv_command(message):
    try:
        value = int(message.parts[1])
        if not 0 <= value <= 100:
            raise ValueError
        if player_good_state():
            g.player_last_vol = value
            g.Player.audio_set_volume(g.player_last_vol)
            return
        send_message(f'{message.author}, nothing is playing')
    except IndexError:
        send_message(f'{g.prefix}sr vol={g.player_last_vol}')
    except ValueError:
        send_message(f'{message.author}, vol 0-100')


@bot_command(name='srq')
def srq_command(message):
    if g.sr:
        if not g.playlist:
            send_message(f'{message.author}, playlist is empty')
            return
        sr_list = [f'{x.title} [{seconds_convert(x.user_duration)}] #{i}'
                if x.user_duration is not None else f'{x.title} #{i}' for i, x in enumerate(g.playlist, start=1)]
        sr_str = ", ".join(sr_list)
        sr_list = divide_chunks(sr_str, 470, sr_list, joinparam=', ')
        send_list(message, sr_str, sr_list, 1, "list")


@bot_command(name='src', check_func=is_mod)
def src_command(message):
    if not g.playlist:
        send_message(f'{message.author} playlist is empty')
        return
    g.playlist.clear()
    send_message(f'queue wiped')


@bot_command(name='srp', check_func=is_mod)
def srp_command(message):
    if str(g.Player.get_state()) == 'State.Playing':
        g.Player.pause()
    elif str(g.Player.get_state()) == 'State.Paused':
        g.Player.play()
    else:
        send_message(f'{message.author}, nothing is playing')


@bot_command(name='srt', check_func=is_mod)
def srt_command(message):
    if not player_good_state():
        send_message(f'{message.author}, nothing is playing')
        return
    try:
        timecode = message.parts[1]
        if re.match(timecode_re, timecode):
            seconds = timecode_convert(timecode)
            if seconds > timecode_convert(g.np_duration):
                send_message(f'{message.author}, time exceeds duration! [{g.np_duration}]')
            else:
                g.Player.set_time(seconds * 1000)
        else:
            send_message(f'{message.author}, timecode error')
    except IndexError:
        send_message(f'{message.author}, no timecode')


@bot_command(name='srfa')
def srfa_command(message):
    if not sr_user_cooldown(message.author):
        try:
            url_or_timecode = message.parts[1]
            if re.match(timecode_re, url_or_timecode):
                message.parts.append(url_or_timecode)
                sr_download(message, g.sr_url, 2, save=True)
                return
            match = sr_download(message, url_or_timecode, 2, save=True)
            if not match:
                timecode_pos = None
                if re.match(timecode_re, message.parts[-1]):
                    timecode_pos = len(message.parts) - 1
                    message.parts[1] = ' '.join(message.parts[1:-1])
                else:
                    message.parts[1] = ' '.join(message.parts[1:])
                try_timecode(message, message.parts[1], timecode_pos, save=True, ytsearch=True)
        except IndexError:
            if not player_good_state():
                send_message(f'{message.author}, nothing is playing')
            else:
                message.parts.append(g.sr_url)
                sr_download(message, message.parts[1], 2, save=True)


@bot_command(name='srfd')
def srfd_command(message):
    if not message.content[1:] == 'srfd':
        songs = get_srfavs_dictlist(message.author)
        if not songs:
            send_message(f'{message.author}, no favorite songs found')
            return
        g.utils_queue.new_task(sr_favs_del, message, songs)


@bot_command(name='srfp')
def srfp_command(message):
    if not message.content[1:] == 'srfp' and sr(message.author):
        songs = get_srfavs_dictlist(message.author)
        if not songs:
            send_message(f'{message.author}, no favorite songs found')
            return
        response, target_not_found, response_added = [], [], []
        for i in range(1, len(message.parts)):
            try:
                index = int(message.parts[i])
                if not 0 < index <= len(songs):
                    target_not_found.append(message.parts[i])
                    continue
                song = songs[index - 1]
                g.sr_download_queue.new_task(download_clip, song.link, message.author,  user_duration=song.user_duration)
                response_added.append(f'{song.title} '
                                      f'{"" if song.user_duration is None else f"[{seconds_convert(song.user_duration)}]"}'
                                      f' - {song.link}')
            except ValueError:
                title = message.parts[i]
                title_found = False
                for song in songs:
                    if title.lower() in song.title.lower():
                        title_found = True
                        g.sr_download_queue.new_task(download_clip, song.link, message.author, user_duration=song.user_duration)
                        response_added.append(f'{song.title} '
                                              f'{"" if song.user_duration is None else f"[{seconds_convert(song.user_duration)}]"}'
                                              f' - {song.link}')
                    if len(response_added) >= g.sr_max_per_request:
                        break
                if not title_found:
                    target_not_found.append(title)
            if len(response_added) >= g.sr_max_per_request:
                break
        if response_added:
            if not is_mod(message.author):
                g.Main.sr_cooldowns[message.author] = time.time()
        if target_not_found:
            response.append(f"Not found: {', '.join(target_not_found)}")
        response_str = '; '.join(response)
        if len(response_str) > 470:
            response *= 0
            if response_added:
                response.append(f"Added: {len(response_added)}")
            if target_not_found:
                response.append(f"Not found: {len(target_not_found)}")
            send_message(' '.join(response))
        else:
            send_message(response_str)


@bot_command(name='srfl')
def srfl_command(message):
    try:
        if message.parts[1]:
            songs = get_srfavs_dictlist(message.author)
            if not songs:
                send_message(f'{message.author}, no favorite songs found')
                return
            target_not_found = []
            response = []
            for i in range(1, len(message.parts)):
                try:
                    index = int(message.parts[i])
                    if not 0 < index <= len(songs):
                        target_not_found.append(message.parts[i])
                        continue
                    song = songs[index - 1]
                    response.append(f'{song.title} - {song.link}')
                except ValueError:
                    title = message.parts[i]
                    title_found = False
                    for j in songs:
                        if title.lower() in j.title.lower():
                            response.append(f'{j.title} - {j.link}')
                            title_found = True
                    if not title_found:
                        target_not_found.append(title)
            if target_not_found:
                response.append(f'Not found: {", ".join(target_not_found)}')
            if response:
                response_str = ' ; '.join(response)
                if len(response_str) > 470:
                    response_arr = divide_chunks(response_str, 470, response, joinparam=' ; ')
                    for msg in response_arr:
                        send_message(msg)
                else:
                    send_message(' ; '.join(response))
    except IndexError:
        send_message(f'{message.author}, {g.prefix}srfl <word/index>')


@bot_command(name='srf')
def srf_command(message):
    songs = get_srfavs_dictlist(message.author)
    if not songs:
        send_message(f'{message.author}, no favorite songs found')
        return
    songs_arr = [f'{song.title} [{seconds_convert(song.user_duration)}] - #{count}'
                 if song.user_duration is not None else f'{song.title} - #{count}'
                 for count, song in enumerate(songs, start=1)]
    songs_str = ", ".join(songs_arr)
    songs_arr = divide_chunks(songs_str, 470, lst=songs_arr, joinparam=', ')
    send_list(message, songs_str, songs_arr, 1, "list")


@bot_command(name='sr')
def sr_command(message):
    if message.content[1:] == "sr":
        if is_mod(message.author):
            if g.sr:
                g.sr = False
                send_message(f'songrequests off')
            else:
                g.sr = True
                send_message(f'songrequests on')
        elif g.sr:
            np_command(message)
    elif sr(message.author):
        match = sr_download(message, message.parts[1], 2)
        if not match:
            if re.match(timecode_re, message.parts[-1]):
                query = ' '.join(message.parts[1:-1])
                g.sr_download_queue.new_task(download_clip, query, message.author, user_duration=message.parts[-1], ytsearch=True)
            else:
                query = ' '.join(message.parts[1:])
                g.sr_download_queue.new_task(download_clip, query, message.author, user_duration=None, ytsearch=True)


@bot_command(name='sql', check_func=is_mod)
def sql_command(message, pipe=False):
    if message.content[1:] == 'sql':
        return send_message(f'{message.author}, no query', pipe=pipe)
    result = g.db.sql_query(" ".join(message.parts[1:]))
    if result:
        result = [' - '.join(str(j) for j in i) for i in result]
        result_str = " , ".join(result)
        if pipe:
            return result_str.split()
        if len(result_str) > 480:
            result_arr = divide_chunks(result_str, 470, result, joinparam=' , ')
            for i in result_arr:
                send_message(i)
        else:
            send_message(result_str)
    elif not result and 'select' == message.parts[1].lower():
        return send_message(f'{message.author}, no results', pipe=pipe)
    elif not result:
        return send_message(f'{message.author}, done', pipe=pipe)
        


@bot_command(name='skip')
def skip_command(message):
    moderator = is_mod(message.author)
    if len(message.parts) == 1:
        if not player_good_state():
            send_message(f'{message.author}, nothing is playing')
        elif moderator or g.sr_user == message.author:
            g.Player.stop()
        else:
            send_message(f'{message.author}, cant skip others song :3')
        return
    elif not moderator and not any(message.author == i.username for i in g.playlist):
        send_message(f'{message.author}, nothing to skip in playlist')
        return
    playlist_cancelled, skip_title, skip_index, playlist_not_found, response = [], [], [], [], []
    for i in range(1, len(message.parts)):
        try:
            target = int(message.parts[i])
            if not 0 < target <= len(g.playlist):
                playlist_not_found.append(f'{target}')
                continue
            song = g.playlist[target - 1]
            if song not in skip_index + skip_title and (moderator or message.author == song.message.author):
                skip_index.append(song)
                playlist_cancelled.append(f'{song.title}'
                                          f'{"" if song.user_duration is None else f"  [{seconds_convert(song.user_duration)}]"}')
            else:
                playlist_not_found.append(f'{target}')
        except ValueError:
            song_cancelled_title = False
            target = message.parts[i]
            for song in g.playlist:
                if song not in skip_title + skip_index and target.lower() in song.title.lower() and (moderator or message.author == song.message.author):
                    playlist_cancelled.append(f'{song.title}'
                                              f'{"" if song.user_duration is None else f"  [{seconds_convert(song.user_duration)}]"}')
                    skip_title.append(song)
                    song_cancelled_title = True
            if not song_cancelled_title:
                playlist_not_found.append(target)
            for song in skip_title:
                g.playlist.remove(song)
            skip_title.clear()
    for i in skip_index:
        g.playlist.remove(i)
    if playlist_cancelled:
        response.append(f'Skip: {", ".join(playlist_cancelled)}')
    if playlist_not_found:
        response.append(f'Not found: {", ".join(playlist_not_found)}')
    if response:
        responsestr = " ".join(response)
        if len(responsestr) > 480:
            response *= 0
            if playlist_cancelled:
                response.append(f'Skip: {len(playlist_cancelled)}')
            if playlist_not_found:
                response.append(f'Not found: {len(playlist_not_found)}')
            send_message(f'{message.author}, {" ".join(response)}')
        else:
            send_message(f'{message.author}, {responsestr}')


@bot_command(name='ban', check_func=is_mod)
def ban_command(message):
    if message.content[1:] != "ban":
        g.utils_queue.new_task(ban_mod_commands, message, 'users banned', 'already banned',
                               no_ban, g.db.add_ban, True)


@bot_command(name='unban', check_func=is_mod)
def unban_command(message):
    if message.content[1:] != "unban":
        g.utils_queue.new_task(ban_mod_commands, message, 'users unbanned', f'not in the list',
                               no_ban, g.db.remove_ban, False)


@bot_command(name='mod')
def mod_command(message):
    if message.content[1:] != "mod" and message.author == g.admin:
        g.utils_queue.new_task(ban_mod_commands, message, 'users modded', 'already modded',
                               is_mod, g.db.add_mod, False)


@bot_command(name='unmod')
def unmod_command(message):
    if message.content[1:] != "unmod" and message.author == g.admin:
        g.utils_queue.new_task(ban_mod_commands, message, 'users unmodded', f'not in the list',
                               is_mod, g.db.remove_mod, True)


@bot_command(name='set')
def set_command(message):
    if message.content[1:] != "set":
        selected = message.parts[1].lower()
        if selected.endswith('.png') or selected.endswith('.gif'):
            my_file = Path("data/custom/" + selected)
            if my_file.is_file():
                call_draw('custom/', selected)
            else:
                send_message(f'{message.author}, {selected} not found ')
        else:
            send_message(f'{message.author}, names include extensions [png/gif]')


@bot_command(name='setrand')
def setrand_command(message):
    try:
        randsrc = message.parts[1]
        if not any(x == randsrc for x in ['png', 'gif', 'pixiv']):
            send_message(f'{message.author}, {g.prefix}setrand [png/gif/pixiv]')
        elif randsrc == 'gif':
            onlygif = [f for f in os.listdir('data/custom/') if f.endswith('.gif')]
            set_random_pic(onlygif, f'{message.author}, gif not found')
        elif randsrc == 'png':
            onlypng = [f for f in os.listdir('data/custom/') if f.endswith('.png')]
            set_random_pic(onlypng, f'{message.author}, png not found')
        elif randsrc == 'pixiv':
            g.px_download_queue.new_task(Pixiv.random_pixiv_art)
    except IndexError:
        onlyfiles = [f for f in os.listdir('data/custom/') if isfile(join('data/custom/', f))]
        set_random_pic(onlyfiles, f'{message.author}, {g.prefix}list is empty')


@bot_command(name='search')
def search_command(message):
    if message.content[1:] != 'search':
        words = checkifnolink('!search')
        if message.parts[1].startswith(("'", '"')) and message.parts[1].endswith(("'", '"')):
            search_words = [x for x in words if x.startswith(message.parts[1][1:-1])]
        else:
            search_words = [x for x in words if message.parts[1].lower() in x]
        str1 = ' '.join(search_words)
        allpages = divide_chunks(str1, 470)
        send_list(message, str1, allpages, 2, "search")


@bot_command(name='list')
def list_command(message):
    words, linkwords = checkifnolink('!list')
    linkstr1 = ' '.join(linkwords)
    linkallpages = divide_chunks(linkstr1, 470)
    str1 = ' '.join(words)
    allpages = divide_chunks(str1, 470)
    try:
        int(message.parts[2])
        if message.parts[0][1:] == "list" and message.parts[1] == "links":
            send_list(message, linkstr1, linkallpages, 2, "list")
    except IndexError:
        try:
            if message.parts[1] == "links":
                send_list(message, linkstr1, linkallpages, 2, "list")
                return
            send_list(message, str1, allpages, 1, "list")
        except IndexError:
            send_list(message, str1, allpages, 1, "list")


@bot_command(name='banlist', check_func=is_mod)
def banlist_command(message):
    checklist(message, g.db.check_banned)


@bot_command(name='modlist', check_func=is_mod)
def modlist_command(message):
    checklist(message, g.db.check_moderators)


@bot_command(name='link')
def link_command(message):
    if message.content[1:] == "link":
        if g.lastlink:
            send_message(f'{message.author}, {g.lastlink} - {g.last_rand_img}')
        else:
            send_message(f'nothing here')
    elif len(message.parts) > 2:
        links_filenames = [{'link': j[0], 'filename': j[1]} for j in g.db.get_links_and_filenames()]
        target_not_found = []
        response = []
        for i in message.parts[1:]:
            link = None
            for lnk in links_filenames:
                if i == lnk.get('filename'):
                    link = lnk.get('link')
                    break
            if link is None:
                target_not_found.append(i)
            else:
                response.append(f'{link} - {i}')
        if target_not_found:
            response.append(f'Not found: {", ".join(target_not_found)}')
        if response:
            response_str = ', '.join(response)
            if len(response_str) > 480:
                response_arr = divide_chunks(response_str, 470, response, joinparam=', ')
                for msg in response_arr:
                    send_message(msg)
            else:
                send_message(', '.join(response))
    else:
        filename = message.parts[1]
        link = g.db.get_link(filename)
        if link:
            send_message(f'{link[0][0]} - {filename}')
        else:
            send_message(f"{message.author}, link for {filename} not found")


@bot_command(name='save')
def save_command(message):
    if message.content[1:] == 'save':
        if re.match(regex, g.lastlink):
            message.parts.append(g.lastlink)
            message.parts.append(''.join(random.choices(
                'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10)))
            change_save_command(message, do_save_response=True)
        else:
            send_message(f'{message.author}, nothing to save')
    else:
        try:
            if message.parts[2]:
                change_save_command(message, do_save_response=True)
        except IndexError:
            message.parts.append(''.join(random.choices(
                'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10)))
            change_save_command(message, do_save_response=True)


@bot_command(name='olist')
def olist_command(message):
    result = g.db.check_ownerlist(message.author)
    result = [item[0] for item in result]
    result = " ".join(result)
    allpages = divide_chunks(result, 480)
    send_list(message, result, allpages, 1, "list")


@bot_command(name='del')
def del_command(message):
    if message.content[1:] != "del":
        g.utils_queue.new_task(del_chat_command, message)


@bot_command(name='ren')
def ren_command(message):
    if message.content[1:] != "ren":
        g.utils_queue.new_task(rename_command, message)


@bot_command(name='info')
def info_command(*args, pipe=False):
    response = f'uptime: {seconds_convert(time.time() - g.Main.start_time, explicit=True)}'
    return send_message(response, pipe=pipe)


@bot_command(name='orand')
def orand_command(message):
    result = g.db.check_ownerlist(message.author)
    try:
        if not result:
            send_message(f'{message.author}, nothing to set')
            return
        result = [item[0] for item in result]
        randsrc = message.parts[1]
        if all(randsrc != x for x in ['gif', 'png']):
            send_message(f'{message.author}, png/gif only')
        elif randsrc == 'gif':
            onlygif = [f for f in result if f.endswith('.gif')]
            set_random_pic(onlygif, f'{message.author}, gif not found')
        elif randsrc == 'png':
            onlypng = [f for f in result if f.endswith('.png')]
            set_random_pic(onlypng, f'{message.author}, png not found')
    except IndexError:
        selected = random.choice(result)
        updatelastlink(selected)
        g.last_rand_img = selected
        call_draw('custom/', selected)


@bot_command(name='help')
def help_command(message, pipe=False):
    try:
        help_command_quoted = False
        help_command = " ".join(message.parts[1:])
        command = message.parts[1]
        if command.startswith(("'", '"')) and command.endswith(("'", '"')):
            command = command[1:-1]
        if help_command.startswith(("'", '"')) and help_command.endswith(("'", '"')):
            help_command = help_command[1:-1]
            help_command_quoted = True
        if not set(command.split()).intersection(commands_list + mod_commands_list +
                                                 [i[1:] for i in commands_list] +
                                                 [i[1:] for i in mod_commands_list]):
            return send_message(f'{message.author}, unknown command', pipe=pipe)
        response = []
        if help_command_quoted:
            for i in info.commands_desc:
                if i.startswith(help_command) or i[1:].startswith(help_command):
                    response.append(i)
        else:
            for i in info.commands_desc:
                if help_command in i:
                    response.append(i)
        if response:
            response_str = ", ".join(response)
            if pipe:
                return response_str.split()
            if len(response_str) > 480:
                response_arr = divide_chunks(response_str, 470, response, joinparam=', ')
                for i in response_arr:
                    send_message(i)
            else:
                send_message(response_str)
        else:
            return send_message(f'{message.author}, no results', pipe=pipe)
    except IndexError:
        return send_message(f'Public command list: {", ".join(i[1:] for i in commands_list)}; '
                     f'Mod: {", ".join(i[1:] for i in mod_commands_list)}', pipe=pipe)


@bot_command(name='title', check_func=is_mod)
def title_command(message):
    g.utils_queue.new_task(change_stream_settings, message, 'title')


@bot_command(name='game', check_func=is_mod)
def game_command(message):
    g.utils_queue.new_task(change_stream_settings, message, 'game')


@bot_command(name='change')
def change_command(message):
    if message.content[1:] != "change":
        g.utils_queue.new_task(change_save_command, message, do_draw=True)


@bot_command(name='pipe')
def pipe_command(message):
    if message.content[1:] != "pipe":
        pipesplit = " ".join(message.parts[1:]).split(' | ')
        if len(pipesplit) < 2:
            send_message(f'{message.author}, you need at least two commands')
            return
        pipesplit = [f'{g.prefix}{i}' for i in pipesplit]
        result = pipesplit[0].split()[1:]
        pipe = True
        for i, last_item in lookahead(pipesplit):
            i = i.split()
            if last_item:
                pipe = False
                if i[0][1:] == 'tts':
                    i[0] += '_colon'
                if i[1:]:
                    for last_arg in i[:0:-1]:
                        result.insert(0, last_arg)
                    #  insert last command args to add something before piped message, example:
                    #  !notify <last_args> <piped message>
                    #  output for "!pipe uptime | notify ciremun bot uptime is:" will create notification for ciremun:
                    #  ciremun, <notify_sender>: bot uptime is: <bot_uptime> [<time> ago]
            try:
                if all(i[0][1:] != x for x in info.pipe_commands):
                    raise TypeError
                command = g.commands_dict[i[0][1:]]
                result.insert(0, i[0])  # insert command string at the beginning, so it looks like chat message
                message.parts = result
                message.content = " ".join(result)
                result = command(message, pipe=pipe)
                if not last_item:
                    if result is False:
                        send_message(f'{message.author}, {i[0][1:]} - mod command')
                        return
                    elif result is None:
                        return
            except TypeError:
                send_message(f'{message.author}, {i[0][1:]} - unsupported command')
                return
            except KeyError:
                send_message(f'{message.author}, {i[0][1:]} - unknown command')
                return


@bot_command(name='tts_colon')
def tts_colon_command(message, **kwargs):
    message.parts[0] = 'tts:'
    message.content = ' '.join(message.parts)
    call_tts.new_task(call_tts.new_message, message)


@bot_command(name='tts', check_func=is_mod)
def tts_command(message):
    try:
        if message.parts[1] == 'vc':
            call_tts.new_task(call_tts.send_set_tts_vc, message)
        elif message.parts[1] == 'vol':
            try:
                vol = float(message.parts[2])
                if not 0 <= vol <= 1:
                    send_message(f'{message.author}, volume 0-1')
                    return
                call_tts.new_task(call_tts.change_volume, vol)
            except IndexError:
                send_message(f'{message.author}, vol={call_tts.engine.getProperty("volume")}')
            except ValueError:
                send_message(f'{message.author}, error converting to float! [{message.parts[2]}]')
        elif message.parts[1] == 'rate':
            try:
                rate = int(message.parts[2])
                call_tts.new_task(call_tts.change_rate, rate)
            except IndexError:
                send_message(f'{message.author}, rate={call_tts.engine.getProperty("rate")}')
            except ValueError:
                send_message(f'{message.author}, error converting to int! [{message.parts[2]}]')
        elif message.parts[1] == 'cfg':
            send_message(f"vol={call_tts.engine.getProperty('volume')}, rate="
                         f"{call_tts.engine.getProperty('rate')}, "
                         f"vc={get_tts_vc_key(call_tts.engine.getProperty('voice'))}")
    except IndexError:
        if g.tts:
            g.tts = False
            send_message(f'tts off')
        else:
            g.tts = True
            send_message(f'tts on')


@bot_command(name='notify')
def notify_command(message, **kwargs):
    if message.content[1:] != "notify":
        if not 4 <= len(message.parts[1]) <= 25:
            send_message(f'{message.author}, message.author must be between 4 and 25 characters')
            return
        notify_message = " ".join(message.parts[2:])
        if not notify_message:
            send_message(f'{message.author}, no notify message')
            return
        g.Main.notify_list.append({'recipient': message.parts[1].lower(),
                                   'message': notify_message,
                                   'date': time.time(),
                                   'sender': message.author})


@bot_command(name='when')
def when_command(message):
    if not any(message.author == i.username for i in g.playlist):
        send_message(f'{message.author}, no queue song')
        return
    response = []
    np_end = next_song_in()
    next_in = np_end
    for count, i in enumerate(g.playlist):
        if i.username == message.author:
            if g.playlist[:count]:
                next_in += sum(
                    timecode_convert(j.duration) - j.user_duration if j.user_duration else timecode_convert(
                        j.duration) for j in g.playlist[:count]) + np_end
            response.append(f'{i.title} in {seconds_convert(next_in, explicit=True)}')
            next_in = 0
            if len(response) > 4:
                break
    if message.parts[1:]:
        response = [song for song in response if " ".join(message.parts[1:]).lower() in song.lower()]
        if not response:
            send_message(f'{message.author}, no results')
            return
    response_str = "; ".join(response)
    if len(response_str) > 470:
        response = divide_chunks(response_str, 470, lst=response, joinparam='; ')
        send_message(f'{message.author}, {response[0]}..')
        return
    send_message(f'{message.author}, {response_str}')


@bot_command(name='imgur')
def imgur_command(message):
    if not message.content[1:] == 'imgur':
        g.utils_queue.new_task(imgur_utils_wrap, message)
