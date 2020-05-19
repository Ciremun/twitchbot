import pafy
import time
import requests
import threading
import os
import random
import typing
import queue
import io
import base64
import _globals as g

from math import floor
from pathlib import Path
from datetime import datetime
from os import listdir
from os.path import isfile, join
from PIL import Image
from _regex import re, regex, timecode_re, youtube_id_re, youtube_link_re, pixiv_re, pixiv_src_re
from _pixiv import Pixiv
from _picture import flask_app


def get_tts_vc_key(vc):
    for k, v in g.tts_voices.items():
        if v == vc:
            return k


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


class Message:

    def __init__(self, message, author):
        self.content = message
        self.parts = message.split()
        self.author = author
    
    def __str__(self):
        return self.content


class Song(typing.NamedTuple):
    vlc_link: str
    title: str
    duration: str
    user_duration: int
    link: str
    username: str


def imgur_utils_wrap(message):
    filename = message.parts[1]
    db_link = g.db.get_link(filename)
    if db_link:
        if is_mod(message.author):
            g.db.remove_link([(filename,)])
            return imgur_utils_wrap(message)
        return send_message(f'{message.author}, {filename} - {db_link[0][0]}')
    path = f'data/custom/{filename}'
    if not Path(path).is_file():
        return send_message(f'{message.author}, file {filename} not found')
    encoded_file = imgur_convert_image(path)
    link = imgur_upload_image(encoded_file)
    if not re.match(regex, link):
        return send_message(f'{message.author}, file upload error [{link}]')
    send_message(f'{message.author}, {filename} - {link}')
    g.db.add_link(link, filename)


def imgur_upload_image(byte):
    result = requests.post('https://api.imgur.com/3/upload',
                           headers={'Authorization': f'Client-ID {g.imgur_client_id}'}, data={'image': byte}).json()
    success = result.get('success')
    status_code = result.get('status')
    if success and status_code == 200:
        link = result.get('data').get('link')
        return f'{link}'
    return f'{status_code}'


def imgur_convert_image(file):
    pil_image = Image.open(file)
    form = pil_image.format
    mode = pil_image.mode
    if any(form == x for x in ['JPEG', 'PNG', 'GIF']):
        with open(file, "rb") as image_file:
            return base64.b64encode(image_file.read())
    elif mode == 'RGBA':
        form = 'PNG'
    elif mode == 'RGB':
        form = 'JPEG'
    bytearr = io.BytesIO()
    pil_image.save(bytearr, format=form)
    bytearr = bytearr.getvalue()
    return bytearr


def resizeimg(ri, rs, imgwidth, imgheight , screenwidth, screenheight):  # resize to fit window
    if rs > ri:
        resized = imgwidth * screenheight / imgheight, screenheight
        return resized[0], resized[1]
    elif rs < ri:
        resized = screenwidth, imgheight * screenwidth / imgwidth
        return resized[0], resized[1]
    else:
        imagescale = screenwidth / imgwidth
        imgwidth *= imagescale
        imgheight *= imagescale
        return imgwidth, imgheight


def is_mod(username):  # check if user is mod
    if username == g.admin:
        return True
    result = g.db.check_if_mod(username)
    if result:
        return True
    return False


def no_ban(username):  # check if user is bad
    if username == g.admin:
        return True
    if is_mod(username):
        return True
    result = g.db.check_if_banned(username)
    if result:
        return False
    return True


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
        return f'{duration}'
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


def sort_pixiv_arts(arts_list, result_list):
    for i in arts_list:
        artratio = i.width / i.height
        if i.page_count > 1 or 'ContentType.MANGA' in str(
                i.type) or artratio > g.pixiv_artratio or \
                any(x in str(i.tags) for x in g.banned_tags):
            continue
        result_list.append(i)
    return result_list


