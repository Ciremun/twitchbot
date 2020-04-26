import youtube_dl
import time
import asyncio
import requests
import threading
import os
import random
import typing
import modules.globals as g

from math import floor
from pathlib import Path
from datetime import datetime
from os import listdir
from os.path import isfile, join
from modules.regex import *
from modules.pixiv import Pixiv


class Song(typing.NamedTuple):
    path: str
    title: str
    duration: str
    user_duration: int
    link: str
    username: str


def resizeimg(ri, rs, image, screenwidth, screenheight):  # resize to fit window
    if rs > ri:
        resized = image.width * screenheight / image.height, screenheight
        return resized[0], resized[1]
    elif rs < ri:
        resized = screenwidth, image.height * screenwidth / image.width
        return resized[0], resized[1]
    else:
        imagescale = screenwidth / image.width
        image.width *= imagescale
        image.height *= imagescale
        return image.width, image.height


def checkmodlist(username):  # check if user is mod
    if username == g.admin:
        return True
    result = g.db.check_if_mod(username)
    if result:
        return True
    return False


def checkbanlist(username):  # check if user is bad
    if username == g.admin:
        return False
    if checkmodlist(username):
        return False
    result = g.db.check_if_banned(username)
    if result:
        return True
    return False


def timecode_convert(timecode):
    """Get Seconds from timecode."""
    timecode = timecode.split(':')
    if len(timecode) == 1:
        return int(timecode[0])
    elif len(timecode) == 2:
        m, s = timecode[0], timecode[1]
        return int(m) * 60 + int(s)
    elif len(timecode) == 3:
        h, m, s = timecode[0], timecode[1], timecode[2]
        return int(h) * 3600 + int(m) * 60 + int(s)


def new_timecode(seconds, minutes, hours, duration):
    if duration <= 59:
        return f'{duration}s'
    elif duration <= 3599:
        if seconds <= 9:
            seconds = f'0{seconds}'
        return f'{minutes}:{seconds}'
    else:
        if minutes <= 9:
            minutes = f'0{minutes}'
        if seconds <= 9:
            seconds = f'0{seconds}'
        return f'{hours}:{minutes}:{seconds}'


def new_timecode_explicit(days, hours, minutes, seconds, duration):
    if duration < 1:
        return f'{floor(duration * 1000)}ms'
    timecode = []
    timecode_dict = {'d': days, 'h': hours, 'm': minutes, 's': seconds}
    for k, v in timecode_dict.items():
        if v:
            timecode.append(f'{v}{k}')
    return " ".join(timecode)


def seconds_convert(duration, explicit=False):
    init_duration = duration
    days = duration // (24 * 3600)
    duration = duration % (24 * 3600)
    hours = duration // 3600
    duration %= 3600
    minutes = duration // 60
    seconds = duration % 60
    days, hours, minutes, seconds = [floor(x) for x in [days, hours, minutes, seconds]]
    if explicit:
        return new_timecode_explicit(days, hours, minutes, seconds, init_duration)
    return new_timecode(seconds, minutes, hours, init_duration)


def while_is_file(folder, filename, form):  # change filename if path exists
    path = Path(folder + filename + form)
    while path.is_file():
        filename = ''.join(random.choices('qwertyuiopasdfghjklzxcvbnm' + '1234567890', k=10))
        path = Path(folder + filename + form)
    return filename


def get_tts_vc_key(vc):  # get voice name by registry key
    for k, v in g.tts_voices.items():
        if v == vc:
            return k
    return None


def sort_pixiv_arts(arts_list, result_list):
    for i in arts_list:
        artratio = i.width / i.height
        if i.page_count > 1 or 'ContentType.MANGA' in str(
                i.type) or artratio > g.pixiv_artratio or \
                any(x in str(i.tags) for x in g.banned_tags):
            continue
        result_list.append(i)
    return result_list


