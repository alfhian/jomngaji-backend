import whisper

# Load model sekali saat startup
model = whisper.load_model("medium")  # bisa diganti "small" untuk lebih ringan

def transcribe_audio(audio_path: str) -> str:
    result = model.transcribe(audio_path, language="ar")
    return result["text"].strip()
