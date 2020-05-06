import re

regex = re.compile(
    r'^(?:http|ftp)s?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # links

timecode_re = re.compile(r'^(?:(?:(\d+):)?(\d+):)?(\d+)$')

youtube_link_re = re.compile(
    r'http(?:s?)://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?')

youtube_id_re = re.compile(r'^([/]?watch\?v)?=([\w-]{11})$')

soundcloud_re = re.compile(r'^(https://)?(www.)?(m\.)?soundcloud\.com/([\w\-.]+/[\w\-.]+)$')

pixiv_re = re.compile(r'^(https://)?(www.)?pixiv\.net/(en)?(artworks)?/(\d+)?(artworks)?(/(\d+)?)?$')

pixiv_src_re = re.compile(r'^(https://)?(www.)?i\.pximg\.net/[\w\-]+/\w+/\d+/\d+/\d+/\d+/\d+/\d+/(('
                          r'\d+)_p\d+\w+\.\w+)?((\d+)_p\d+\.\w+)?$')

chat_msg = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")