async def rename_command(username, messagesplit):  # rename function for image owners
    try:
        imagename = messagesplit[1].lower()
        newimagename = fixname(messagesplit[2].lower())
        moderator = checkmodlist(username)
        if not moderator and not check_owner(username, imagename):
            onlyfiles = [f for f in listdir('data/custom/') if isfile(join('data/custom/', f))]
            words = onlyfiles
            if imagename not in words:
                send_message(f'{username}, file not found')
                return
            for element in words:
                if element == imagename:
                    send_message(f'{username}, access denied')
        else:
            my_file = Path("data/custom/" + newimagename)
            if my_file.is_file():
                send_message("{}, {} already exists".format(username, newimagename))
                return
            if imagename[-4:] != newimagename[-4:] and not moderator:
                send_message(f"{username}, sowwy, format change isn't allowed")
                return
            try:
                os.rename('data/custom/' + imagename, 'data/custom/' + newimagename)
                g.db.update_link_filename(imagename, newimagename)
                g.db.update_owner_filename(imagename, newimagename)
                send_message('{}, {} --> {}'.format(username, imagename, newimagename))
            except:
                send_message(f'{username}, file not found')
    except IndexError:
        send_message(f'{username}, {g.prefix}ren <filename> <new filename>')


def send_list(username, messagesplit, list_str, list_arr, list_page_pos, list_type):
    if 490 >= len(list_str) > 0:
        send_message("{}".format(list_str))
        return
    if len(list_str) == 0:
        if list_type == "search":
            send_message(f'{username}, no results')
            return
        else:
            send_message(f'{username}, list is empty')
            return
    try:
        pagenum = int(messagesplit[list_page_pos])
        if pagenum <= 0 or pagenum > len(list_arr):
            send_message(f'{username}, page not found')
            return
        send_message("{} {}/{}".format(list_arr[pagenum - 1], pagenum, len(list_arr)))
    except (IndexError, ValueError):
        if len(list_str) > 490 or len(list_str) <= 490:
            send_message('{} 1/{}'.format(list_arr[0], len(list_arr)))


def owner_list(username, messagesplit):  # list of images for image owners
    result = g.db.check_ownerlist(username)
    result = [item[0] for item in result]
    result = " ".join(result)
    allpages = divide_chunks(result, 480)
    send_list(username, messagesplit, result, allpages, 1, "list")


def divide_chunks(string, length, lst=None, joinparam=' '):  # divide string into chunks
    chunk = []
    all_chunks = []
    if lst is None:
        lst = string.split()
    message_length = 0
    i = 0
    for element in lst:
        message_length += len(element) + 1
        if message_length + len(lst[i]) + 1 <= length:
            chunk.append(element)
        else:
            chunk = f'{joinparam}'.join(chunk) + f'{joinparam}' + element
            all_chunks.append(chunk)
            chunk = []
            message_length = 0
        i += 1
    chunk = f'{joinparam}'.join(chunk)
    all_chunks.append(chunk)
    all_chunks = list(filter(None, all_chunks))
    return all_chunks


def checklist(username, messagesplit, db_call):  # check ban/mod list
    result = db_call()
    result = [item[0] for item in result]
    result = " ".join(result)
    allpages = divide_chunks(result, 480)
    send_list(username, messagesplit, result, allpages, 1, "list")


def fixname(name):  # fix filename for windows
    if name.startswith('.'):
        name = '•' + name[1:]
    name = \
        name.replace('\\', '❤').replace('/', '❤').replace(':', ';').replace('*', '★').replace('?', '❓').replace(
            '"', "'").replace('<', '«').replace('>', '»').replace('|', '│')
    return name


def checkifnolink(act):
    mypath = 'data/custom/'
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    result = g.db.get_links_filenames()
    lst_result = [i[0] for i in result]
    words = [x if set(x.split()).intersection(lst_result) else x + '*' for x in onlyfiles]
    if act == '!search':
        return words
    linkwords = [x for x in words if '*' not in x]
    return words, linkwords


def get_current_date():
    nowdate = datetime.now()
    return nowdate


def check_owner(username, imagename):  # check if user owns image
    result = g.db.check_owner(imagename, username)
    if result:
        return True
    return False


def updatelastlink(selected):
    result = g.db.get_link(selected)
    result = " ".join([item[0] for item in result])
    if result:
        g.lastlink = result
        return
    g.lastlink = f'no link saved'
    return


