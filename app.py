from flask import Flask, render_template, send_from_directory, Response, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from QA_analyst import main as qa_main, split_text, summarize_chunk, extract_key_takeaways, generate_title_subtitle
from youtube_transcriber import process_youtube_video, transcribe_audio_stream
import json
import tempfile
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
import traceback
import yt_dlp
import whisper
import re

load_dotenv()

app = Flask(__name__, static_folder='static')

# Use the connection string format you provided
DATABASE_URL = f"postgresql://postgres.oabafybqxkxpziadbmhk:{os.getenv('SUPABASE_KEY')}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define your models here
class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_title = db.Column(db.String(200), nullable=False)
    report_subtitle = db.Column(db.String(200))
    transcript = db.Column(db.Text, nullable=False)
    final_summary = db.Column(db.Text, nullable=False)
    chunk_summaries = db.Column(db.Text)  # Store as JSON string
    report_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

print("Current working directory:", os.getcwd())

env_path = os.path.join(os.getcwd(), '.env')
print("Looking for .env file at:", env_path)

if os.path.exists(env_path):
    print(".env file found")
    with open(env_path, 'r') as f:
        print(".env file contents:")
        print(f.read())
else:
    print(".env file not found")

# Print environment variables for debugging
print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
print("SUPABASE_KEY:", os.getenv("SUPABASE_KEY"))

# Now try to get the variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print("SUPABASE_URL:", supabase_url)
print("SUPABASE_KEY:", supabase_key)

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the .env file")

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

def download_youtube_audio(youtube_url):
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

def transcribe_audio(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return result["text"]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_type = request.form.get('input_type')
        report_type = request.form.get('report_type')
        if input_type == 'text':
            transcript = request.form.get('transcript')
            return Response(process_transcript(transcript, report_type), content_type='text/event-stream')
        elif input_type == 'youtube':
            youtube_link = request.form.get('youtube_link')
            return Response(process_youtube_transcript(youtube_link, report_type), content_type='text/event-stream')
        else:
            return jsonify({"error": "Invalid input type"}), 400
    return render_template('index.html')

def process_youtube_transcript(youtube_link, report_type):
    def generate():
        try:
            yield "data: " + json.dumps({"status": "Downloading audio from YouTube"}) + "\n\n"
            audio_file = download_youtube_audio(youtube_link)
            
            yield "data: " + json.dumps({"status": "Transcribing audio"}) + "\n\n"
            for transcription_chunk in transcribe_audio_stream(audio_file):
                yield "data: " + json.dumps({"status": "Transcribing", "chunk": transcription_chunk}) + "\n\n"
            
            # After transcription is complete, process the full transcript
            full_transcript = " ".join(transcription_chunk for transcription_chunk in transcribe_audio_stream(audio_file))
            yield from process_transcript(full_transcript, report_type)
            
        except Exception as e:
            print(f"Error in process_youtube_transcript: {str(e)}")
            print(traceback.format_exc())
            yield "data: " + json.dumps({"status": "Error", "message": str(e)}) + "\n\n"

    return generate()

@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        response = supabase.table("summaries").select("id, created_at, report_title").order('created_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_analysis/<int:id>', methods=['GET'])
def get_analysis(id):
    try:
        response = supabase.table("summaries").select("*").eq("id", id).execute()
        if response.data:
            analysis = response.data[0]
            return jsonify({
                'transcript': analysis['transcript'],
                'final_summary': analysis['final_summary'],
                'chunk_summaries': json.loads(analysis['chunk_summaries']),
                'report_title': analysis['report_title'],
                'report_subtitle': analysis['report_subtitle'],
                'report_type': analysis.get('report_type', 'Not specified')
            })
        else:
            return jsonify({"error": "Analysis not found"}), 404
    except Exception as e:
        print(f"Error in get_analysis: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def process_transcript(transcript, report_type):
    def generate():
        try:
            yield "data: " + json.dumps({"status": "Processing transcript"}) + "\n\n"
            
            chunks = split_text(transcript)
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks):
                summary = summarize_chunk(chunk)
                chunk_summaries.append(summary)
                yield "data: " + json.dumps({
                    "status": f"Processed chunk {i+1}/{len(chunks)}",
                    "summary": summary,
                    "type": "chunk"
                }) + "\n\n"
            
            yield "data: " + json.dumps({"status": "Extracting key takeaways"}) + "\n\n"
            
            final_summary = extract_key_takeaways(chunk_summaries)
            print("Final summary generated:", final_summary[:100] + "...")  # Debug print
            
            print("Generating title and subtitle...")  # Debug print
            title_subtitle = generate_title_subtitle(final_summary)
            
            # Debug prints
            print("Generated title:", title_subtitle.get("title", "No title generated"))
            print("Generated subtitle:", title_subtitle.get("subtitle", "No subtitle generated"))
            
            yield "data: " + json.dumps({
                "status": "Complete", 
                "final_summary": final_summary,
                "chunk_summaries": chunk_summaries,
                "report_title": title_subtitle.get("title", "Comprehensive Analysis Report"),
                "report_subtitle": title_subtitle.get("subtitle", "Detailed summary and key insights from your transcript"),
                "transcript": transcript,
                "type": "final"
            }) + "\n\n"

            # Store data in Supabase after sending the final summary
            data = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "transcript": transcript,
                "chunk_summaries": json.dumps(chunk_summaries),
                "final_summary": final_summary,
                "report_title": title_subtitle["title"],
                "report_subtitle": title_subtitle["subtitle"],
                "report_type": report_type  # Make sure this line is included
            }
            
            try:
                result = supabase.table("summaries").insert(data).execute()
                print("Data inserted successfully:", result)
                yield "data: " + json.dumps({"status": "Data saved to database"}) + "\n\n"
            except Exception as e:
                error_message = str(e)
                print("Error inserting data into Supabase:", error_message)
                yield "data: " + json.dumps({"status": "Error saving data", "error": error_message}) + "\n\n"

        except Exception as e:
            print(f"Error in process_transcript: {str(e)}")
            print(traceback.format_exc())
            yield "data: " + json.dumps({"status": "Error", "message": str(e)}) + "\n\n"

    return generate()