def rename_command(message):  # rename function for image owners
    try:
        imagename = message.parts[1].lower()
        newimagename = fixname(message.parts[2].lower())
        moderator = is_mod(message.author)
        if not moderator and not check_owner(message.author, imagename):
            onlyfiles = [f for f in listdir('data/custom/') if isfile(join('data/custom/', f))]
            words = onlyfiles
            if imagename not in words:
                send_message(f'{message.author}, file not found')
                return
            for element in words:
                if element == imagename:
                    send_message(f'{message.author}, access denied')
        else:
            my_file = Path("data/custom/" + newimagename)
            if my_file.is_file():
                send_message(f"{message.author}, {newimagename} already exists")
                return
            if imagename[-4:] != newimagename[-4:] and not moderator:
                send_message(f"{message.author}, sowwy, format change isn't allowed")
                return
            try:
                os.rename('data/custom/' + imagename, 'data/custom/' + newimagename)
                g.db.update_link_filename(imagename, newimagename)
                g.db.update_owner_filename(imagename, newimagename)
                send_message(f'{message.author}, {imagename} --> {newimagename}')
            except:
                send_message(f'{message.author}, file not found')
    except IndexError:
        send_message(f'{message.author}, {g.prefix}ren <filename> <new filename>')


def send_list(message, list_str, list_arr, list_page_pos, list_type):
    if 490 >= len(list_str) > 0:
        return send_message(f"{list_str}")
    if not list_str:
        if list_type == "search":
            return send_message(f'{message.author}, no results')
        return send_message(f'{message.author}, list is empty')
    try:
        pagenum = int(message.parts[list_page_pos])
        if pagenum <= 0 or pagenum > len(list_arr):
            return send_message(f'{message.author}, page not found')
        send_message(f"{list_arr[pagenum - 1]} {pagenum}/{len(list_arr)}")
    except (IndexError, ValueError):
        if list_arr:
            send_message(f'{list_arr[0]} 1/{len(list_arr)}')


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


def checklist(message, db_call):  # check ban/mod list
    result = db_call()
    result = [item[0] for item in result]
    result = " ".join(result)
    allpages = divide_chunks(result, 480)
    send_list(message, result, allpages, 1, "list")


def fixname(name):  # fix filename for OS Windows
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


def check_owner(message, imagename):  # check if user owns image
    result = g.db.check_owner(imagename, message.author)
    if result:
        return True
    return False


def sr_favs_del(message, songs):
    response, remove_song, target_not_found, song_removed_response = [], [], [], []
    for i in range(1, len(message.parts)):
        try:
            index = int(message.parts[i])
            if not 0 <= index <= len(songs):
                target_not_found.append(message.parts[i])
                continue
            song = songs[index - 1]
            user_duration = song.user_duration
            if user_duration is None:
                user_duration = 0
            remove_tup = (song.title, timecode_convert(song.duration), user_duration, song.link, message.author)
            if remove_tup not in remove_song:
                song_removed_response.append(f'{song.title}'
                                             f'{"" if not user_duration else f" [{seconds_convert(user_duration)}]"}')
                remove_song.append(remove_tup)
        except ValueError:
            target = message.parts[i]
            song_found = False
            for song in songs:
                if target.lower() in song.title.lower():
                    song_found = True
                    user_duration = song.user_duration
                    if user_duration is None:
                        user_duration = 0
                    remove_tup = (song.title, timecode_convert(song.duration), user_duration, song.link, message.author)
                    if remove_tup not in remove_song:
                        song_removed_response.append(f'{song.title}'
                                                     f'{"" if not user_duration else f" [{seconds_convert(user_duration)}]"}')
                        remove_song.append(remove_tup)
            if not song_found:
                target_not_found.append(message.parts[i])
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
            send_message(f'{message.author}, {" ".join(response)}')
        else:
            send_message(response_str)


def del_chat_command(message):
    response_not_found, response_denied, response_deleted, remove_links, remove_owners = [], [], [], [], []
    file_deleted = False
    moderator = is_mod(message.author)
    for i in message.parts[1:]:
        imagename = i.lower()
        if not moderator and not check_owner(message.author, imagename):
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
    response = f"{message.author}, {'; '.join(response)}"
    if len(response) <= 490:
        send_message(response)
    else:
        response = divide_chunks(response, 480)
        for i in response:
            send_message(i)