async def sr_favs_del(username, messagesplit, songs):
    response, remove_song, target_not_found, song_removed_response = [], [], [], []
    for i in range(1, len(messagesplit)):
        await asyncio.sleep(0)
        try:
            index = int(messagesplit[i])
            if not 0 <= index <= len(songs):
                target_not_found.append(messagesplit[i])
                continue
            song = songs[index - 1]
            user_duration = song["user_duration"]
            if user_duration is None:
                user_duration = 0
                song_removed_response.append(song["title"])
            else:
                song_removed_response.append(f'{song["title"]} '
                                             f'[{seconds_convert(song["user_duration"])}]')
            remove_song.append((song["title"], username,
                                song["filename"],
                                user_duration,
                                song["link"], song["duration"]))
            try:
                os.remove('data/sounds/favs/' + song["filename"])
            except:
                pass
        except ValueError:
            target = messagesplit[i]
            song_found = False
            for song in songs:
                if target.lower() in song['title'].lower():
                    song_found = True
                    user_duration = song["user_duration"]
                    if user_duration is None:
                        user_duration = 0
                        song_removed_response.append(song["title"])
                    else:
                        song_removed_response.append(f'{song["title"]} '
                                                     f'[{seconds_convert(song["user_duration"])}]')
                    remove_song.append((song["title"], username,
                                        song["filename"],
                                        user_duration,
                                        song["link"], song["duration"]))
                    try:
                        os.remove('data/sounds/favs/' + song["filename"])
                    except:
                        pass
                    break
            if not song_found:
                target_not_found.append(messagesplit[i])
                continue
    g.db.remove_srfavs(remove_song)
    if song_removed_response:
        response.append(f'Favorites removed: {", ".join(song_removed_response)}')
    if target_not_found:
        response.append(f'Not found: {", ".join(target_not_found)}')
    if response:
        response_str = ' '.join(response)
        if len(response_str) > 470:
            response *= 0
            if song_removed_response:
                response.append(f'Favorites removed: {len(song_removed_response)}')
            if target_not_found:
                response.append(f'Not found: {len(target_not_found)}')
            send_message(f'{username}, {" ".join(response)}')
        else:
            send_message(response_str)


async def del_chat_command(username, messagesplit):
    response_not_found, response_denied, response_deleted, remove_links, remove_owners = [], [], [], [], []
    file_deleted = False
    moderator = checkmodlist(username)
    for i in messagesplit[1:]:
        imagename = i.lower()
        if not moderator and not check_owner(username, imagename):
            words = [f for f in listdir('data/custom/') if isfile(join('data/custom/', f))]
            if not set(imagename.split()).intersection(words):
                response_not_found.append(imagename)
                continue
            else:
                response_denied.append(imagename)
        else:
            try:
                os.remove('data/custom/' + imagename)
                remove_links.append((imagename,))
                remove_owners.append((imagename,))
                response_deleted.append(imagename)
                file_deleted = True
            except:
                response_not_found.append(i.lower())
    response = []
    if file_deleted:
        g.db.remove_link(remove_links)
        g.db.remove_owner(remove_owners)
        response.append(f"Deleted: {', '.join(response_deleted)}")
    if response_denied:
        response.append(f"Access denied: {', '.join(response_denied)}")
    if response_not_found:
        response.append(f"Not found: {', '.join(response_not_found)}")
    response = f"{username}, {'; '.join(response)}"
    if len(response) <= 490:
        send_message(response)
    else:
        response = divide_chunks(response, 480)
        for i in response:
            send_message(i)


async def delete_ban_mod(response, boolean, str1, str2, username):
    if response:
        response = ', '.join(response)
        if boolean:
            response = f'{username}, {str1}, except: {response} - {str2}'
        else:
            response = f'{username}, {response} - {str2}'
        if len(response) <= 490:
            send_message(response)
        else:
            response = divide_chunks(response, 400)
            for i in response:
                send_message(i)
    else:
        send_message('{}, {}'.format(username, str1))


