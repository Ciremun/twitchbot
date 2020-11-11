import threading
import random
import base64
import queue
import json
import time
import os
import io
import re
from os.path import isfile, join
from pathlib import Path
from math import floor
from json.decoder import JSONDecodeError

import requests
from PIL import Image
from youtube_dl import DownloadError

import src.db as db
import src.config as g
from .qthreads import sr_download_queue, px_download_queue, sr_queue
from .classes import Song, Message
from .pixiv import Pixiv
from .server import set_image, Player
from .log import logger

link_re = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
timecode_re = re.compile(r'^(t:)((?:(?:(\d+):)?(\d+):)?(\d+))$')
youtube_link_re = re.compile(r'http(?:s?)://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?')
youtube_id_re = re.compile(r'^([/]?watch\?v)?=([\w-]{11})$')
pixiv_re = re.compile(r'^(https://)?(www.)?pixiv\.net/(en)?(artworks)?/(\d+)?(artworks)?(/(\d+)?)?$')
pixiv_src_re = re.compile(r'^(https://)?(www.)?i\.pximg\.net/[\w\-]+/\w+/\d+/\d+/\d+/\d+/\d+/\d+/(('
                          r'\d+)_p\d+\w+\.\w+)?((\d+)_p\d+\.\w+)?$')
chat_msg_re = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")

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


def imgur_utils_wrap(message):
    filename = message.parts[1]
    db_link = db.get_link(filename)
    if db_link:
        if is_mod(message.author):
            db.remove_link([(filename,)])
            return imgur_utils_wrap(message)
        return send_message(f'{message.author}, {filename} - {db_link[0][0]}')
    path = f'flask/images/user/{filename}'
    if not Path(path).is_file():
        return send_message(f'{message.author}, file {filename} not found')
    encoded_file = imgur_convert_image(path)
    link = imgur_upload_image(encoded_file)
    if not re.match(link_re, link):
        return send_message(f'{message.author}, file upload error [{link}]')
    send_message(f'{message.author}, {filename} - {link}')
    db.add_link(link, filename)


def imgur_upload_image(byte):
    result = requests.post('https://api.imgur.com/3/image',
                           headers={'Authorization': f'Client-ID {g.ImgurClientID}'}, data={'image': byte}).json()
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


def is_admin(username):
    return username == g.admin


def is_mod(username):
    if username == g.admin:
        return True
    result = db.check_if_mod(username)
    if result:
        return True
    return False


def no_ban(username):
    if is_mod(username):
        return True
    result = db.check_if_banned(username)
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
                i.type) or artratio > g.pixiv_max_art_ratio or \
                any(x in str(i.tags) for x in g.pixiv_banned_tags):
            continue
        result_list.append(i)
    return result_list


def rename_command(message):  # rename function for image owners
    try:
        imagename = message.parts[1].lower()
        newimagename = fixname(message.parts[2].lower())
        moderator = is_mod(message.author)
        if not moderator and not check_owner(message.author, imagename):
            onlyfiles = [f for f in os.listdir('flask/images/user/') if isfile(join('flask/images/user/', f))]
            words = onlyfiles
            if imagename not in words:
                send_message(f'{message.author}, file not found')
                return
            for element in words:
                if element == imagename:
                    send_message(f'{message.author}, access denied')
        else:
            my_file = Path("flask/images/user/" + newimagename)
            if my_file.is_file():
                send_message(f"{message.author}, {newimagename} already exists")
                return
            if imagename[-4:] != newimagename[-4:] and not moderator:
                send_message(f"{message.author}, sowwy, format change isn't allowed")
                return
            try:
                os.rename('flask/images/user/' + imagename, 'flask/images/user/' + newimagename)
                db.update_link_filename(imagename, newimagename)
                db.update_owner_filename(imagename, newimagename)
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
    mypath = 'flask/images/user/'
    onlyfiles = [f for f in os.listdir(mypath) if isfile(join(mypath, f))]
    result = db.get_links_filenames()
    lst_result = [i[0] for i in result]
    words = [x if set(x.split()).intersection(lst_result) else x + '*' for x in onlyfiles]
    if act == '!search':
        return words
    linkwords = [x for x in words if '*' not in x]
    return words, linkwords


