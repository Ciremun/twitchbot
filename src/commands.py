import src.info as info
import src.config as g
from .qthreads import utils_queue, sr_download_queue, px_download_queue, tts_queue
from .info import commands_list, mod_commands_list
from .server import Player, TextToSpeech, set_image
from .pixiv import Pixiv
from .utils import *

commands = {}

def bot_command(*, name, check_func=no_ban):
    def decorator(func):
        def wrapper(message, **kwargs):
            if not check_func(message.author):
                return False
            return func(message, **kwargs)
        wrapper.__name__ = name
        commands[name] = wrapper
        return wrapper
    return decorator


@bot_command(name='exit')
def exit_command(message):
    if message.author == g.admin:
        for folder in g.clear_folders:
            clear_folder(folder)
        os._exit(0)


@bot_command(name='log')
def log_command(message):
    if message.author == g.admin:
        g.logs = not g.logs
        send_message(f'chat log: {g.logs}')


@bot_command(name='np')
def np_command(message):
    if not Player.active_state():
        send_message(f'{message.author}, nothing is playing')
    elif Player.state == 'State.Paused':
        np_response('Paused')
    else:
        np_response('Now playing')


@bot_command(name='srv', check_func=is_mod)
def srv_command(message):
    try:
        value = float(message.parts[1])
        if not 0 <= value <= 1:
            raise ValueError
        g.sr_volume = value
        Player.set_volume(g.sr_volume)
    except IndexError:
        send_message(f'sr vol: {g.sr_volume}')
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
    if Player.state == 'State.Playing':
        Player.pause()
    elif Player.state == 'State.Paused':
        Player.play()
    else:
        send_message(f'{message.author}, nothing is playing')


@bot_command(name='srt', check_func=is_mod)
def srt_command(message):
    if not Player.active_state():
        send_message(f'{message.author}, nothing is playing')
        return
    try:
        timecode = message.parts[1]
        if re.match(timecode_re, timecode):
            timecode = timecode[2:]
            seconds = timecode_convert(timecode)
            if seconds > timecode_convert(g.np_duration):
                send_message(f'{message.author}, time exceeds duration! [{g.np_duration}]')
            else:
                Player.set_time(seconds)
        else:
            send_message(f'{message.author}, timecode error')
    except IndexError:
        send_message(f'{message.author}, no timecode')


@bot_command(name='srfa')
def srfa_command(message):
    try:
        url_or_timecode = message.parts[1]
        if re.match(timecode_re, url_or_timecode):
            if not g.sr_url:
                send_message(f'{message.author}, nothing is playing')
                return
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
        if not Player.active_state():
            send_message(f'{message.author}, nothing is playing')
        else:
            message.parts.append(g.sr_url)
            sr_download(message, message.parts[1], 2, save=True)


@bot_command(name='srfd')
def srfd_command(message):
    if not no_args(message, 'srfd'):
        songs = get_srfavs_dictlist(message.author)
        if not songs:
            send_message(f'{message.author}, no favorite songs found')
            return
        utils_queue.new_task(sr_favs_del, message, songs)


@bot_command(name='srfp')
def srfp_command(message):
    if not no_args(message, 'srfp') and sr(message.author):
        songs = get_srfavs_dictlist(message.author)
        if not songs:
            send_message(f'{message.author}, no favorite songs found')
            return
        response, target_not_found = [], []
        response_added = 0
        for i in range(1, len(message.parts)):
            try:
                index = int(message.parts[i])
                if not 0 < index <= len(songs):
                    target_not_found.append(message.parts[i])
                    continue
                song = songs[index - 1]
                sr_download_queue.new_task(download_clip, song.link, message.author,  user_duration=song.user_duration)
                response_added += 1
            except ValueError:
                title = message.parts[i]
                title_found = False
                for song in songs:
                    if title.lower() in song.title.lower():
                        title_found = True
                        sr_download_queue.new_task(download_clip, song.link, message.author, user_duration=song.user_duration)
                        response_added += 1
                    if response_added >= g.sr_max_songs_per_request:
                        break
                if not title_found:
                    target_not_found.append(title)
            if response_added >= g.sr_max_songs_per_request:
                break
        if response_added:
            if not is_mod(message.author):
                g.sr_cooldowns[message.author] = time.time()
        if target_not_found:
            response.append(f"Not found: {', '.join(target_not_found)}")
            response_str = '; '.join(response)
            if len(response_str) > 470:
                response *= 0
                if target_not_found:
                    response.append(f"Not found: {len(target_not_found)}")
                return send_message(' '.join(response))
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
    if no_args(message, 'sr'):
        if is_mod(message.author):
            g.sr = not g.sr
            send_message(f'sr: {g.sr}')
        elif g.sr:
            np_command(message)
    elif sr(message.author):
        match = sr_download(message, message.parts[1], 2)
        if not match:
            if re.match(timecode_re, message.parts[-1]):
                query = ' '.join(message.parts[1:-1])
                sr_download_queue.new_task(download_clip, query, message.author, 
                                                user_duration=timecode_re.sub(r'\2', message.parts[-1]), ytsearch=True)
            else:
                query = ' '.join(message.parts[1:])
                sr_download_queue.new_task(download_clip, query, message.author, user_duration=None, ytsearch=True)


