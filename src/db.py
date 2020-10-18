import sqlite3
import threading

conn = sqlite3.connect('bot.db', check_same_thread=False, isolation_level=None)
c = conn.cursor()

lock = threading.Lock()

def acquireLock(func):
    def wrapper(*args, **kwargs):
        try:
            lock.acquire(True)
            return func(*args, **kwargs)
        finally:
            lock.release()
    return wrapper

tables = [
"CREATE TABLE IF NOT EXISTS owners (id integer PRIMARY KEY, filename text NOT NULL, owner text NOT NULL)",
"""\
CREATE TABLE IF NOT EXISTS srfavs (id integer PRIMARY KEY, title text NOT NULL, \
duration integer NOT NULL, user_duration integer, link text NOT NULL, username text NOT NULL)\
""",
"CREATE TABLE IF NOT EXISTS links (id integer PRIMARY KEY, link text NOT NULL, filename text NOT NULL)",
"CREATE TABLE IF NOT EXISTS imgcount (id integer PRIMARY KEY, count integer NOT NULL)",
"CREATE TABLE IF NOT EXISTS moderators (id integer PRIMARY KEY, username text NOT NULL)",
"CREATE TABLE IF NOT EXISTS banned (id integer PRIMARY KEY, username text NOT NULL)"
]

for create_table_query in tables:
    c.execute(create_table_query)


@acquireLock
def add_owner(filename, owner):
    c.execute('INSERT INTO owners (filename, owner) VALUES (:filename, :owner)',
                    {'filename': filename, 'owner': owner})


@acquireLock
def remove_owner(filename):
    c.executemany('DELETE FROM owners WHERE filename = ?', filename)


@acquireLock
def add_srfavs(title, duration, user_duration, link, username):
    c.execute('INSERT INTO srfavs (title, duration, user_duration, link, username) '
                    'VALUES (:title, :duration, :user_duration, :link, :username)',
                    {'title': title, 'duration': duration, 'user_duration': user_duration, 
                    'link': link, 'username': username})


@acquireLock
def remove_srfavs(data):
    c.executemany("DELETE FROM srfavs WHERE title = ? and duration = ? and user_duration = ? "
                        "and link = ? and username = ?", data)


@acquireLock
def check_srfavs_list(username):
    c.execute('SELECT title, duration, user_duration, link FROM srfavs WHERE username = :username',
                    {'username': username})
    return c.fetchall()


@acquireLock
def check_owner(filename, owner):
    c.execute('SELECT owner FROM owners WHERE filename = :filename AND owner = :owner', {'filename': filename,
                                                                                                'owner': owner})
    return c.fetchall()


@acquireLock
def check_ownerlist(owner):
    c.execute('SELECT filename FROM owners WHERE owner = :owner', {'owner': owner})
    return c.fetchall()


@acquireLock
def update_owner_filename(filename, new_filename):
    c.execute('UPDATE owners SET filename = :new_filename WHERE filename = :filename', {'filename': filename,
                                                                                                'new_filename':
                                                                                                    new_filename})


@acquireLock
def add_link(link, filename):
    c.execute('INSERT INTO links (link, filename) VALUES (:link, :filename)',
                    {'link': link, 'filename': filename})


@acquireLock
def remove_link(filename):
    c.executemany('DELETE FROM links WHERE filename = ?', filename)


@acquireLock
def update_link_filename(filename, new_filename):
    c.execute('UPDATE links SET filename = :new_filename WHERE filename = :filename', {'filename': filename,
                                                                                            'new_filename':
                                                                                                new_filename})


@acquireLock
def get_links_filenames():
    c.execute('SELECT filename FROM links')
    return c.fetchall()


@acquireLock
def get_links_and_filenames():
    c.execute('SELECT link, filename FROM links')
    return c.fetchall()


@acquireLock
def get_link(filename):
    c.execute('SELECT link FROM links WHERE filename = :filename', {'filename': filename})
    return c.fetchall()


@acquireLock
def get_imgcount():
    c.execute('SELECT count FROM imgcount')
    return c.fetchone()

numba = get_imgcount()
if not numba:
    c.execute('INSERT INTO imgcount (count) VALUES (1)')
    numba = get_imgcount()
numba = numba[0]

@acquireLock
def update_imgcount(count):
    global numba
    numba = str(int(numba) + 1)
    c.execute('UPDATE imgcount SET count = :count', {'count': count})


@acquireLock
def check_if_mod(username):
    c.execute('SELECT username FROM moderators WHERE username = :username', {'username': username})
    return c.fetchall()


@acquireLock
def check_moderators():
    c.execute('SELECT username FROM moderators')
    return c.fetchall()


@acquireLock
def add_mod(username):
    c.executemany("INSERT INTO moderators (username) VALUES (?)", username)


@acquireLock
def remove_mod(username):
    c.executemany("DELETE FROM moderators WHERE username = ?", username)


@acquireLock
def check_if_banned(username):
    c.execute('SELECT username FROM banned WHERE username = :username', {'username': username})
    return c.fetchall()


@acquireLock
def check_banned():
    c.execute('SELECT username FROM banned')
    return c.fetchall()


@acquireLock
def add_ban(username):
    c.executemany("INSERT INTO banned (username) VALUES (?)", username)


@acquireLock
def remove_ban(username):
    c.executemany("DELETE FROM banned WHERE username = ?", username)


@acquireLock
def sql_query(query):
    try:
        c.execute(query)
    except Exception as e:
        return [(str(e),)]
    return c.fetchall()
