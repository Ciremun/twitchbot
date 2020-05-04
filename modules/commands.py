import asyncio
import modules.main
import modules.decorators
import modules.info as info

from modules.utils import *
from modules.regex import *
from modules.pixiv import Pixiv
from modules.tts import call_tts
from modules.decorators import bot_command, moderator_command
from modules.info import commands_list, mod_commands_list


@moderator_command
def die_command(**kwargs):
    call_draw('data/special/', 'greenscreen.png')


@bot_command
def exit_command(*, username, message, **kwargs):
    if message[1:] == "exit" and username == g.admin:
        for folder in g.clear_folders:
            clear_folder(folder)
        result = g.db.get_srfavs_filenames()
        result = [item[0] for item in result]
        favorites = [f for f in os.listdir('data/sounds/favs/') if isfile(join('data/sounds/favs/', f))]
        for f in favorites:
            try:
                if not set(f.split()).intersection(result):
                    os.remove(os.path.join('data/sounds/favs/', f))
            except:
                pass
        os._exit(0)


@bot_command
def log_command(*, username, **kwargs):
    if username == g.admin:
        if g.logs:
            g.logs = False
            send_message('logs off')
        else:
            g.logs = True
            send_message('logs on')


@bot_command
def np_command(*, username, **kwargs):
    if not player_good_state():
        send_message(f'{username}, nothing is playing')
    elif str(g.Player.get_state()) == 'State.Paused':
        np_response('Paused')
    else:
        np_response('Now playing')


@moderator_command
def srv_command(*, username, messagesplit, **kwargs):
    try:
        value = int(messagesplit[1])
        if not 0 <= value <= 100:
            raise ValueError
        if player_good_state():
            g.player_last_vol = value
            g.Player.audio_set_volume(g.player_last_vol)
            return
        send_message(f'{username}, nothing is playing')
    except IndexError:
        send_message(f'{g.prefix}sr vol={g.player_last_vol}')
    except ValueError:
        send_message(f'{username}, vol 0-100')


@bot_command
def srq_command(*, username, messagesplit, **kwargs):
    if g.sr:
        sr_get_list(username, messagesplit)


@moderator_command
def srs_command(*, username, messagesplit, **kwargs):
    if len(messagesplit) == 1:
        if not player_good_state():
            send_message(f'{username}, nothing is playing')
        else:
            g.Player.stop()
        return
    if not g.playlist:
        send_message(f'{username}, playlist is empty')
        return
    skipped_response, skip_title, skip_index, user_response, target_not_found = [], [], [], [], []
    for i in range(1, len(messagesplit)):
        try:
            target = int(messagesplit[i])
            if not 0 < target <= len(g.playlist):
                target_not_found.append(f'{target}')
                continue
            song = g.playlist[target - 1]
            skip_index.append(song)
            skipped_response.append(
                f'{song.title}'
                f'{"" if song.user_duration is None else f" [{seconds_convert(song.user_duration)}]"}')
        except ValueError:
            target = messagesplit[i]
            title_skipped = False
            for song in g.playlist:
                if song not in skip_index and target.lower() in song.title.lower():
                    skip_title.append(song)
                    skipped_response.append(
                        f'{song.title}'
                        f'{"" if song.user_duration is None else f" [{seconds_convert(song.user_duration)}]"}')
                    title_skipped = True
            if not title_skipped:
                target_not_found.append(target)
            for song in skip_title:
                g.playlist.remove(song)
            skip_title.clear()
    for song in skip_index:
        g.playlist.remove(song)
    if skipped_response:
        user_response.append(f'Skip: {", ".join(skipped_response)}')
    if target_not_found:
        user_response.append(f'Not found: {", ".join(target_not_found)}')
    if user_response:
        user_response_str = "; ".join(user_response)
        if len(user_response_str) > 470:
            user_response *= 0
            if skipped_response:
                user_response.append(f'Skip: {len(skipped_response)}')
            if target_not_found:
                user_response.append(f'Not found: {len(target_not_found)}')
            send_message(f'{username}, {"; ".join(user_response)}')
        else:
            send_message(user_response_str)


