import os
from openai import OpenAI
import json
import traceback
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def split_text(text, max_chunk_size=2000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        if current_size + len(word) + 1 > max_chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def summarize_chunk(chunk):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Please summarize the following text:\n\n{chunk}"}
        ]
    )
    return response.choices[0].message.content.strip()

def extract_key_takeaways(summaries):
    combined_summaries = "\n\n".join(summaries)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts key takeaways from summaries."},
            {"role": "user", "content": f"Please extract the key takeaways from these summaries:\n\n{combined_summaries}"}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_title_subtitle(summary):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates titles and subtitles."},
            {"role": "user", "content": f"Please generate a title and subtitle for this summary:\n\n{summary}"}
        ]
    )
    result = response.choices[0].message.content.strip()
    title, subtitle = result.split('\n', 1)
    return {"title": title.strip(), "subtitle": subtitle.strip()}

def main(transcript, report_type):
    chunks = split_text(transcript)
    chunk_summaries = [summarize_chunk(chunk) for chunk in chunks]
    final_summary = extract_key_takeaways(chunk_summaries)
    title_subtitle = generate_title_subtitle(final_summary)
    return {
        'chunk_summaries': chunk_summaries,
        'final_summary': final_summary,
        'title': title_subtitle['title'],
        'subtitle': title_subtitle['subtitle']
    }

# Make sure these functions are defined and implemented
