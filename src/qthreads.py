from .classes import QueueThread

main_queue = QueueThread('main')
sr_queue = QueueThread('sr')
sr_download_queue = QueueThread('srdl')
px_download_queue = QueueThread('pxdl')
utils_queue = QueueThread('utils')
tts_queue = QueueThread('tts')