@bot_command(name='sql', check_func=is_mod)
def sql_command(message, pipe=False):
    if no_args(message, 'sql'):
        return send_message(f'{message.author}, no query', pipe=pipe)
    result = db.sql_query(" ".join(message.parts[1:]))
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
        if not Player.active_state():
            send_message(f'{message.author}, nothing is playing')
        elif moderator or g.sr_user == message.author:
            Player.stop()
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
            if song not in skip_index + skip_title and (moderator or message.author == song.username):
                skip_index.append(song)
                playlist_cancelled.append(f'{song.title}'
                                          f'{"" if song.user_duration is None else f"  [{seconds_convert(song.user_duration)}]"}')
            else:
                playlist_not_found.append(f'{target}')
        except ValueError:
            song_cancelled_title = False
            target = message.parts[i]
            for song in g.playlist:
                if song not in skip_title + skip_index and target.lower() in song.title.lower() and (moderator or message.author == song.username):
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
    if not no_args(message, 'ban'):
        utils_queue.new_task(ban_mod_commands, message, 'users banned', 'already banned',
                               no_ban, db.add_ban, True)


@bot_command(name='unban', check_func=is_mod)
def unban_command(message):
    if not no_args(message, 'unban'):
        utils_queue.new_task(ban_mod_commands, message, 'users unbanned', f'not in the list',
                               no_ban, db.remove_ban, False)


@bot_command(name='mod')
def mod_command(message):
    if not no_args(message, 'mod') and message.author == g.admin:
        utils_queue.new_task(ban_mod_commands, message, 'users modded', 'already modded',
                               is_mod, db.add_mod, False)


@bot_command(name='unmod')
def unmod_command(message):
    if not no_args(message, 'unmod') and message.author == g.admin:
        utils_queue.new_task(ban_mod_commands, message, 'users unmodded', f'not in the list',
                               is_mod, db.remove_mod, True)


@bot_command(name='set')
def set_command(message):
    if not no_args(message, 'set'):
        selected = message.parts[1].lower()
        if selected.endswith('.png') or selected.endswith('.gif'):
            my_file = Path("flask/images/user/" + selected)
            if my_file.is_file():
                set_image('user/', selected)
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
            onlygif = [f for f in os.listdir('flask/images/user/') if f.endswith('.gif')]
            set_random_pic(onlygif, f'{message.author}, gif not found')
        elif randsrc == 'png':
            onlypng = [f for f in os.listdir('flask/images/user/') if f.endswith('.png')]
            set_random_pic(onlypng, f'{message.author}, png not found')
        elif randsrc == 'pixiv':
            px_download_queue.new_task(Pixiv.random_pixiv_art)
    except IndexError:
        onlyfiles = [f for f in os.listdir('flask/images/user/') if isfile(join('flask/images/user/', f))]
        set_random_pic(onlyfiles, f'{message.author}, {g.prefix}list is empty')


@bot_command(name='search')
def search_command(message):
    if not no_args(message, 'search'):
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
        if message.parts[0][g.prefix_len:] == "list" and message.parts[1] == "links":
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
    checklist(message, db.check_banned)


@bot_command(name='modlist', check_func=is_mod)
def modlist_command(message):
    checklist(message, db.check_moderators)


@bot_command(name='link')
def link_command(message):
    if no_args(message, 'link'):
        if not g.last_rand_img:
            send_message(f'{message.author}, nothing here')
            return
        link = db.get_link(g.last_rand_img)
        response = f'{link[0][0]} - {g.last_rand_img}' if link else f'{g.last_link} - {g.last_rand_img}' if g.last_link else f'no link for {g.last_rand_img}'
        send_message(f'{message.author}, {response}')
    elif len(message.parts) > 2:
        links_filenames = [{'link': j[0], 'filename': j[1]} for j in db.get_links_and_filenames()]
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
        link = db.get_link(filename)
        if link:
            send_message(f'{link[0][0]} - {filename}')
        else:
            send_message(f"{message.author}, link for {filename} not found")


@bot_command(name='save')
def save_command(message):
    if no_args(message, 'save'):
        if re.match(link_re, g.last_link):
            message.parts.append(g.last_link)
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
    result = db.check_ownerlist(message.author)
    result = [item[0] for item in result]
    result = " ".join(result)
    allpages = divide_chunks(result, 480)
    send_list(message, result, allpages, 1, "list")