@app.route('/debug/list_analyses')
def list_analyses():
    try:
        response = supabase.table("summaries").select("id, report_title, created_at").order('created_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/result/<int:id>')
def result(id):
    try:
        # Fetch the specific analysis
        analysis_response = supabase.table("summaries").select("*").eq("id", id).execute()
        if not analysis_response.data:
            return "Analysis not found", 404
        analysis = analysis_response.data[0]

        # Fetch the history
        history_response = supabase.table("summaries").select("id, report_title, created_at").order('created_at', desc=True).execute()
        history = history_response.data

        # Set a default value for report_type if it's None
        report_type = analysis.get('report_type', 'Not specified')

        return render_template('result.html',
                               transcript=analysis['transcript'],
                               final_summary=analysis['final_summary'],
                               chunk_summaries=json.loads(analysis['chunk_summaries']),
                               report_title=analysis['report_title'],
                               report_subtitle=analysis['report_subtitle'],
                               report_type=report_type,
                               history=history)
    except Exception as e:
        print(f"Error in result route: {str(e)}")
        print(traceback.format_exc())
        return "An error occurred", 500

@app.template_filter('format_summary')
def format_summary(text):
    lines = text.split('\n')
    formatted_lines = []
    in_list = False
    indent_level = 0
    
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('- '):
            if not in_list:
                formatted_lines.append('<ul class="list-disc pl-5">')
                in_list = True
            formatted_lines.append(f'<li class="mb-2">{stripped_line[2:]}</li>')
        elif stripped_line.startswith('**') and stripped_line.endswith('**'):
            # This is a heading
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append(f'<h3 class="chunk-heading mt-4 mb-2">{stripped_line[2:-2]}</h3>')
            indent_level += 1
        elif stripped_line:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            if indent_level > 0:
                formatted_lines.append(f'<p class="indented-content mb-2">{stripped_line}</p>')
            else:
                formatted_lines.append(f'<p class="mb-2">{stripped_line}</p>')
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            indent_level = 0
    
    if in_list:
        formatted_lines.append('</ul>')
    
    # Join the formatted lines
    text = ''.join(formatted_lines)
    
    # Replace remaining **** with <strong></strong> for bold text
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    return text

if __name__ == '__main__':
    app.run(debug=True)
