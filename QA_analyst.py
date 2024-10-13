import os
from openai import OpenAI
import json
import traceback  # Add this import
from flask import Flask, jsonify, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)

# Use the connection string format you provided
DATABASE_URL = f"postgresql://postgres.oabafybqxkxpziadbmhk:{os.getenv('SUPABASE_KEY')}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_title = db.Column(db.String(200), nullable=False)
    report_subtitle = db.Column(db.String(200))
    transcript = db.Column(db.Text, nullable=False)
    final_summary = db.Column(db.Text, nullable=False)
    chunk_summaries = db.Column(db.Text)  # Store as JSON string
    report_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

def read_text_from_file(file_path):
    """Reads the text content from a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def split_text(text, max_size=6000):
    """Splits text into chunks that are less than max_size tokens."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    for word in words:
        word_length = len(word)  # Approximate token count
        if current_size + word_length + 1 > max_size:  # +1 for the space
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = word_length
        else:
            current_chunk.append(word)
            current_size += word_length + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def summarize_chunk(text, model="gpt-4o-mini", max_tokens=2000):
    """First round summarization: Summarize the text focusing on key takeaways with details."""
    prompt = (
        "You are a professional blockchain analyst. "
        "Your task is to summarize the following text, focusing on key takeaways while keeping as much detail and figures as possible. "
        "Include all specific data points, quotes, statistics, and any projections mentioned. "
        "Ensure that the summary is comprehensive and includes all important points."
        "Present the summary in a structured bullet point format."
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": f"Please summarize the following text:\n\n{text}"
            }
        ],
        max_tokens=max_tokens,
        temperature=0.3
    )
    summary = response.choices[0].message.content.strip()
    print("Chunk Summary:", summary)  # Optional: Print each summary for verification
    return summary

def extract_key_takeaways(summaries, report_type="analyst", model="gpt-4o-mini", max_tokens=2500):
    """Second round summarization: Extract key takeaways from the summaries in the specified format."""
    combined_summaries = "\n\n".join(summaries)
    
    if report_type == "analyst":
        prompt = (
            "You are a professional blockchain analyst preparing a report for senior stakeholders. "
            "Your task is to extract key takeaways from the following summaries. "
            "Present each key takeaway as a bolded heading summarizing the key idea, followed by a detailed explanation and analysis. "
            "Do not refer to 'the speaker' or 'they'; instead, focus directly on the subject matter. "
            "Include specific figures, statistics, data points, and examples from the text to support each point. "
            "Avoid duplication by ensuring each bullet point addresses a unique aspect of the content. "
            "Use a formal, analytical tone appropriate for a professional report intended for senior stakeholders. "
            "Ensure clarity and conciseness in your writing."
        )
    elif report_type == "medium":
        prompt = (
            "You are a blockchain enthusiast writing an engaging Medium post about a YouTube video. "
            "Your task is to create an interesting yet professional article based on the following summaries. "
            "Structure the article with an attention-grabbing introduction, 3-5 main points with subheadings, and a conclusion. "
            "Use a conversational tone that's accessible to a general audience while maintaining professionalism. "
            "Include specific examples, anecdotes, and data points from the summaries to illustrate your points. "
            "Engage the reader by asking thought-provoking questions and providing insights. "
            "Aim for a balance between being informative and entertaining. "
            "Conclude with a call-to-action or a reflection on the implications of the content."
        )
    else:
        raise ValueError("Invalid report type. Choose 'analyst' or 'medium'.")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Please create the content based on these summaries:\n\n{combined_summaries}"}
        ],
        max_tokens=max_tokens,
        temperature=0.4  # Slightly increased for more creativity in the Medium post
    )
    content = response.choices[0].message.content.strip()
    return content

def write_text_to_file(texts, output_path):
    """Writes the texts to a file, ensuring the final report is at the front."""
    with open(output_path, 'w', encoding='utf-8') as file:
        for text in texts:
            file.write(text + "\n\n")

def generate_title_subtitle(summary, report_type="analyst", model="gpt-4o-mini", max_tokens=100):
    """Generate a title and subtitle based on the final summary and report type."""
    if report_type == "analyst":
        prompt = (
            "Based on the following summary, generate a concise title (max 8 words) and a one-sentence subtitle "
            "that captures the essence of the professional analyst report. Return only the JSON object without any markdown formatting."
        )
    elif report_type == "medium":
        prompt = (
            "Based on the following summary, generate an engaging and catchy title (max 10 words) and a one-sentence subtitle "
            "that would attract readers to a Medium post about this topic. The title should be intriguing but not clickbait. "
            "Return only the JSON object without any markdown formatting."
        )
    else:
        raise ValueError("Invalid report type. Choose 'analyst' or 'medium'.")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": summary}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        content = content.replace('```json', '').replace('```', '').strip()
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Error in generate_title_subtitle: {e}")
        print(traceback.format_exc())
    
    return {"title": "Comprehensive Analysis Report", "subtitle": "Detailed summary and key insights from your transcript"}