def ban_mod_commands(message, str1, str2, check_func, db_call, check_func_result):
    response = []
    users = []
    boolean = False
    for i in message.parts[1:]:
        user = i.lower()
        if not check_func(user) == check_func_result:
            response.append(user)
        else:
            users.append((user,))
            boolean = True
    db_call(users)
    if response:
        response = ', '.join(response)
        if boolean:
            response = f'{message.author}, {str1}, except: {response} - {str2}'
        else:
            response = f'{message.author}, {response} - {str2}'
        if len(response) <= 490:
            send_message(response)
        else:
            response = divide_chunks(response, 400)
            for i in response:
                send_message(i)
    else:
        send_message(f'{message.author}, {str1}')


def change_stream_settings(message, setting):
    channel_info = requests.get(f"https://api.twitch.tv/kraken/channels/{g.channel_id}",
                                headers={"Client-ID": g.client_id,
                                         "Accept": "application/vnd.twitchtv.v5+json"}).json()
    if setting == 'title':
        set_title = " ".join(message.parts[1:])
        if not set_title:
            send_message(f'Title: {channel_info["status"]}')
        else:
            change_status_game(set_title, channel_info["game"], message.author)
    elif setting == 'game':
        set_game = " ".join(message.parts[1:])
        if not set_game:
            send_message(f'Game: {channel_info["game"]}')
        else:
            change_status_game(channel_info["status"], set_game, message.author)


def change_status_game(channel_status, channel_game, username):
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


def try_timecode(message, url, timecode_pos, save=False, ytsearch=False):
    try:
        if timecode_pos is None:
            raise IndexError
        timecode = message.parts[timecode_pos]
        if re.match(timecode_re, timecode):
            g.sr_download_queue.new_task(download_clip, url, message.author, user_duration=timecode, ytsearch=ytsearch, save=save)
            return
        send_message(f'{message.author}, timecode error')
    except IndexError:
        g.sr_download_queue.new_task(download_clip, url, message.author, ytsearch=ytsearch, save=save)


def clear_folder(path):
    filelist = [f for f in os.listdir(path) if isfile(join(path, f))]
    for f in filelist:
        try:
            os.remove(os.path.join(path, f))
        except:
            pass


def change_pixiv(message, pattern, group, group2, url):
    try:
        imagename = fixname(message.parts[2].lower())
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        g.px_download_queue.new_task(Pixiv.save_pixiv_art, imagename, message.author, pxid, setpic=True, save=True)
    except IndexError:
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        g.px_download_queue.new_task(Pixiv.save_pixiv_art, g.db.numba, message.author, pxid, 'data/images/', setpic=True)
        g.db.update_imgcount(int(g.db.numba) + 1)


def save_pixiv(message, pattern, group, group2, url):
    try:
        imagename = fixname(message.parts[2].lower())
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        g.px_download_queue.new_task(Pixiv.save_pixiv_art, imagename, message.author, pxid, save=True, save_msg=True)
    except IndexError:
        pass


def sr_download(message, url, timecode_pos, save=False):
    if re.match(youtube_link_re, url):
        try_timecode(message, url, timecode_pos, save=save)
    elif re.match(youtube_id_re, url):
        video_id = youtube_id_re.sub(r'\2', url)
        url = f'https://www.youtube.com/watch?v={video_id}'
        try_timecode(message, url, timecode_pos, save=save)
    else:
        return False
    return True


def get_srfavs_dictlist(username):
    result = g.db.check_srfavs_list(username)
    if not result:
        return False
    return [Song(None, song[0], seconds_convert(song[1]), (None if song[2] == 0 else song[2]), song[3], username)
            for song in result]


def set_random_pic(lst, response):
    if not lst:
        send_message(response)
        return
    selected = random.choice(lst)
    g.last_rand_img = selected
    g.lastlink = None
    call_draw('custom/', selected)


