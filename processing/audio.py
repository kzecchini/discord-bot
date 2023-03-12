import os
import string
from pydub import AudioSegment
from pydub.silence import split_on_silence
import logging
import sqlite3
import youtube_dl
import re


# get root logger for package
logger = logging.getLogger()

def my_hook(d):
    if d['status'] == 'finished':
        logging.info('Done downloading, now converting ...')

# set youtube download globals
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'logger': logger,
    'outtmpl': './data/audio/%(id)s_%(epoch)s.%(ext)s',
    'progress_hooks': [my_hook],
}

# seconds
MAX_DOWNLOAD_LEN = 600
# milliseconds
MAX_CLIP_LEN = 8000

DATA_PATH = './data'

def get_files(path):
    filenames = []
    for filename in os.listdir(path):
        rel_path = os.path.join(path, filename)
        if os.path.isfile(rel_path):
            filenames.append(rel_path)
    return filenames


def clean_message(s):
    exclude = set(string.punctuation)
    s = (''.join(ch for ch in s if ch not in exclude)).lower()
    return s


def save_audio_chunks(audio_file, target_dir, min_silence_len=500, 
                      silence_thres=-16, format="mp3"):
    outpath = os.path.join(target_dir, os.path.split(audio_file)[-1])
    outpath = outpath.split(".")[0] + "_{:2d}" + ".mp3"

    sound = AudioSegment.from_mp3(audio_file)
    chunks = split_on_silence(sound, min_silence_len=min_silence_len,
                              silence_thresh=silence_thres)
    for i, chunk in enumerate(chunks):
        chunk.export(outpath.format(i), format=format)



def get_video_id(url):
    video_id = None
    pattern = "^.*(youtu.be\/|v\/|e\/|u\/\w+\/|embed\/|v=)([^#\&\?]*).*"
    m = re.match(pattern, url)
    if m:
        video_id = m[2]
    return video_id


def download_video(url, ydl_opts, fpath):
    curr_path = check_videos(url, fpath) 
    
    if curr_path is not None:
        logging.info("already found youtube file")
        return curr_path
    
    else:
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info['duration'] > MAX_DOWNLOAD_LEN:
                    logging.info("Video too long to download!")
                    raise Exception
                else:
                    ydl.download([url])
        except Exception as e:
            raise e
        return check_videos(url, fpath)


def convert_time(t):
    mins, secs = map(int, t.split(":"))
    millis = (secs + mins*60)*1000
    return millis
    

def check_videos(url, path):
    filenames = get_files(path)
    filenames = [filename for filename in filenames if len(filename.split("_")) == 2]
    filename_ids = {os.path.split(filename)[-1].split("_")[0]: filename for filename in filenames}
    video_id = get_video_id(url)
    for fid, fname in filename_ids.items():
        if (fid == video_id):
            return fname


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


def split_video(fpath, start_time, end_time):
    sound = AudioSegment.from_mp3(fpath)
    sound = standardize_silence(sound[start_time:end_time])
    split_path = os.path.split(fpath)
    fname, ext = split_path[-1].split(".")
    fpath = os.path.join(split_path[0], fname)
    new_path = fpath + "_{}_{}.{}".format(start_time, end_time, ext)
    sound.export(new_path, format=ext)
    return new_path