def get_report_type():
    """Prompt the user to select the report type."""
    while True:
        print("\nPlease select the type of report you want to generate:")
        print("1. Professional Analyst Report")
        print("2. Engaging Medium Blog Post")
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == '1':
            return "analyst"
        elif choice == '2':
            return "medium"
        else:
            print("Invalid choice. Please enter 1 or 2.")

def main(input_text, output_path):
    # Step 1: Use the input text directly instead of reading from a file
    text = input_text
    
    # Step 2: Split the text into manageable chunks
    chunks = split_text(text)
    
    # Step 3: First round summarization for each chunk
    first_round_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        summary = summarize_chunk(chunk)
        first_round_summaries.append(summary)
    
    # New Step: Get user's choice for report type
    report_type = get_report_type()
    
    # Step 4: Second round summarization to extract key takeaways
    final_report = extract_key_takeaways(first_round_summaries, report_type)
    
    # Step 5: Generate title and subtitle
    title_subtitle = generate_title_subtitle(final_report, report_type)
    
    # Step 6: Combine all summaries (final report first)
    all_summaries = [final_report] + first_round_summaries
    
    # Step 7: Write all summaries to the output file
    write_text_to_file(all_summaries, output_path)
    
    return output_path, first_round_summaries, final_report, title_subtitle, report_type

# Example usage:
# result = main(input_text, "output.txt")

@app.route('/get_history')
def get_history():
    try:
        analyses = Analysis.query.order_by(Analysis.created_at.desc()).all()
        return jsonify([{
            'id': analysis.id,
            'report_title': analysis.report_title,
            'created_at': analysis.created_at.isoformat()
        } for analysis in analyses])
    except Exception as e:
        print(f"Error fetching history: {str(e)}")
        return jsonify({"error": f"Error fetching history: {str(e)}"}), 500

@app.route('/get_analysis/<int:id>')
def get_analysis(id):
    print(f"Attempting to fetch analysis with id: {id}")
    try:
        analysis = Analysis.query.get(id)
        if analysis is None:
            print(f"Analysis with id {id} not found")
            return jsonify({"error": f"Analysis with id {id} not found"}), 404
        print(f"Analysis found: {analysis.report_title}")
        return jsonify({
            'transcript': analysis.transcript,
            'final_summary': analysis.final_summary,
            'chunk_summaries': json.loads(analysis.chunk_summaries),
            'report_title': analysis.report_title,
            'report_subtitle': analysis.report_subtitle,
            'report_type': analysis.report_type
        })
    except Exception as e:
        print(f"Error fetching analysis: {str(e)}")
        return jsonify({"error": f"Error fetching analysis: {str(e)}"}), 500

@app.route('/debug/db_check')
def db_check():
    try:
        # Try to establish a direct connection to the database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        cur.close()
        conn.close()

        # Now try to fetch some data using SQLAlchemy
        analyses = Analysis.query.limit(5).all()
        return jsonify({
            "status": "success",
            "message": f"Connected to database. PostgreSQL version: {db_version[0]}",
            "sample": [{
                "id": a.id,
                "title": a.report_title,
                "created_at": a.created_at.isoformat()
            } for a in analyses]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to database: {str(e)}",
            "traceback": traceback.format_exc(),
            "database_url": DATABASE_URL.replace(os.getenv('SUPABASE_KEY'), '[REDACTED]')  # Redact the password
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result/<int:id>')
def result(id):
    analysis = Analysis.query.get(id)
    if analysis is None:
        abort(404)
    return render_template('result.html',
                           transcript=analysis.transcript,
                           final_summary=analysis.final_summary,
                           chunk_summaries=json.loads(analysis.chunk_summaries),
                           report_title=analysis.report_title,
                           report_subtitle=analysis.report_subtitle,
                           report_type=analysis.report_type)

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

@app.route('/debug/list_analyses')
def list_analyses():
    try:
        analyses = Analysis.query.all()
        return jsonify([{
            'id': a.id,
            'report_title': a.report_title,
            'created_at': a.created_at.isoformat()
        } for a in analyses])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug/add_sample_analysis')
def add_sample_analysis():
    try:
        sample_analysis = Analysis(
            report_title="Sample Analysis",
            report_subtitle="This is a sample analysis",
            transcript="This is a sample transcript",
            final_summary="This is a sample final summary",
            chunk_summaries=json.dumps(["Chunk 1 summary", "Chunk 2 summary"]),
            report_type="analyst"
        )
        db.session.add(sample_analysis)
        db.session.commit()
        return jsonify({"message": "Sample analysis added", "id": sample_analysis.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Make sure this is at the end of your file
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)