async def ban_mod_commands(username, messagesplit, str1, str2, check_func, db_call, check_func_result):
    response = []
    users = []
    boolean = False
    for i in messagesplit[1:]:
        user = i.lower()
        if check_func(user) == check_func_result:
            response.append(user)
        else:
            users.append((user,))
            boolean = True
    db_call(users)
    await delete_ban_mod(response, boolean, str1, str2, username)


def sr_get_list(username, messagesplit):
    if not g.playlist:
        send_message(f'{username}, playlist is empty')
        return
    sr_list = [f'{x[1]} [{seconds_convert(x[3])}] #{i}' if x[3] is not None else f'{x[1]} #{i}' for i, x in
               enumerate(g.playlist, start=1)]
    sr_str = ", ".join(sr_list)
    sr_list = divide_chunks(sr_str, 470, sr_list, joinparam=', ')
    send_list(username, messagesplit, sr_str, sr_list, 1, "list")


async def change_stream_settings(username, messagesplit, setting):
    channel_info = requests.get(f"https://api.twitch.tv/kraken/channels/{g.channel_id}",
                                headers={"Client-ID": g.client_id,
                                         "Accept": "application/vnd.twitchtv.v5+json"}).json()
    if setting == 'title':
        set_title = " ".join(messagesplit[1:])
        if not set_title:
            send_message(f'Title: {channel_info["status"]}')
        else:
            await change_status_game(set_title, channel_info["game"], username)
    elif setting == 'game':
        set_game = " ".join(messagesplit[1:])
        if not set_game:
            send_message(f'Game: {channel_info["game"]}')
        else:
            await change_status_game(channel_info["status"], set_game, username)


async def change_status_game(channel_status, channel_game, username):
    requests.put(f"https://api.twitch.tv/kraken/channels/{g.channel_id}",
                 headers={"Client-ID": g.client_id,
                          "Accept": "application/vnd.twitchtv.v5+json",
                          "Authorization": g.client_auth},
                 data={"channel[status]": channel_status,
                       "channel[game]": channel_game})
    send_message(f'{username}, done')


def np_response(mode):
    current_time_ms = g.Player.get_time()
    current_time = floor(current_time_ms / 1000)
    current_time = seconds_convert(current_time)
    send_message(f'{mode}: {g.np} - {g.sr_url} - {current_time}/{g.np_duration}')


def try_timecode(url, messagesplit, username, timecode_pos=None, yt_request=True, folder='data/sounds/sr/',
                 ytsearch=False):
    try:
        if timecode_pos is None:
            raise IndexError
        timecode = messagesplit[timecode_pos]
        if re.match(timecode_re, timecode):
            g.sr_download_queue.call_download_clip(url, username, user_duration=timecode, yt_request=yt_request,
                                                   folder=folder, ytsearch=ytsearch)
        else:
            send_message(f'{username}, timecode error')
    except IndexError:
        g.sr_download_queue.call_download_clip(url, username, yt_request=yt_request, folder=folder,
                                               ytsearch=ytsearch)


def clear_folder(path):
    filelist = [f for f in os.listdir(path) if isfile(join(path, f))]
    for f in filelist:
        try:
            os.remove(os.path.join(path, f))
        except:
            pass


def change_pixiv(pattern, group, group2, url, messagesplit, username):
    try:
        imagename = fixname(messagesplit[2].lower())
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        Pixiv.save_pixiv_art(imagename, username, pxid, setpic=True, save=True)
    except IndexError:
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        Pixiv.save_pixiv_art(g.db.numba, username, pxid, 'data/images/', setpic=True)
        g.db.update_imgcount(int(g.db.numba) + 1)


def save_pixiv(pattern, group, group2, url, messagesplit, username):
    try:
        imagename = fixname(messagesplit[2].lower())
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        Pixiv.save_pixiv_art(imagename, username, pxid, save=True, save_msg=True)
    except IndexError:
        pass