@moderator_command
def src_command(*, username, **kwargs):
    if not g.playlist:
        send_message(f'{username} playlist is empty')
        return
    g.playlist.clear()
    send_message(f'queue wiped')


@moderator_command
def srp_command(*, username, **kwargs):
    if str(g.Player.get_state()) == 'State.Playing':
        g.Player.pause()
    elif str(g.Player.get_state()) == 'State.Paused':
        g.Player.play()
    else:
        send_message(f'{username}, nothing is playing')


@moderator_command
def srt_command(*, username, messagesplit, **kwargs):
    if not player_good_state():
        send_message(f'{username}, nothing is playing')
        return
    try:
        timecode = messagesplit[1]
        if re.match(timecode_re, timecode):
            seconds = timecode_convert(timecode)
            if seconds > timecode_convert(g.np_duration):
                send_message(f'{username}, time exceeds duration! [{g.np_duration}]')
            else:
                g.Player.set_time(seconds * 1000)
        else:
            send_message(f'{username}, timecode error')
    except IndexError:
        send_message(f'{username}, no timecode')


@bot_command
def srfa_command(*, username, messagesplit, **kwargs):
    if not sr_user_cooldown(username):
        try:
            url_or_timecode = messagesplit[1]
            if re.match(timecode_re, url_or_timecode):
                messagesplit.append(url_or_timecode)
                messagesplit[1] = g.sr_url
                sr_download(messagesplit, username, 'data/sounds/favs/', timecode_pos=2)
                return
            match = sr_download(messagesplit, username, 'data/sounds/favs/',
                                link_pos=1, timecode_pos=2)
            if not match:
                timecode_pos = None
                if re.match(timecode_re, messagesplit[-1]):
                    timecode_pos = len(messagesplit) - 1
                    messagesplit[1] = ' '.join(messagesplit[1:-1])
                else:
                    messagesplit[1] = ' '.join(messagesplit[1:])
                try_timecode(messagesplit[1], messagesplit, username,
                             timecode_pos=timecode_pos,
                             folder='data/sounds/favs/', ytsearch=True)
        except IndexError:
            if not player_good_state():
                send_message(f'{username}, nothing is playing')
            else:
                messagesplit.append(g.sr_url)
                sr_download(messagesplit, username, 'data/sounds/favs/', timecode_pos=3)


@bot_command
def srfd_command(*, username, messagesplit, **kwargs):
    try:
        if messagesplit[1]:
            songs = get_srfavs_dictlist(username)
            if not songs:
                send_message(f'{username}, no favorite songs found')
                return
            asyncio.run(sr_favs_del(username, messagesplit, songs))
    except IndexError:
        send_message(f'{username}, {g.prefix}srfd <index1> <index2>..')


