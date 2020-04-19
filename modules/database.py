import sqlite3
import threading

from modules.decorators import conn_query, regular_query


class ThreadDB(threading.Thread):

    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.conn = sqlite3.connect('../data/db/picturebot.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.numba = str(self.get_imgcount()[0][0])

    @conn_query
    def add_owner(self, filename, owner):
        self.c.execute('INSERT INTO owners (filename, owner) VALUES (:filename, :owner)',
                       {'filename': filename, 'owner': owner})

    @conn_query
    def remove_owner(self, filename):
        self.c.executemany('DELETE FROM owners WHERE filename = ?', filename)

    @conn_query
    def add_srfavs(self, song, owner, filename, user_duration, link, duration):
        self.c.execute('INSERT INTO srfavs (song, owner, filename, user_duration, link, duration) '
                       'VALUES (:song, :owner, :filename, :user_duration, :link, :duration)',
                       {'song': song, 'owner': owner, 'filename': filename, 'user_duration': user_duration,
                        'link': link, 'duration': duration})

    @conn_query
    def remove_srfavs(self, data):
        self.c.executemany("DELETE FROM srfavs WHERE song = ? and owner = ? and filename = ? and "
                           "user_duration = ? and link = ? and duration = ?", data)

    @regular_query
    def check_srfavs_list(self, owner):
        self.c.execute('SELECT song, filename, user_duration, link, duration FROM srfavs WHERE owner = :owner',
                       {'owner': owner})
        return self.c.fetchall()

    @regular_query
    def get_srfavs_filenames(self):
        self.c.execute('SELECT filename FROM srfavs')
        return self.c.fetchall()

    @regular_query
    def check_owner(self, filename, owner):
        self.c.execute('SELECT owner FROM owners WHERE filename = :filename AND owner = :owner', {'filename': filename,
                                                                                                  'owner': owner})
        return self.c.fetchall()

    @regular_query
    def check_ownerlist(self, owner):
        self.c.execute('SELECT filename FROM owners WHERE owner = :owner', {'owner': owner})
        return self.c.fetchall()

    @conn_query
    def update_owner_filename(self, filename, new_filename):
        self.c.execute('UPDATE owners SET filename = :new_filename WHERE filename = :filename',
                       {'filename': filename,
                        'new_filename':
                            new_filename})

    @conn_query
    def add_link(self, link, filename):
        self.c.execute('INSERT INTO links (link, filename) VALUES (:link, :filename)',
                       {'link': link, 'filename': filename})

    @conn_query
    def remove_link(self, filename):
        self.c.executemany('DELETE FROM links WHERE filename = ?', filename)

    @conn_query
    def update_link_filename(self, filename, new_filename):
        self.c.execute('UPDATE links SET filename = :new_filename WHERE filename = :filename', {'filename': filename,
                                                                                                'new_filename':
                                                                                                    new_filename})

    @regular_query
    def check_filename_has_link(self, filename):
        self.c.execute('SELECT filename FROM links WHERE filename = :filename', {'filename': filename})
        return self.c.fetchall()

    @regular_query
    def get_links_filenames(self):
        self.c.execute('SELECT filename FROM links')
        return self.c.fetchall()

    @regular_query
    def get_links_and_filenames(self):
        self.c.execute('SELECT link, filename FROM links')
        return self.c.fetchall()

    @regular_query
    def get_link(self, filename):
        self.c.execute('SELECT link FROM links WHERE filename = :filename', {'filename': filename})
        return self.c.fetchall()

    @regular_query
    def get_imgcount(self):
        self.c.execute('SELECT count FROM imgcount')
        return self.c.fetchall()

    @conn_query
    def update_imgcount(self, count):
        self.numba = str(int(self.numba) + 1)
        self.c.execute('UPDATE imgcount SET count = :count', {'count': count})

    @regular_query
    def check_if_mod(self, username):
        self.c.execute('SELECT username FROM moderators WHERE username = :username', {'username': username})
        return self.c.fetchall()

    @regular_query
    def check_moderators(self):
        self.c.execute('SELECT username FROM moderators')
        return self.c.fetchall()

    @conn_query
    def add_mod(self, username):
        self.c.executemany("INSERT INTO moderators (username) VALUES (?)", username)

    @conn_query
    def remove_mod(self, username):
        self.c.executemany("DELETE FROM moderators WHERE username = ?", username)

    @regular_query
    def check_if_banned(self, username):
        self.c.execute('SELECT username FROM banned WHERE username = :username', {'username': username})
        return self.c.fetchall()

    @regular_query
    def check_banned(self):
        self.c.execute('SELECT username FROM banned')
        return self.c.fetchall()

    @conn_query
    def add_ban(self, username):
        self.c.executemany("INSERT INTO banned (username) VALUES (?)", username)

    @conn_query
    def remove_ban(self, username):
        self.c.executemany("DELETE FROM banned WHERE username = ?", username)

    @conn_query
    def sql_query(self, query):
        try:
            self.c.execute(query)
        except Exception as e:
            return [(str(e),)]
        return self.c.fetchall()


db = ThreadDB('ThreadDB')
