import os
import string
from pydub import AudioSegment
from pydub.silence import split_on_silence


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