def check_owner(message_author, imagename):  # check if user owns image
    result = db.check_owner(imagename, message_author)
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
    db.remove_srfavs(remove_song)
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
            words = [f for f in os.listdir('flask/images/user/') if isfile(join('flask/images/user/', f))]
            if not set(imagename.split()).intersection(words):
                response_not_found.append(imagename)
                continue
            else:
                response_denied.append(imagename)
        else:
            try:
                os.remove('flask/images/user/' + imagename)
                remove_links.append((imagename,))
                remove_owners.append((imagename,))
                response_deleted.append(imagename)
                file_deleted = True
            except:
                response_not_found.append(i.lower())
    response = []
    if file_deleted:
        db.remove_link(remove_links)
        db.remove_owner(remove_owners)
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
    if not g.keys.get('ChannelID'):
        response = requests.get(f'https://api.twitch.tv/helix/users?login={g.channel}', 
                                    headers={'Client-ID': g.ClientID, 
                                                'Authorization': f'Bearer {g.ClientOAuth}'}).json()
        g.ChannelID = response['data'][0]['id']
        print(f'ChannelID = {g.ChannelID}')
    channel_info = requests.get(f"https://api.twitch.tv/kraken/channels/{g.ChannelID}",
                                headers={"Client-ID": g.ClientID,
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
    requests.put(f"https://api.twitch.tv/kraken/channels/{g.ChannelID}",
                 headers={"Client-ID": g.ClientID,
                          "Accept": "application/vnd.twitchtv.v5+json",
                          "Authorization": f'OAuth {g.ClientOAuth}'},
                 data={"channel[status]": channel_status,
                       "channel[game]": channel_game})
    send_message(f'{username}, done')


def np_response(mode):
    current_time = Player.get_time()
    current_time = seconds_convert(current_time)
    send_message(f'{mode}: {g.np} - {g.sr_url} - {current_time}/{g.np_duration}')


def try_timecode(message, url, timecode_pos, save=False, ytsearch=False):
    try:
        if timecode_pos is None:
            raise IndexError
        timecode = message.parts[timecode_pos]
        if re.match(timecode_re, timecode):
            timecode = timecode_re.sub(r'\2', timecode)
            sr_download_queue.new_task(download_clip, url, message.author, user_duration=timecode, ytsearch=ytsearch, save=save)
            return
        send_message(f'{message.author}, timecode error')
    except IndexError:
        sr_download_queue.new_task(download_clip, url, message.author, ytsearch=ytsearch, save=save)


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
        px_download_queue.new_task(Pixiv.save_pixiv_art, imagename, message.author, pxid, setpic=True, save=True)
    except IndexError:
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        px_download_queue.new_task(Pixiv.save_pixiv_art, db.numba, message.author, pxid, 'temp/', setpic=True)
        db.update_imgcount(int(db.numba) + 1)


def save_pixiv(message, pattern, group, group2, url):
    try:
        imagename = fixname(message.parts[2].lower())
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        px_download_queue.new_task(Pixiv.save_pixiv_art, imagename, message.author, pxid, save=True, save_msg=True)
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
    result = db.check_srfavs_list(username)
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
    g.last_link = ''
    link = db.get_link(selected)
    if link:
        g.last_link = link[0][0]
    set_image('user/', selected)


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
    elif re.match(link_re, url):
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
            folder = 'user/'
            imagename = while_is_file(folder, fixname(message.parts[2].lower()), f'{file_format}')
            do_save = True
        except IndexError:
            folder = 'temp/'
            imagename = db.numba
            db.update_imgcount(int(db.numba) + 1)
        filepath = f'flask/images/{folder}{imagename}{file_format}'
        with open(filepath, 'wb') as download:
            download.write(r.content)
        if Path(filepath).is_file():
            image = f'{imagename}{file_format}'
            if do_draw:
                set_image(folder, image)
            if do_save:
                db.add_link(url, image)
                db.add_owner(image, message.author)
            if do_save_response:
                send_message(f'{message.author}, {image} saved')
        else:
            send_message(f'{message.author}, download error')
    else:
        send_message(f"{message.author}, no link")


def send_message(message: str, pipe=False):
    if pipe:
        return message.split()
    g.twitch_socket.send(bytes(f"PRIVMSG #{g.channel} :{message}\r\n", "UTF-8"))


def player_start_playing():
    for _ in range(1500):
        if Player.active_state():
            return
        time.sleep(0.01)


def playmusic():
    if not g.playlist:
        return
    song = g.playlist.pop(0)
    Player.set_media(song.audio_link)
    Player.play()
    g.np, g.np_duration, g.sr_url, g.sr_user = song.title, song.duration, song.link, song.username
    if song.user_duration is not None:
        Player.set_time(song.user_duration)
    player_start_playing()
    while Player.active_state():
        time.sleep(2)


def download_clip(url: str, username: str, user_duration=None, ytsearch=False, save=False):
    """
    add song to playlist/favorites
    url: youtube link/id or search query
    username: twitch username
    user_duration: timecode (song start time)
    ytsearch: youtube search query
    save: add to favorites
    """
    if not save and not is_mod(username):
        g.sr_cooldowns[username] = time.time()
    if ytsearch:
        query = requests.utils.quote(url)
        result = requests.get('https://www.googleapis.com/youtube/v3/search?'
                              f'part=snippet&maxResults=1&type=video&q={query}&key={g.GoogleKey}',
                              headers={'Accept': 'application/json'}).json()
        items = result.get("items")
        if not items:
            logger.error(result)
            send_message(f'{username}, no results')
            return
        url = f'https://youtu.be/{items[0]["id"]["videoId"]}'
    try:
        info = g.ydl.extract_info(url, download=False)
    except DownloadError:
        send_message(f'{username}, unsupported url')
        return
    audio_link = info['formats'][0]['url']
    if audio_link.startswith('https://manifest.googlevideo.com/api/manifest/dash/'):
        try:
            audio_link = re.match(r'(.*)<\/BaseURL>', requests.get(audio_link).text.split('<BaseURL>')[1]).group(1)
        except Exception as e:
            send_message(f'{username}, unsupported url')
            logger.exception(e)
            return
    title = info['title']
    duration = info['duration']
    user_duration = check_sr_req(user_duration, duration, username)
    if user_duration is False:
        del g.sr_cooldowns[username]
        return
    url = f"https://youtu.be/{info['id']}"
    if save:
        if user_duration is None:
            db.add_srfavs(title, duration, 0, url, username)
            send_message(f'{username}, {title} - {url} - added to favorites')
        else:
            db.add_srfavs(title, duration, user_duration, url, username)
            send_message(f'{username}, {title} [{seconds_convert(user_duration)}] - {url} - added to favorites')
        return
    duration = seconds_convert(duration)
    song = Song(audio_link, title, duration, user_duration, url, username)
    g.playlist.append(song)
    response = new_song_response([], song)
    send_message(f'+ {response[0]}')
    sr_queue.new_task(playmusic)


def check_sr_req(user_duration, duration, username):
    if user_duration is not None:
        if not isinstance(user_duration, int):
            user_duration = timecode_convert(user_duration)
        if user_duration > duration:
            send_message(f'{username}, time exceeds duration! [{seconds_convert(duration)}]')
            return False
    if duration > g.sr_max_song_duration and not is_mod(username):
        send_message(f'{username}, '
                     f'{seconds_convert(duration)} > max duration[{seconds_convert(g.sr_max_song_duration)}]')
        return False
    return user_duration


def sr(username):
    if not g.sr:
        return False
    return not sr_user_cooldown(username)


def sr_user_cooldown(username):
    sr_cooldown = g.sr_user_cooldown
    if not sr_cooldown:
        return False
    user_cooldown = g.sr_cooldowns.get(username)
    if not user_cooldown:
        return False
    time_diff = time.time() - user_cooldown
    if time_diff < sr_cooldown:
        send_message(f'{username}, your cooldown is {seconds_convert(sr_cooldown - time_diff, explicit=True)}')
        return True
    del g.sr_cooldowns[username]
    return False


def next_song_in():
    if Player.active_state():
        current_time = Player.get_time()
        np_duration = timecode_convert(g.np_duration)
        return np_duration - current_time
    return 0


def new_song_response(response: list, song: Song):
    next_in = next_song_in()
    if not next_in and sr_queue.q.empty():
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


def no_args(message: Message, command: str):
    return message.content[len(g.prefix):] == command


def check_chat_notify(username: str):
    if any(x == username for x in g.notify_in_progress):
        return
    if any(d['recipient'] == username for d in g.notify_list):
        g.notify_in_progress.append(username)
        response = []
        for i in g.notify_list:
            if i['recipient'] == username:
                response.append(f'{i["sender"]}: {i["message"]} '
                                f'[{seconds_convert(time.time() - i["date"], explicit=True)} ago]')
        if response:
            response_str = f'{username}, {"; ".join(response)}'
            if len(response_str) > 480:
                for i in divide_chunks(response_str, 480, response, joinparam='; '):
                    send_message(i)
                    time.sleep(1)
            else:
                send_message(response_str)
        g.notify_list = [d for d in g.notify_list if d['recipient'] != username]
        g.notify_in_progress.remove(username)


def convert_type(string: str):
    if string.isdigit():
        return int(string)
    try:
        return float(string)
    except ValueError:
        pass
    lower_string = string.lower()
    if lower_string == 'none':
        return None
    elif lower_string == 'true':
        return True
    elif lower_string == 'false':
        return False
    elif string.startswith('{'):
        try:
            return json.loads(string)
        except JSONDecodeError:
            pass
    return string
