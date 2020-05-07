import pafy
import youtube_dl
import time
import requests
import threading
import os
import random
import typing
import queue
import io
import base64
import modules.globals as g

from math import floor
from pathlib import Path
from datetime import datetime
from os import listdir
from os.path import isfile, join
from PIL import Image
from modules.regex import *
from modules.pixiv import Pixiv


class Song(typing.NamedTuple):
    path: str
    filename: str
    title: str
    duration: str
    user_duration: int
    link: str
    username: str


def imgur_utils_wrap(username, messagesplit, message):
    file = messagesplit[1]
    db_link = g.db.get_link(file)
    if db_link:
        send_message(f'{username}, {file} - {db_link[0][0]}')
        return
    path = f'data/custom/{file}'
    if not Path(path).is_file():
        send_message(f'{username}, file {file} not found')
        return
    encoded_file = imgur_convert_image(path)
    link = imgur_upload_image(encoded_file)
    if not re.match(regex, link):
        send_message(f'{username}, file upload error [{link}]')
        return
    send_message(f'{username}, {file} - {link}')
    g.db.add_link(link, file)


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


def rename_command(username, messagesplit):  # rename function for image owners
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


def sr_favs_del(username, messagesplit, songs):
    response, remove_song, target_not_found, song_removed_response = [], [], [], []
    for i in range(1, len(messagesplit)):
        try:
            index = int(messagesplit[i])
            if not 0 <= index <= len(songs):
                target_not_found.append(messagesplit[i])
                continue
            song = songs[index - 1]
            user_duration = song.user_duration
            if user_duration is None:
                user_duration = 0
            remove_tup = (
                song.path, song.filename, song.title, timecode_convert(song.duration), user_duration, song.link,
                username)
            if remove_tup not in remove_song:
                song_removed_response.append(f'{song.title}'
                                             f'{"" if not user_duration else f" [{seconds_convert(user_duration)}]"}')
                remove_song.append(remove_tup)
                g.playlist = [x for x in g.playlist if x != song]
                try:
                    os.remove(song.path)
                except:
                    pass
        except ValueError:
            target = messagesplit[i]
            song_found = False
            for song in songs:
                if target.lower() in song.title.lower():
                    song_found = True
                    user_duration = song.user_duration
                    if user_duration is None:
                        user_duration = 0
                    remove_tup = (
                        song.path, song.filename, song.title, timecode_convert(song.duration), user_duration, song.link,
                        username)
                    if remove_tup not in remove_song:
                        song_removed_response.append(f'{song.title}'
                                                     f'{"" if not user_duration else f" [{seconds_convert(user_duration)}]"}')
                        remove_song.append(remove_tup)
                        g.playlist = [x for x in g.playlist if x != song]
                        try:
                            os.remove(song.path)
                        except:
                            pass
            if not song_found:
                target_not_found.append(messagesplit[i])
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


def del_chat_command(username, messagesplit):
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


def delete_ban_mod(response, boolean, str1, str2, username):
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


def ban_mod_commands(username, messagesplit, str1, str2, check_func, db_call, check_func_result):
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
    delete_ban_mod(response, boolean, str1, str2, username)


def sr_get_list(username, messagesplit):
    if not g.playlist:
        send_message(f'{username}, playlist is empty')
        return
    sr_list = [f'{x.title} [{seconds_convert(x.user_duration)}] #{i}'
               if x.user_duration is not None else f'{x.title} #{i}' for i, x in enumerate(g.playlist, start=1)]
    sr_str = ", ".join(sr_list)
    sr_list = divide_chunks(sr_str, 470, sr_list, joinparam=', ')
    send_list(username, messagesplit, sr_str, sr_list, 1, "list")