@bot_command
def srfp_command(*, username, messagesplit, **kwargs):
    if sr(username):
        try:
            if messagesplit[1]:
                songs = get_srfavs_dictlist(username)
                if not songs:
                    send_message(f'{username}, no favorite songs found')
                    return
                response, target_not_found, response_added = [], [], []
                for i in range(1, len(messagesplit)):
                    try:
                        index = int(messagesplit[i])
                        if not 0 < index <= len(songs):
                            target_not_found.append(messagesplit[i])
                            continue
                        song = songs[index - 1]
                        g.playlist.append(song)
                        g.sr_queue.new_task(playmusic)
                        if song.user_duration is not None:
                            response_added.append(f'{song.title} '
                                                  f'[{seconds_convert(song.user_duration)}]'
                                                  f' - {song.link} - #{len(g.playlist)}')
                        else:
                            response_added.append(f'{song.title} - '
                                                  f'{song.link} - #{len(g.playlist)}')
                    except ValueError:
                        title = messagesplit[i]
                        title_found = False
                        for j in songs:
                            if title.lower() in j.title.lower():
                                g.playlist.append(j)
                                title_found = True
                                g.sr_queue.new_task(playmusic)
                                if j.user_duration is not None:
                                    response_added.append(f'{j.title} '
                                                          f'[{seconds_convert(j.user_duration)}]'
                                                          f' - '
                                                          f'{j.link} - #{len(g.playlist)}')
                                else:
                                    response_added.append(f'{j.title} - {j.link} - '
                                                          f'#{len(g.playlist)}')
                            if len(response_added) >= g.sr_max_per_request:
                                break
                        if not title_found:
                            target_not_found.append(title)
                    if len(response_added) >= g.sr_max_per_request:
                        break
                if response_added:
                    if not checkmodlist(username):
                        g.Main.sr_cooldowns[username] = time.time()
                    response.append(f"+ {'; '.join(response_added)}")
                if target_not_found:
                    response.append(f"Not found: {', '.join(target_not_found)}")
                if response:
                    response_str = ' '.join(response)
                    if len(response_str) > 470:
                        response *= 0
                        if response_added:
                            response.append(f"Added: {len(response_added)}")
                        if target_not_found:
                            response.append(f"Not found: {len(target_not_found)}")
                        send_message(' '.join(response))
                    else:
                        send_message(response_str)
        except IndexError:
            send_message(f'{username}, {g.prefix}srfp <word/index>')


@bot_command
def srfl_command(*, username, messagesplit, **kwargs):
    try:
        if messagesplit[1]:
            songs = get_srfavs_dictlist(username)
            if not songs:
                send_message(f'{username}, no favorite songs found')
                return
            target_not_found = []
            response = []
            for i in range(1, len(messagesplit)):
                try:
                    index = int(messagesplit[i])
                    if not 0 < index <= len(songs):
                        target_not_found.append(messagesplit[i])
                        continue
                    song = songs[index - 1]
                    response.append(f'{song.title} - {song.link}')
                except ValueError:
                    title = messagesplit[i]
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
        send_message(f'{username}, {g.prefix}srfl <word/index>')


@bot_command
def srf_command(*, username, messagesplit, **kwargs):
    songs = get_srfavs_dictlist(username)
    if not songs:
        send_message(f'{username}, no favorite songs found')
        return
    songs_arr = [f'{song.title} [{seconds_convert(song.user_duration)}] - #{count}'
                 if song.user_duration is not None else f'{song.title} - #{count}'
                 for count, song in enumerate(songs, start=1)]
    songs_str = ", ".join(songs_arr)
    songs_arr = divide_chunks(songs_str, 470, lst=songs_arr, joinparam=', ')
    send_list(username, messagesplit, songs_str, songs_arr, 1, "list")


@bot_command
def sr_command(*, username, messagesplit, message):
    if message == f"{g.prefix}sr":
        if checkmodlist(username):
            if g.sr:
                g.sr = False
                send_message(f'{g.prefix}sr off')
            else:
                g.sr = True
                send_message(f'{g.prefix}sr on')
        elif g.sr:
            np_command(username=username, messagesplit=messagesplit, message=message)
    elif sr(username):
        match = sr_download(messagesplit, username, timecode_pos=2)
        if not match:
            if re.match(timecode_re, messagesplit[-1]):
                query = ' '.join(messagesplit[1:-1])
                g.sr_download_queue.new_task(download_clip, query, username, user_duration=messagesplit[-1],
                                             ytsearch=True)
            else:
                query = ' '.join(messagesplit[1:])
                g.sr_download_queue.new_task(download_clip, query, username, user_duration=None, ytsearch=True)


@moderator_command
def sql_command(*, username, messagesplit, pipe=False, **kwargs):
    try:
        if not messagesplit[1]:
            raise IndexError
        result = g.db.sql_query(" ".join(messagesplit[1:]))
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
        elif not result and 'select' == messagesplit[1].lower():
            if pipe:
                return f'{username}, no results'.split()
            send_message(f'{username}, no results')
        elif not result:
            if pipe:
                return f'{username}, done'.split()
            send_message(f'{username}, done')
    except IndexError:
        if pipe:
            return f'{username}, no query'.split()
        send_message(f'{username}, no query')