def sr_download(messagesplit, username, folder='data/sounds/sr/', link_pos=1, timecode_pos=None, ytsearch=False):
    if re.match(youtube_link_re, messagesplit[link_pos]):
        try_timecode(messagesplit[link_pos], messagesplit, username, timecode_pos=timecode_pos, folder=folder,
                     ytsearch=ytsearch)
    elif re.match(video_id_re, messagesplit[link_pos]):
        video_id = video_id_re.sub(r'\2', messagesplit[link_pos])
        url = f'https://www.youtube.com/watch?v={video_id}'
        try_timecode(url, messagesplit, username, timecode_pos=timecode_pos, folder=folder, ytsearch=ytsearch)
    elif re.match(soundcloud_re, messagesplit[link_pos]):
        try_timecode(messagesplit[link_pos], messagesplit, username, timecode_pos=timecode_pos,
                     yt_request=False, folder=folder, ytsearch=ytsearch)
    elif re.match(soundcloud_id_re, messagesplit[1]):
        soundcloud_id = soundcloud_re.sub(r'\4', messagesplit[link_pos])
        url = f'https://soundcloud.com/{soundcloud_id}'
        try_timecode(url, messagesplit, username, timecode_pos=timecode_pos, yt_request=False,
                     folder=folder, ytsearch=ytsearch)
    else:
        return False
    return True


def get_srfavs_dictlist(username):
    result = g.db.check_srfavs_list(username)
    if not result:
        return False
    songs = []
    for song in result:
        if song[2] == 0:
            user_duration = None
        else:
            user_duration = song[2]
        song_dict = {
            "title": song[0],
            "filename": song[1],
            "user_duration": user_duration,
            "link": song[3],
            "duration": song[4]
        }
        songs.append(song_dict)
    return songs


def set_random_pic(lst, response):
    if not lst:
        send_message(response)
        return
    selected = random.choice(lst)
    updatelastlink(selected)
    g.last_rand_img = selected
    call_draw('data/custom/', selected)


def change_save_command(username, messagesplit, do_draw=False, do_save=False, do_save_response=False):
    url = messagesplit[1]
    if re.match(pixiv_re, url):
        if do_draw:
            change_pixiv(pixiv_re, r'\5', r'\8', url, messagesplit, username)
        else:
            save_pixiv(pixiv_re, r'\5', r'\8', url, messagesplit, username)
    elif re.match(pixiv_src_re, url):
        if do_draw:
            change_pixiv(pixiv_src_re, r'\4', r'\6', url, messagesplit, username)
        else:
            save_pixiv(pixiv_src_re, r'\4', r'\6', url, messagesplit, username)
    elif re.match(regex, url):
        content_type = requests.head(url, allow_redirects=True).headers.get('content-type').split(
            '/')
        if content_type[0] != 'image':
            send_message(f'{username}, unknown format')
            return
        if content_type[1] != 'gif':
            file_format = '.png'
        else:
            file_format = f'.{content_type[1]}'
        r = requests.get(url)
        try:
            folder = 'data/custom/'
            imagename = while_is_file(folder, fixname(messagesplit[2].lower()),
                                      f'{file_format}')
            filepath = Path(f'{folder}{imagename}{file_format}')
            do_save = True
        except IndexError:
            folder = 'data/images/'
            imagename = g.db.numba
            g.db.update_imgcount(int(g.db.numba) + 1)
            filepath = Path(f'{folder}{imagename}{file_format}')
        with open(filepath, 'wb') as download:
            download.write(r.content)
        if filepath.is_file():
            if do_draw:
                call_draw(folder, f'{imagename}{file_format}')
            if do_save:
                g.db.add_link(url, f'{imagename}{file_format}')
                g.db.add_owner(f'{imagename}{file_format}', username)
            if do_save_response:
                send_message(f'{username}, {imagename}{file_format} saved')
        else:
            send_message(f'{username}, download error')
    else:
        send_message(f"{username}, no link")


def send_message(message):  # bot message to twitch chat
    g.s.send(bytes("PRIVMSG #" + g.CHANNEL + " :" + message + "\r\n", "UTF-8"))


def call_draw(folder, selected):  # update global var for pyglet update method, changes image
    g.res = folder
    g.drawfile = selected


def sr_start_playing():  # wait for vlc player to start
    while not player_good_state():
        time.sleep(0.01)


