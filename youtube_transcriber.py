import yt_dlp
import os
from openai import OpenAI
from dotenv import load_dotenv
import tempfile
from pydub import AudioSegment
import math

# Initialize the OpenAI client
load_dotenv() 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def download_youtube_audio(youtube_url):
    """Download audio from a YouTube video."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(id)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        filename = f"{info['id']}.mp3"
    return filename

def split_audio(audio_file, max_size_mb=24):
    audio = AudioSegment.from_mp3(audio_file)
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(audio_file)
    
    if file_size <= max_size_bytes:
        return [audio_file]  # Return the original file if it's small enough
    
    duration_ms = len(audio)
    chunk_duration_ms = math.floor((max_size_bytes / file_size) * duration_ms)
    
    chunks = []
    for i in range(0, duration_ms, chunk_duration_ms):
        chunk = audio[i:i+chunk_duration_ms]
        chunk_file = f"{audio_file[:-4]}_chunk_{len(chunks)}.mp3"
        chunk.export(chunk_file, format="mp3")
        chunks.append(chunk_file)
    
    return chunks

def transcribe_audio_stream(audio_file):
    """Transcribe audio file using OpenAI's Whisper API and yield results."""
    try:
        chunks = split_audio(audio_file)
        for chunk in chunks:
            with open(chunk, "rb") as audio:
                response = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio,
                    response_format="text"
                )
            yield response
            if chunk != audio_file:  # Only remove if it's a chunk, not the original file
                os.remove(chunk)
    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        yield None

def process_youtube_video(youtube_url):
    """Process a YouTube video: download audio and transcribe."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            audio_file = download_youtube_audio(youtube_url)
            transcript = " ".join(list(transcribe_audio_stream(audio_file)))
            
            os.chdir(original_dir)
            
        return transcript
    except Exception as e:
        print(f"Error processing YouTube video: {str(e)}")
        return None