@bot_command
def cancel_command(*, username, messagesplit, **kwargs):
    if not any(username == i.username for i in g.playlist):
        send_message(f'{username}, nothing to cancel')
        return
    if len(messagesplit) == 1:
        for song in g.playlist:
            if username == song.username:
                g.playlist.remove(song)
                send_message(f'{username}, Cancelled: {song.title}'
                             f'{"" if song.user_duration is None else f" [{seconds_convert(song.user_duration)}]"}')
                return
    playlist_cancelled, playlist_to_del, playlist_not_found, response = [], [], [], []
    for i in range(1, len(messagesplit)):
        song_cancelled_title = False
        try:
            target = int(messagesplit[i])
            if not 0 < target <= len(g.playlist):
                playlist_not_found.append(f'{target}')
                continue
            song = g.playlist[target - 1]
            if username == song.username and song not in playlist_to_del:
                playlist_to_del.append(song)
                if song.user_duration is not None:
                    playlist_cancelled.append(f'{song.title} [{seconds_convert(song.user_duration)}]')
                else:
                    playlist_cancelled.append(song.title)
        except ValueError:
            target = messagesplit[i]
            for song in g.playlist:
                if username == song.username and song not in playlist_to_del and target.lower() in song.title.lower():
                    if song.user_duration is not None:
                        playlist_cancelled.append(f'{song.title} [{seconds_convert(song.user_duration)}]')
                    else:
                        playlist_cancelled.append(song.title)
                    playlist_to_del.append(song)
                    song_cancelled_title = True
            if not song_cancelled_title:
                playlist_not_found.append(target)
    for i in playlist_to_del:
        g.playlist.remove(i)
    if playlist_cancelled:
        response.append(f'Cancelled: {", ".join(playlist_cancelled)}')
    if playlist_not_found:
        response.append(f'Not found: {", ".join(playlist_not_found)}')
    if response:
        responsestr = " ".join(response)
        if len(responsestr) > 480:
            response *= 0
            if playlist_cancelled:
                response.append(f'Cancelled: {len(playlist_cancelled)}')
            if playlist_not_found:
                response.append(f'Not found: {len(playlist_not_found)}')
            send_message(f'{username}, {" ".join(response)}')
        else:
            send_message(f'{username}, {responsestr}')


@moderator_command
def ban_command(*, username, messagesplit, message):
    if message != f"{g.prefix}ban":
        asyncio.run(ban_mod_commands(username, messagesplit, 'users banned', 'already banned',
                                     checkbanlist, g.db.add_ban, True))


@moderator_command
def unban_command(*, username, messagesplit, message):
    if message != f"{g.prefix}unban":
        asyncio.run(ban_mod_commands(username, messagesplit,
                                     'users unbanned', f'not in the list',
                                     checkbanlist, g.db.remove_ban, False))


@bot_command
def mod_command(*, username, messagesplit, message):
    if message != f"{g.prefix}mod" and username == g.admin:
        asyncio.run(ban_mod_commands(username, messagesplit, 'users modded', 'already modded',
                                     checkmodlist, g.db.add_mod, True))


@bot_command
def unmod_command(*, username, messagesplit, message):
    if message != f"{g.prefix}unmod" and username == g.admin:
        asyncio.run(ban_mod_commands(username, messagesplit,
                                     'users unmodded', f'not in the list',
                                     checkmodlist, g.db.remove_mod, False))


@bot_command
def set_command(*, username, messagesplit, message):
    if message != f"{g.prefix}set":
        selected = messagesplit[1].lower()
        if selected.endswith('.png') or selected.endswith('.gif'):
            my_file = Path("data/custom/" + selected)
            if my_file.is_file():
                call_draw('data/custom/', selected)
            else:
                send_message(f'{username}, {selected} not found ')
        else:
            send_message('{}, names include extensions [png/gif]'.format(username))


