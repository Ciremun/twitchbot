import sqlite3

conn = sqlite3.connect('data/db/picturebot.db')
c = conn.cursor()

with conn:
    c.execute('delete from owners')
    c.execute('delete from links')
    c.execute('delete from moderators')
    c.execute('delete from banned')
    c.execute('delete from srfavs')
    c.execute('vacuum')