def change_stream_settings(username, messagesplit, setting):
    channel_info = requests.get(f"https://api.twitch.tv/kraken/channels/{g.channel_id}",
                                headers={"Client-ID": g.client_id,
                                         "Accept": "application/vnd.twitchtv.v5+json"}).json()
    if setting == 'title':
        set_title = " ".join(messagesplit[1:])
        if not set_title:
            send_message(f'Title: {channel_info["status"]}')
        else:
            change_status_game(set_title, channel_info["game"], username)
    elif setting == 'game':
        set_game = " ".join(messagesplit[1:])
        if not set_game:
            send_message(f'Game: {channel_info["game"]}')
        else:
            change_status_game(channel_info["status"], set_game, username)


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


def try_timecode(url, messagesplit, username, timecode_pos, save=False, yt_request=True, ytsearch=False,
                 folder='data/sounds/sr/'):
    try:
        if timecode_pos is None:
            raise IndexError
        timecode = messagesplit[timecode_pos]
        if re.match(timecode_re, timecode):
            g.sr_download_queue.new_task(download_clip, url, username, user_duration=timecode, yt_request=yt_request,
                                         folder=folder, ytsearch=ytsearch, save=save)
            return
        send_message(f'{username}, timecode error')
    except IndexError:
        g.sr_download_queue.new_task(download_clip, url, username, yt_request=yt_request, folder=folder,
                                     ytsearch=ytsearch, save=save)


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
        g.px_download_queue.new_task(Pixiv.save_pixiv_art, imagename, username, pxid, setpic=True, save=True)
    except IndexError:
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        g.px_download_queue.new_task(Pixiv.save_pixiv_art, g.db.numba, username, pxid, 'data/images/', setpic=True)
        g.db.update_imgcount(int(g.db.numba) + 1)


def save_pixiv(pattern, group, group2, url, messagesplit, username):
    try:
        imagename = fixname(messagesplit[2].lower())
        try:
            pxid = int(pattern.sub(group, url))
        except ValueError:
            pxid = int(pattern.sub(group2, url))
        g.px_download_queue.new_task(Pixiv.save_pixiv_art, imagename, username, pxid, save=True, save_msg=True)
    except IndexError:
        pass


def sr_download(url, messagesplit, username, timecode_pos, save=False, folder='data/sounds/sr/'):
    if re.match(youtube_link_re, url):
        try_timecode(url, messagesplit, username, timecode_pos, save=save)
    elif re.match(youtube_id_re, url):
        video_id = youtube_id_re.sub(r'\2', url)
        url = f'https://www.youtube.com/watch?v={video_id}'
        try_timecode(url, messagesplit, username, timecode_pos, save=save)
    elif re.match(soundcloud_re, url):
        try_timecode(url, messagesplit, username, timecode_pos, folder=folder, save=save, yt_request=False)
    else:
        return False
    return True


def get_srfavs_dictlist(username):
    result = g.db.check_srfavs_list(username)
    if not result:
        return False
    return [Song(song[0], song[1], song[2], seconds_convert(song[3]),
                 (None if song[4] == 0 else song[4]), song[5], username) for song in result]


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


def fix_pafy_url(pafy_url: str, pafy_obj):
    if 'videoplayback' in pafy_url:
        return pafy_url
    return pafy_obj.getbest().url


def playmusic():  # play song from playlist
    if not g.playlist:
        return
    song = g.playlist.pop(0)
    if song.path == 'None':
        pafy_obj = get_pafy_obj(song.link)
        if not pafy_obj:
            return
        pafy_url = pafy_obj.getbestaudio()
        if not pafy_url:
            send_message(f'no audio for {song.link}')
            return
        url = fix_pafy_url(pafy_url.url, pafy_obj)
        media = g.PlayerInstance.media_new(url)
    else:
        media = g.PlayerInstance.media_new(song.path)
    media.get_mrl()
    g.Player.set_media(media)
    g.Player.play()
    g.np, g.np_duration, g.sr_url = song.title, song.duration, song.link
    if song.user_duration is not None:
        g.Player.set_time(song.user_duration * 1000)
    sr_start_playing()
    while player_good_state():
        time.sleep(2)