def change_save_command(message, do_draw=False, do_save=False, do_save_response=False):
    url = message.parts[1]
    if re.match(pixiv_re, url):
        if do_draw:
            change_pixiv(message, pixiv_re, r'\5', r'\8', url)
        else:
            save_pixiv(message, pixiv_re, r'\5', r'\8', url)
    elif re.match(pixiv_src_re, url):
        if do_draw:
            change_pixiv(message, pixiv_src_re, r'\4', r'\6', url)
        else:
            save_pixiv(message, pixiv_src_re, r'\4', r'\6', url)
    elif re.match(regex, url):
        try:
            content_type = requests.head(url, allow_redirects=True).headers.get('content-type').split('/')
        except requests.exceptions.ConnectionError:
            send_message(f'{message.author}, connection error')
            return
        if content_type[0] != 'image':
            send_message(f'{message.author}, no image')
            return
        if content_type[1] != 'gif':
            file_format = '.png'
        else:
            file_format = f'.{content_type[1]}'
        r = requests.get(url)
        try:
            folder = 'custom/'
            imagename = while_is_file(folder, fixname(message.parts[2].lower()), f'{file_format}')
            do_save = True
        except IndexError:
            folder = 'images/'
            imagename = g.db.numba
            g.db.update_imgcount(int(g.db.numba) + 1)
        filepath = f'data/{folder}{imagename}{file_format}'
        with open(filepath, 'wb') as download:
            download.write(r.content)
        if Path(filepath).is_file():
            image = f'{imagename}{file_format}'
            if do_draw:
                call_draw(folder, image)
            if do_save:
                g.db.add_link(url, image)
                g.db.add_owner(image, message.author)
            if do_save_response:
                send_message(f'{message.author}, {image} saved')
        else:
            send_message(f'{message.author}, download error')
    else:
        send_message(f"{message.author}, no link")


def send_message(message: str, pipe=False):  # bot message to twitch chat
    if pipe:
        return message.split()
    g.s.send(bytes(f"PRIVMSG #{g.CHANNEL} :{message}\r\n", "UTF-8"))


def call_draw(folder: str, filename: str):  # change image
    flask_app.set_image(folder, filename)


def sr_start_playing():  # wait for vlc player to start
    while not player_good_state():
        time.sleep(0.01)


def player_good_state():
    return any(str(g.Player.get_state()) == x for x in ['State.Playing', 'State.Paused'])


def fix_pafy_url(pafy_url: str, pafy_obj):
    if 'videoplayback' in pafy_url:
        return pafy_url
    return pafy_obj.getbest().url


def playmusic():  # play song from playlist
    if not g.playlist:
        return
    song = g.playlist.pop(0)
    media = g.PlayerInstance.media_new(song.vlc_link)
    media.get_mrl()
    g.Player.set_media(media)
    g.Player.play()
    g.np, g.np_duration, g.sr_url, g.sr_user = song.title, song.duration, song.link, song.username
    if song.user_duration is not None:
        g.Player.set_time(song.user_duration * 1000)
    sr_start_playing()
    while player_good_state():
        time.sleep(2)


def get_pafy_obj(url: str):
    pafy_obj = None
    i = 0
    while not pafy_obj:
        try:
            pafy_obj = pafy.new(url)
        except OSError as e:
            if 'This video is unavailable.' in str(e):
                send_message(f'{url} is unavailable.')
                return
            i += 1
            if i > 5:
                return
            print('OSError (pafy bug?) in get_pafy_obj, retrying..')
    return pafy_obj


