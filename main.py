
if __name__ == '__main__':
    from src.utils import timecode_convert
    from src.chat import ChatThread
    import src.server as server
    import src.config as g
    g.sr_max_song_duration = timecode_convert(g.cfg['sr_max_song_duration'])
    g.sr_user_cooldown = timecode_convert(g.cfg['sr_user_cooldown'])
    ChatThread('chat').start()
    server.run()
