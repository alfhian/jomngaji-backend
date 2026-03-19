import os
import subprocess

def ensure_wav(path: str) -> str:
    # kalau sudah wav, langsung return
    if path.lower().endswith(".wav"):
        return path
    # convert ke wav standar
    new_path = os.path.splitext(path)[0] + ".wav"
    cmd = ["ffmpeg", "-y", "-i", path, "-ar", "16000", "-ac", "1", new_path]
    subprocess.run(cmd, check=True)
    return new_path

def convert_to_wav(path: str) -> str:
    new_path = os.path.splitext(path)[0] + "_conv.wav"
    cmd = ["ffmpeg", "-y", "-i", path, "-ar", "16000", "-ac", "1", new_path]
    subprocess.run(cmd, check=True)
    return new_path


def save_upload(file, folder="temp") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, file.filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path
