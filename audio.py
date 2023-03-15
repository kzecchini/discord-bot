import os
from pydub import AudioSegment
import yt_dlp
import re
from copy import deepcopy


DEFAULT_DOWNLOAD_PATH = "./data/audio"

# set youtube download globals
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],

}

def get_video_id(url):
    video_id = None
    pattern = "^.*(youtu.be\/|v\/|e\/|u\/\w+\/|embed\/|v=)([^#\&\?]*).*"
    m = re.match(pattern, url)
    if m:
        video_id = m[2]
    return video_id

def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    trim_ms = 0
    assert chunk_size
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size
    return trim_ms

def standardize_silence(sound, silence_len=250, silence_threshold=-50.0, chunk_size=10):
    # first remove silence
    start_trim = detect_leading_silence(sound, silence_threshold=silence_threshold, chunk_size=chunk_size)
    end_trim = detect_leading_silence(sound.reverse())
    duration = len(sound)    
    trimmed_sound = sound[start_trim:duration-end_trim]

    # add standard silence len
    silence = AudioSegment.silent(duration=silence_len) # or be explicit
    trimmed_sound = silence + trimmed_sound + silence
    return trimmed_sound


def split_video(fpath, start_time, end_time=None):
    sound = AudioSegment.from_mp3(fpath)
    if end_time:
        sound_range = sound[start_time:end_time]
    else:
        sound_range = sound[start_time:]
    sound = standardize_silence(sound_range)
    split_path = os.path.split(fpath)
    fname, ext = split_path[-1].split(".")
    fpath = os.path.join(split_path[0], fname)
    new_path = fpath + "_{}_{}.{}".format(start_time, end_time, ext)
    sound.export(new_path, format=ext)
    return new_path


# TODO: yt-dlp has a bug with start_time currently, so we go off of end time, and postprocess to cut the extra out before actual starting time
def download_and_process_clip(url: str, start_time_seconds: float, end_time_seconds: float, download_path=DEFAULT_DOWNLOAD_PATH):
    download_clip(url, start_time_seconds, end_time_seconds, download_path=download_path)
    video_id = get_video_id(url)
    fpath = f'{download_path}/{video_id}.mp3'
    clip_start_time = (start_time_seconds - end_time_seconds)*1000
    return split_video(fpath, start_time=clip_start_time)


def download_clip(url: str, start_time_seconds: float, end_time_seconds: float, download_path: str = DEFAULT_DOWNLOAD_PATH):
    # seems to be about 10 seconds off, minimum 15 second chunk

    def download_ranges(info_dict, ydl):
         return [{'start_time': start_time_seconds, 'end_time': end_time_seconds}]
    
    ydl_opts = deepcopy(YDL_OPTS)
    ydl_opts['outtmpl'] = os.path.join(download_path, '%(id)s.%(ext)s')

    ydl_opts['download_ranges'] = download_ranges

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=SBPvlxKrtpU"
    # url = "https://www.youtube.com/watch?v=PS3nii58Q1w"
    # url = "https://www.youtube.com/watch?v=mR3Plv8HuNk"

    start = 15*60 + 19
    end = 15*60 + 21

    download_and_process_clip(url, start, end, download_path="./data/test")
