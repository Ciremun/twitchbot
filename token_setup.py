import sqlite3

conn = sqlite3.connect('data/db/picturebot.db')
c = conn.cursor()

twitch_bot_token = input('twitch_bot_token?\n')
pixiv_token = input('pixiv_token?\n')
twitch_channel_id = input('twitch_channel_id?\n')
twitch_app_client_id = input('twitch_app_client_id?\n')
twitch_app_oauth = input('twitch_app_oauth[channel_editor]?\n')

with open('data/special/tokens', 'w') as f:
    f.write(f'twitch_bot_token {twitch_bot_token}\n'
            f'pixiv_token {pixiv_token}\n'
            f'twitch_channel_id {twitch_channel_id}\n'
            f'twitch_app_client_id {twitch_app_client_id}\n'
            f'twitch_app_oauth[channel_editor] {twitch_app_oauth}')
with conn:
    c.execute(f'delete from owners')
    c.execute(f'delete from links')
    c.execute(f'delete from moderators')
    c.execute(f'delete from banned')
    c.execute(f'delete from srfavs')