@bot_command
def setrand_command(*, username, messagesplit, **kwargs):
    try:
        randsrc = messagesplit[1]
        if not any(x == randsrc for x in ['png', 'gif', 'pixiv']):
            send_message(f'{username}, {g.prefix}setrand [png/gif/pixiv]')
        elif randsrc == 'gif':
            onlygif = [f for f in os.listdir('data/custom/') if f.endswith('.gif')]
            set_random_pic(onlygif, f'{username}, gif not found')
        elif randsrc == 'png':
            onlypng = [f for f in os.listdir('data/custom/') if f.endswith('.png')]
            set_random_pic(onlypng, f'{username}, png not found')
        elif randsrc == 'pixiv':
            g.px_download_queue.new_task(Pixiv.random_pixiv_art)
    except IndexError:
        onlyfiles = [f for f in os.listdir('data/custom/') if isfile(join('data/custom/', f))]
        set_random_pic(onlyfiles, f'{username}, {g.prefix}list is empty')


@bot_command
def search_command(*, username, messagesplit, message):
    if message != f'{g.prefix}search':
        words = checkifnolink('!search')
        if messagesplit[1].startswith(("'", '"')) and messagesplit[1].endswith(("'", '"')):
            search_words = [x for x in words if x.startswith(messagesplit[1][1:-1])]
        else:
            search_words = [x for x in words if messagesplit[1].lower() in x]
        str1 = ' '.join(search_words)
        allpages = divide_chunks(str1, 470)
        send_list(username, messagesplit, str1, allpages, 2, "search")


@bot_command
def list_command(*, username, messagesplit, **kwargs):
    words, linkwords = checkifnolink('!list')
    linkstr1 = ' '.join(linkwords)
    linkallpages = divide_chunks(linkstr1, 470)
    str1 = ' '.join(words)
    allpages = divide_chunks(str1, 470)
    try:
        int(messagesplit[2])
        if messagesplit[0][1:] == "list" and messagesplit[1] == "links":
            send_list(username, messagesplit, linkstr1, linkallpages, 2, "list")
    except IndexError:
        try:
            if messagesplit[1] == "links":
                send_list(username, messagesplit, linkstr1, linkallpages, 2, "list")
                return
            send_list(username, messagesplit, str1, allpages, 1, "list")
        except IndexError:
            send_list(username, messagesplit, str1, allpages, 1, "list")


@moderator_command
def banlist_command(*, username, messagesplit, **kwargs):
    checklist(username, messagesplit, g.db.check_banned)


@moderator_command
def modlist_command(*, username, messagesplit, **kwargs):
    checklist(username, messagesplit, g.db.check_moderators)


@bot_command
def link_command(*, username, messagesplit, message):
    if message == f"{g.prefix}link":
        if g.lastlink:
            send_message('{}, {} - {}'.format(username, g.lastlink, g.last_rand_img))
        else:
            send_message(f'nothing here')
    elif len(messagesplit) > 2:
        links_filenames = [{'link': j[0], 'filename': j[1]} for j in g.db.get_links_and_filenames()]
        target_not_found = []
        response = []
        for i in messagesplit[1:]:
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
        link = g.db.get_link(messagesplit[1])
        if link:
            send_message(f'{" , ".join([i[0] for i in link])} - {messagesplit[1]}')
        else:
            send_message(f"{username}, {messagesplit[1]} not found")