def player_good_state():
    return any(str(g.Player.get_state()) == x for x in ['State.Playing', 'State.Paused'])


def playmusic():  # play song from playlist
    if not g.playlist:
        return
    file = g.playlist.pop(0)
    media = g.PlayerInstance.media_new(file.path)
    media.get_mrl()
    g.Player.set_media(media)
    g.Player.play()
    g.np, g.np_duration, g.sr_url = file.title, file.duration, file.link
    if file.user_duration is not None:
        g.Player.set_time(file.user_duration * 1000)
    sr_start_playing()
    while player_good_state():
        time.sleep(2)


def download_clip(url, username, user_duration=None, yt_request=True, folder='data/sounds/sr/', ytsearch=False):
    """
    download .wav song file, add song to favorites, add song to playlist
    :param url: youtube/soundcloud link or youtube search query
    :param username: twitch username
    :param user_duration: timecode (song start time)
    :param yt_request: if url is youtube
    :param folder: .wav file folder
    :param ytsearch: if youtube search query
    """
    name = ''.join(random.choices('qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10))
    name = while_is_file(folder, name, '.wav')
    home = folder + name + '.wav'
    ydl_opts = {
        'quiet': True,
        'nocheckcertificate': True,
        'max_downloads': '1',
        'cookiefile': 'data/special/cookies.txt',
        'ratelimit': g.ytdl_rate,
        'format': 'bestaudio/best',
        'outtmpl': home,
        'noplaylist': True,
        'continue_dl': True,
        'noprogress': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192', }]
    }
    if ytsearch:
        ydl_opts['playlist_items'] = '1'
        search_query = ''
        for i in url.split():
            search_query += i + '+'
        search_query = search_query[:-1]
        url = f'https://www.youtube.com/results?search_query={search_query}'
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        if ytsearch:
            title = info_dict['entries'][0].get('title', None)
            duration = info_dict['entries'][0].get('duration', 0)
            video_id = info_dict['entries'][0].get('id', None)
            url = f'https://youtu.be/{video_id}'
        else:
            title = info_dict.get('title', None)
            duration = info_dict.get('duration', 0)
        if yt_request and not ytsearch:
            sr_url = info_dict.get('id', None)
            sr_url = f'https://youtu.be/{sr_url}'
        else:
            sr_url = url
        if user_duration is not None:
            user_duration = timecode_convert(user_duration)
            if user_duration > duration:
                send_message(f'{username}, time exceeds duration! [{seconds_convert(duration)}]')
                return
        if duration > g.max_duration and not checkmodlist(username):
            send_message(f'{username}, '
                         f'{seconds_convert(duration)} > max duration[{seconds_convert(g.max_duration)}]')
            return
        ydl.prepare_filename(info_dict)
        ydl.download([url])
        if folder == 'data/sounds/favs/':
            if user_duration is None:
                g.db.add_srfavs(title, username, name + '.wav', 0, sr_url, duration)
                send_message(f'{username}, {title} - {sr_url} - added to favorites')
            else:
                g.db.add_srfavs(title, username, name + '.wav', user_duration, sr_url, duration)
                send_message(
                    f'{username}, {title} [{seconds_convert(user_duration)}] - {sr_url} - added to favorites')
            return
        duration = seconds_convert(duration)
        g.playlist.append(Song(home, title, duration, user_duration, sr_url, username))
        if user_duration is not None:
            send_message(f'+ {title} [{seconds_convert(user_duration)}] - {sr_url} - #{len(g.playlist)}')
        else:
            send_message(f'+ {title} - {sr_url} - #{len(g.playlist)}')
        g.sr_queue.call_playmusic()


class Thread(threading.Thread):

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.tasks = []
        self.start()

    def run(self):
        while True:
            time.sleep(0.2)
            if self.tasks:
                task = self.tasks.pop(0)
                task['func'](*task['args'], **task['kwargs'])

    def call_playmusic(self):
        self.tasks.append({'func': playmusic, 'args': (), 'kwargs': {}})

    def call_download_clip(self, url, username, **kwargs):
        self.tasks.append({'func': download_clip, 'args': (url, username), 'kwargs': kwargs})