def download_clip(url: str, username: str, user_duration=None, ytsearch=False, save=False):
    """
    add song to playlist/favorites
    :param url: youtube link/id or search query
    :param username: twitch username
    :param user_duration: timecode (song start time)
    :param ytsearch: youtube search query
    :param save: add to favorites
    """
    if not is_mod(username):
        g.Main.sr_cooldowns[username] = time.time()
    if not ytsearch:
        pafy_obj = get_pafy_obj(url)
        if not pafy_obj:
            return
        duration = pafy_obj.length
        user_duration = check_sr_req(user_duration, duration, username)
        if user_duration is False:
            return
        pafy_url = pafy_obj.getbestaudio()
        if not pafy_url:
            send_message(f'no audio for {url}')
            return
        vlc_link = fix_pafy_url(pafy_url.url, pafy_obj)
        title = pafy_obj.title
        url = f'https://youtu.be/{pafy_obj.videoid}'
    else:
        query = requests.utils.quote(url)
        result = requests.get('https://www.googleapis.com/youtube/v3/search?'
                              f'part=snippet&maxResults=1&type=video&q={query}&key={g.google_key}',
                              headers={'Accept': 'application/json'}).json()
        items = result.get("items")
        if not items:
            send_message(f'{username}, no results')
            return
        url = f'https://youtu.be/{items[0]["id"]["videoId"]}'
        pafy_obj = get_pafy_obj(url)
        if not pafy_obj:
            return
        duration = pafy_obj.length
        user_duration = check_sr_req(user_duration, duration, username)
        if user_duration is False:
            return
        pafy_url = pafy_obj.getbestaudio()
        if not pafy_url:
            send_message(f'no audio for {url}')
            return
        vlc_link = fix_pafy_url(pafy_url.url, pafy_obj)
        title = pafy_obj.title
    if save:
        if user_duration is None:
            g.db.add_srfavs(title, duration, 0, url, username)
            send_message(f'{username}, {title} - {url} - added to favorites')
        else:
            g.db.add_srfavs(title, duration, user_duration, url, username)
            send_message(f'{username}, {title} [{seconds_convert(user_duration)}] - {url} - added to favorites')
        return
    duration = seconds_convert(duration)
    song = Song(vlc_link, title, duration, user_duration, url, username)
    g.playlist.append(song)
    response = new_song_response([], song)
    send_message(f'+ {response[0]}')
    g.sr_queue.new_task(playmusic)


def check_sr_req(user_duration, duration, username):
    if user_duration is not None:
        if not isinstance(user_duration, int):
            user_duration = timecode_convert(user_duration)
        if user_duration > duration:
            send_message(f'{username}, time exceeds duration! [{seconds_convert(duration)}]')
            return False
    if duration > g.max_duration and not is_mod(username):
        send_message(f'{username}, '
                     f'{seconds_convert(duration)} > max duration[{seconds_convert(g.max_duration)}]')
        return False
    return user_duration


def sr(username):
    if not g.sr:
        return False
    return not sr_user_cooldown(username)


def sr_user_cooldown(username):
    sr_cooldown = g.sr_cooldown
    if not sr_cooldown:
        return False
    user_cooldown = g.Main.sr_cooldowns.get(username, None)
    if not user_cooldown:
        return False
    time_diff = time.time() - user_cooldown
    if time_diff < sr_cooldown:
        send_message(f'{username}, your cooldown is {seconds_convert(sr_cooldown - time_diff, explicit=True)}')
        return True
    del g.Main.sr_cooldowns[username]
    return False


def next_song_in():
    if player_good_state():
        current_time_ms = g.Player.get_time()
        current_time = floor(current_time_ms / 1000)
        np_duration = timecode_convert(g.np_duration)
        return np_duration - current_time
    return 0


def new_song_response(response: list, song: Song):
    next_in = next_song_in()
    if not next_in and g.sr_queue.q.empty():
        response.append(
            f'{song.title} '
            f'{"" if song.user_duration is None else f"[{seconds_convert(song.user_duration)}]"}'
            f' - {song.link} - Now playing'
        )
    else:
        next_in += sum(
            timecode_convert(x.duration) - x.user_duration if x.user_duration else timecode_convert(x.duration) for x in
            g.playlist[:-1])
        response.append(
            f'{song.title} '
            f'{"" if song.user_duration is None else f"[{seconds_convert(song.user_duration)}]"}'
            f' - {song.link} - #{len(g.playlist)}'
            f'{"" if not next_in else f", playing in {seconds_convert(next_in, explicit=True)}"}'
        )
    return response


class RunInThread(threading.Thread):

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.q = queue.Queue()
        self.start()

    def run(self):
        while True:
            task = self.q.get(block=True)
            task['func'](*task['args'], **task['kwargs'])
            self.q.task_done()

    def new_task(self, func, *args, **kwargs):
        self.q.put({'func': func, 'args': args, 'kwargs': kwargs})