def get_pafy_obj(url: str):
    pafy_obj = None
    while not pafy_obj:
        try:
            pafy_obj = pafy.new(url)
        except OSError as e:
            if 'This video is unavailable.' in str(e):
                send_message(f'{url} is unavailable.')
                return
            print('OSError (pafy/youtubedl bug?) in pafy_link, retrying..')
    return pafy_obj


def download_clip(url, username, user_duration=None, yt_request=True, folder='data/sounds/sr/', ytsearch=False,
                  save=False):
    """
    download .wav song file, add song to favorites, add song to playlist
    :param url: youtube/soundcloud link or youtube search query
    :param username: twitch username
    :param user_duration: timecode (song start time)
    :param yt_request: youtube url
    :param folder: .wav file folder
    :param ytsearch: youtube search query
    :param save: add to favorites
    """
    if not checkmodlist(username):
        g.Main.sr_cooldowns[username] = time.time()
    if yt_request and not ytsearch:
        pafy_obj = get_pafy_obj(url)
        if not pafy_obj:
            return
        duration = pafy_obj.length
        user_duration = check_sr_req(user_duration, duration, username)
        if user_duration is False:
            return
        path = 'None'
        filename = 'None'
        title = pafy_obj.title
        url = f'https://youtu.be/{pafy_obj.videoid}'
    else:
        name = ''.join(random.choices('qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM' + '1234567890', k=10))
        name = while_is_file(folder, name, '.wav')
        path = f'{folder}{name}.wav'
        filename = f'{name}.wav'
        ydl_opts = {
            'quiet': True,
            'nocheckcertificate': True,
            'max_downloads': '1',
            'cookiefile': 'data/special/cookies.txt',
            'ratelimit': g.ytdl_rate,
            'format': 'bestaudio/best',
            'outtmpl': path,
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
            try:
                info_dict = ydl.extract_info(url, download=False)
            except youtube_dl.utils.DownloadError as e:
                if 'HTTP Error 404: Not Found' in str(e):
                    send_message(f'{url} HTTP Error 404: Not Found')
                else:
                    send_message(f'{url} is unavailable.')
                return
            if ytsearch:
                try:
                    entries = info_dict['entries'][0]
                except IndexError:
                    send_message(f'{username}, no results for {url}')
                    return
                title = entries.get('title', None)
                duration = entries.get('duration', 0)
                url = f"https://youtu.be/{entries.get('id', None)}"
                filename = 'None'
                path = 'None'
            else:
                title = info_dict.get('title', None)
                duration = info_dict.get('duration', 0)
            user_duration = check_sr_req(user_duration, duration, username)
            if user_duration is False:
                return
            if not ytsearch:
                ydl.prepare_filename(info_dict)
                ydl.download([url])
    if save:
        if user_duration is None:
            g.db.add_srfavs(path, filename, title, duration, 0, url, username)
            send_message(f'{username}, {title} - {url} - added to favorites')
        else:
            g.db.add_srfavs(path, filename, title, duration, user_duration, url, username)
            send_message(f'{username}, {title} [{seconds_convert(user_duration)}] - {url} - added to favorites')
        return
    duration = seconds_convert(duration)
    song = Song(path, filename, title, duration, user_duration, url, username)
    g.playlist.append(song)
    response = new_song_response([], song)
    send_message(f'+ {response[0]}')
    g.sr_queue.new_task(playmusic)


def check_sr_req(user_duration, duration, username):
    if user_duration is not None:
        user_duration = timecode_convert(user_duration)
        if user_duration > duration:
            send_message(f'{username}, time exceeds duration! [{seconds_convert(duration)}]')
            return False
    if duration > g.max_duration and not checkmodlist(username):
        send_message(f'{username}, '
                     f'{seconds_convert(duration)} > max duration[{seconds_convert(g.max_duration)}]')
        return False
    return user_duration


def sr(username):
    if not g.sr:
        return False
    return not sr_user_cooldown(username)


def sr_user_cooldown(username: str):
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
