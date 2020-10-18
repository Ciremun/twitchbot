import random
import time
import os
from os.path import isfile, join
from threading import Thread
from pathlib import Path
from os import listdir

from pixivapi import Client, RankingMode, BadApiResponse

import src.db as db
import src.utils as u
import src.config as g
from .server import set_image

class ThreadPixiv(Thread):

    def __init__(self, name):
        Thread.__init__(self)
        self.name = name
        self.client = Client()
        self.allranking = []
        self.artpath = Path('flask/images/pixiv/')
        self.start()

    def run(self):
        pass # @@@ broken
        # self.pixiv_init()

    def download_art(self, obj, size, filename):
        obj.download(directory=self.artpath,
                     size=size, filename=filename)

    def random_pixiv_art(self):  # download and set random pixiv art
        try:
            ranking = random.choice(self.allranking)
            fetchmode = random.random()  # ranked or ranked related art 20/80
            if fetchmode > 0.2:
                related_offset = 0
                allrelated = []
                for _ in range(4):
                    related = self.client.fetch_illustration_related(ranking.id,
                                                                     offset=related_offset).get('illustrations')
                    allrelated = u.sort_pixiv_arts(related, allrelated)
                    related_offset += 30
                illustration = random.choice(list(allrelated))
            else:
                illustration = ranking
            print(f'art id: {illustration.id}')
            artid = illustration.id
            g.lastlink = f'https://www.pixiv.net/en/artworks/{artid}'
            g.last_rand_img = f'{artid}.png'
            art = Path(f'flask/images/pixiv/{artid}.png')
            if not art.is_file():
                self.download_art(illustration, g.pixiv_size, artid)
                if not art.is_file():
                    os.rename(f'flask/images/pixiv/{artid}.jpg', f'flask/images/pixiv/{artid}.png')
            set_image('pixiv/', f'{artid}.png')
        except BadApiResponse as pixiv_exception:  # reconnect
            if 'Status code: 400' in str(pixiv_exception):
                self.pixiv_init()
            self.random_pixiv_art()
        except Exception as e:
            if 'RemoteDisconnected' in str(e):
                self.random_pixiv_art()

    def save_pixiv_art(self, namesave, owner, artid, folder='user/', setpic=False, save=False, save_msg=False):
        """
        save pixiv art by art id
        :param save_msg: whether send <image saved> message
        :param save: whether save image
        :param setpic: whether set image
        :param namesave: filename
        :param owner: twitch username
        :param artid: pixiv art id
        :param folder: image save folder inside flask app static folder
        """
        try:
            print(f'art id: {artid}')
            namesave = u.while_is_file(folder, namesave, '.png')
            namesave = u.while_is_file(folder, namesave, '_p0.png')
            savedart = self.client.fetch_illustration(int(artid))
            self.download_art(savedart, g.pixiv_size, namesave)
            if os.path.isdir('flask/images/pixiv/' + namesave):
                mypath2 = 'flask/images/pixiv/' + namesave
                onlyfiles = [f for f in listdir(mypath2) if isfile(join(mypath2, f))]
                for i in onlyfiles:
                    os.rename(f'flask/images/pixiv/{namesave}/{i}', f'flask/images/{folder}{namesave}{i[8:-4]}.png')
                    if save:
                        db.add_link(f'https://www.pixiv.net/en/artworks/{artid}', f'{namesave}{i[8:-4]}.png')
                        db.add_owner(f'{namesave}{i[8:-4]}.png', owner)
                    if setpic:
                        set_image(folder, f'{namesave}{i[8:-4]}.png')
                        time.sleep(1.5)
                os.rmdir(f'flask/images/pixiv/{namesave}')
                if save_msg:
                    u.send_message(f'{owner}, {namesave}.png saved')
                return
            art = Path(f'flask/images/pixiv/{namesave}.png')
            filepath = f'flask/images/pixiv/{namesave}.png'
            if not art.is_file():
                filepath = f'flask/images/pixiv/{namesave}.jpg'
            os.rename(filepath, f'flask/images/{folder}{namesave}.png')
            if save:
                db.add_link(f'https://www.pixiv.net/en/artworks/{artid}', f'{namesave}.png')
                db.add_owner(f'{namesave}.png', owner)
            if setpic:
                set_image(folder, f'{namesave}.png')
            if save_msg:
                u.send_message(f'{owner}, {namesave}.png saved')
        except BadApiResponse as pixiv_exception:  # reconnect
            print(f'badapiresponse - {pixiv_exception}')
            if 'Status code: 404' in str(pixiv_exception):
                u.send_message(f'{owner}, {artid} not found')
                return
            if 'Status code: 400' in str(pixiv_exception):
                self.pixiv_init()
            self.save_pixiv_art(namesave, owner, artid, folder, setpic, save, save_msg)
        except Exception as e:
            if 'RemoteDisconnected' in str(e):
                self.save_pixiv_art(namesave, owner, artid, folder, setpic, save, save_msg)

    def pixiv_init(self):
        try:
            self.allranking *= 0
            self.client.authenticate(g.keys['PixivToken'])
            print('pixiv auth √')
            rank_offset = 30
            ranking1 = self.client.fetch_illustrations_ranking(
                mode=RankingMode.DAY).get('illustrations')  # check 500 arts, filter by tags and ratio
            self.allranking = u.sort_pixiv_arts(ranking1, self.allranking)
            for i in range(16):
                print(f'\rpixiv load={int(i / 16 * 100) + 7}%', end='')
                ranking = self.client.fetch_illustrations_ranking(mode=RankingMode.DAY,
                                                                  offset=rank_offset).get('illustrations')
                self.allranking = u.sort_pixiv_arts(ranking, self.allranking)
                rank_offset += 30
            print()
        except BadApiResponse:
            time.sleep(30)
            self.run()

Pixiv = ThreadPixiv("ThreadPixiv")