@bot_command(name='del')
def del_command(message):
    if not no_args(message, 'del'):
        utils_queue.new_task(del_chat_command, message)


@bot_command(name='ren')
def ren_command(message):
    if not no_args(message, 'ren'):
        utils_queue.new_task(rename_command, message)


@bot_command(name='info')
def info_command(*args, pipe=False):
    response = f'uptime: {seconds_convert(time.time() - g.start_time, explicit=True)}'
    return send_message(response, pipe=pipe)


@bot_command(name='orand')
def orand_command(message):
    result = db.check_ownerlist(message.author)
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
        g.last_rand_img = selected
        g.last_link = ''
        link = db.get_link(selected)
        if link:
            g.last_link = link[0][0]
        set_image('user/', selected)


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
                                                 [i[g.prefix_len:] for i in commands_list] +
                                                 [i[g.prefix_len:] for i in mod_commands_list]):
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
        return send_message(f'Public command list: {", ".join(i[g.prefix_len:] for i in commands_list)}; '
                     f'Mod: {", ".join(i[g.prefix_len:] for i in mod_commands_list)}', pipe=pipe)


@bot_command(name='title', check_func=is_mod)
def title_command(message):
    utils_queue.new_task(change_stream_settings, message, 'title')


@bot_command(name='game', check_func=is_mod)
def game_command(message):
    utils_queue.new_task(change_stream_settings, message, 'game')


@bot_command(name='change')
def change_command(message):
    if not no_args(message, 'change'):
        utils_queue.new_task(change_save_command, message, do_draw=True)


def pipe_command(message):
    if not no_args(message, 'pipe'):
        message.parts[0] = message.parts[0][g.prefix_len:]
        pipesplit = " ".join(message.parts).split(' | ')
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
                if i[1:]:
                    for last_arg in i[:0:-1]:
                        result.insert(0, last_arg)
            try:
                if all(i[0][g.prefix_len:] != x for x in info.pipe_commands):
                    raise TypeError
                command = commands[i[0][g.prefix_len:]]
                result.insert(0, i[0])
                message.parts = result
                message.content = " ".join(result)
                result = command(message, pipe=pipe)
                if not last_item:
                    if result is False:
                        send_message(f'{message.author}, {i[0][g.prefix_len:]} - mod command')
                        return
                    elif result is None:
                        return
            except TypeError:
                send_message(f'{message.author}, {i[0][g.prefix_len:]} - unsupported command')
                return
            except KeyError:
                send_message(f'{message.author}, {i[0][g.prefix_len:]} - unknown command')
                return


@bot_command(name='tts')
def tts_command(message, **kwargs):
    if g.tts:
        if not no_args(message, 'tts'):
            del message.parts[0]
            tts_queue.new_task(TextToSpeech.say_message, message.parts)
            return
        tts_queue.new_task(TextToSpeech.get_set_tts_voice, message)

@bot_command(name='ttscfg', check_func=is_mod)
def ttscfg_command(message):
    try:
        if message.parts[1] == 'vc':
            tts_queue.new_task(TextToSpeech.get_set_tts_voice, message)
        elif message.parts[1] == 'vol':
            try:
                vol = float(message.parts[2])
                if not 0 <= vol <= 1:
                    send_message(f'{message.author}, volume 0-1')
                    return
                TextToSpeech.set_attr('tts_volume', vol)
            except IndexError:
                TextToSpeech.get_attr('tts_volume')
            except ValueError:
                send_message(f'{message.author}, error converting to float! [{message.parts[2]}]')
        elif message.parts[1] == 'rate':
            try:
                rate = float(message.parts[2])
                TextToSpeech.set_attr('tts_rate', rate)
            except IndexError:
                TextToSpeech.get_attr('tts_rate')
            except ValueError:
                send_message(f'{message.author}, error converting to float! [{message.parts[2]}]')
        elif message.parts[1] == 'toggle':
            g.tts = not g.tts
            send_message(f'tts: {g.tts}')
    except IndexError:
        TextToSpeech.get_cfg()


@bot_command(name='notify')
def notify_command(message, **kwargs):
    if not no_args(message, 'notify'):
        if not 4 <= len(message.parts[1]) <= 25:
            send_message(f'{message.author}, message.author must be between 4 and 25 characters')
            return
        notify_message = " ".join(message.parts[2:])
        if not notify_message:
            send_message(f'{message.author}, no notify message')
            return
        g.notify_list.append({'recipient': message.parts[1].lower(),
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
    if not no_args(message, 'imgur'):
        utils_queue.new_task(imgur_utils_wrap, message)