@bot_command
def save_command(*, username, messagesplit, message):
    if message == f'{g.prefix}save':
        if re.match(regex, g.lastlink):
            messagesplit.append(g.lastlink)
            messagesplit.append(''.join(random.choices(
                'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10)))
            change_save_command(username, messagesplit, do_save_response=True)
        else:
            send_message(f'{username}, nothing to save')
    else:
        try:
            if messagesplit[2]:
                change_save_command(username, messagesplit, do_save_response=True)
        except IndexError:
            messagesplit.append(''.join(random.choices(
                'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10)))
            change_save_command(username, messagesplit, do_save_response=True)


@bot_command
def olist_command(*, username, messagesplit, **kwargs):
    owner_list(username, messagesplit)


@bot_command
def del_command(*, username, messagesplit, message):
    if message != f"{g.prefix}del":
        asyncio.run(del_chat_command(username, messagesplit))


@bot_command
def ren_command(*, username, messagesplit, message):
    if message != f"{g.prefix}ren":
        asyncio.run(rename_command(username, messagesplit))


@bot_command
def info_command(pipe=False, **kwargs):
    response = f'uptime: {seconds_convert(time.time() - modules.main.startTime, explicit=True)}'
    if pipe:
        return response.split()
    send_message(response)


@bot_command
def orand_command(*, username, messagesplit, **kwargs):
    result = g.db.check_ownerlist(username)
    try:
        if not result:
            send_message(f'{username}, nothing to set')
            return
        result = [item[0] for item in result]
        randsrc = messagesplit[1]
        if all(randsrc != x for x in ['gif', 'png']):
            send_message(f'{username}, png/gif only')
        elif randsrc == 'gif':
            onlygif = [f for f in result if f.endswith('.gif')]
            set_random_pic(onlygif, f'{username}, gif not found')
        elif randsrc == 'png':
            onlypng = [f for f in result if f.endswith('.png')]
            set_random_pic(onlypng, f'{username}, png not found')
    except IndexError:
        selected = random.choice(result)
        updatelastlink(selected)
        g.last_rand_img = selected
        call_draw('data/custom/', selected)


@bot_command
def help_command(*, username, messagesplit, pipe=False, **kwargs):
    try:
        help_command_quoted = False
        help_command = " ".join(messagesplit[1:])
        command = messagesplit[1]
        if command.startswith(("'", '"')) and command.endswith(("'", '"')):
            command = command[1:-1]
        if help_command.startswith(("'", '"')) and help_command.endswith(("'", '"')):
            help_command = help_command[1:-1]
            help_command_quoted = True
        if not set(command.split()).intersection(commands_list + mod_commands_list +
                                                 [i[1:] for i in commands_list] +
                                                 [i[1:] for i in mod_commands_list]):
            if pipe:
                return f'{username}, unknown command'.split()
            send_message(f'{username}, unknown command')
            return
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
            if pipe:
                return f'{username}, no results'.split()
            send_message(f'{username}, no results')
    except IndexError:
        if pipe:
            return f'Public command list: {", ".join(i[1:] for i in commands_list)} ; ' \
                   f'Mod: {", ".join(i[1:] for i in mod_commands_list)}'.split()
        send_message(f'Public command list: {", ".join(i[1:] for i in commands_list)} ; '
                     f'Mod: {", ".join(i[1:] for i in mod_commands_list)}')


@moderator_command
def title_command(*, username, messagesplit, **kwargs):
    asyncio.run(change_stream_settings(username, messagesplit, 'title'))


@moderator_command
def game_command(*, username, messagesplit, **kwargs):
    asyncio.run(change_stream_settings(username, messagesplit, 'game'))


@bot_command
def change_command(*, username, messagesplit, message):
    if message != f"{g.prefix}change":
        change_save_command(username, messagesplit, do_draw=True)


@bot_command
def pipe_command(*, username, messagesplit, message):
    if message != f"{g.prefix}pipe":
        pipesplit = " ".join(messagesplit[1:]).split(' | ')
        if len(pipesplit) < 2:
            send_message(f'{username}, you need at least two commands')
            return
        pipesplit = [f'{g.prefix}{i}' for i in pipesplit]
        result = pipesplit[0].split()[1:]

        def lookahead(iterable):
            """Pass through all values from the given iterable, augmented by the
            information if there are more values to come after the current one
            (True), or if it is the last value (False).
            """
            it = iter(iterable)
            last = next(it)
            for val in it:
                yield last, False
                last = val
            yield last, True

        pipe = True
        for i, last_item in lookahead(pipesplit):
            i = i.split()
            if last_item:
                pipe = False
                if i[0][1:] == 'tts':
                    i[0] += '_colon'
                if i[1:]:
                    result.insert(0, " ".join(i[1:]))
                    #  insert last command args to specify users, append to tts
            try:
                if all(i[0][1:] != x for x in info.pipe_commands):
                    raise TypeError
                command = g.commands_dict[i[0][1:]]
                result.insert(0, i[0])  # insert command string at the beginning, so it looks like chat message
                result = command(username=username, messagesplit=result, message=" ".join(result), pipe=pipe)
                if result is None and not last_item:
                    send_message(f'{username}, {i[0][1:]} - mod command')
                    return
            except TypeError:
                send_message(f'{username}, {i[0][1:]} - unsupported command')
                return
            except KeyError:
                send_message(f'{username}, {i[0][1:]} - unknown command')
                return


@bot_command
def tts_colon_command(*, username, messagesplit, **kwargs):
    messagesplit[0] = 'tts:'
    call_tts.temper.append([" ".join(messagesplit), username])


@moderator_command
def tts_command(*, username, messagesplit, **kwargs):
    try:
        if messagesplit[1] == 'vc':
            call_tts.send_set_tts_vc(username, messagesplit)
        elif messagesplit[1] == 'vol':
            try:
                call_tts.engine.setProperty('volume', float(messagesplit[2]))
                send_message('{}, vol={}'.format(username, float(messagesplit[2])))
            except IndexError:
                send_message('{}, vol={}'.format(username, call_tts.engine.getProperty('volume')))
        elif messagesplit[1] == 'rate':
            try:
                call_tts.engine.setProperty('rate', int(messagesplit[2]))
                send_message('{}, rate={}'.format(username, float(messagesplit[2])))
            except IndexError:
                send_message('{}, rate={}'.format(username, call_tts.engine.getProperty('rate')))
        elif messagesplit[1] == 'cfg':
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


@bot_command
def notify_command(*, username, messagesplit, message, **kwargs):
    if message != f"{g.prefix}notify":
        if not 4 <= len(messagesplit[1]) <= 25:
            send_message(f'{username}, username must be between 4 and 25 characters')
            return
        notify_message = " ".join(messagesplit[2:])
        if not notify_message:
            send_message(f'{username}, no notify message')
            return
        g.Main.notify_list.append({'recipient': messagesplit[1].lower(),
                                   'message': notify_message,
                                   'date': time.time(),
                                   'sender': username})


@bot_command
def when_command(*, username, messagesplit, **kwargs):
    if not any(username == i.username for i in g.playlist):
        send_message(f'{username}, no queue song')
        return
    next_in = 0
    np_end = 0
    response = []
    if player_good_state():
        current_time_ms = g.Player.get_time()
        current_time = floor(current_time_ms / 1000)
        np_duration = timecode_convert(g.np_duration)
        np_end = np_duration - current_time
        next_in = np_end
    for count, i in enumerate(g.playlist):
        if i.username == username:
            if g.playlist[:count]:
                next_in += sum(
                    timecode_convert(j.duration) - j.user_duration if j.user_duration else timecode_convert(
                        j.duration) for j in g.playlist[:count]) + np_end
            response.append(f'{i.title} in ({seconds_convert(next_in, explicit=True)})')
            next_in = 0
            if len(response) > 4:
                break
    if messagesplit[1:]:
        response = [song for song in response if " ".join(messagesplit[1:]).lower() in song.lower()]
        if not response:
            send_message(f'{username}, no results')
            return
    response_str = ", ".join(response)
    if len(response_str) > 470:
        response = divide_chunks(response_str, 470, lst=response, joinparam='; ')
        send_message(f'{username}, {response[0]}..')
        return
    send_message(f'{username}, {response_str}')
