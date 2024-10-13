import os
from openai import OpenAI
import json
import traceback
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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

def extract_key_takeaways(summaries, report_type="analyst", model="gpt-4", max_tokens=2500):
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

def generate_title_subtitle(summary, report_type="analyst", model="gpt-4", max_tokens=100):
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

def main(transcript, report_type):
    logger.info("Starting main function")
    
    # Step 1: Split the text into manageable chunks
    chunks = split_text(transcript)
    logger.info(f"Split transcript into {len(chunks)} chunks")
    
    # Step 2: First round summarization for each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Summarizing chunk {i+1}/{len(chunks)}")
        summary = summarize_chunk(chunk)
        chunk_summaries.append(summary)
    
    # Step 3: Second round summarization to extract key takeaways
    logger.info("Extracting key takeaways")
    final_summary = extract_key_takeaways(chunk_summaries, report_type)
    
    # Step 4: Generate title and subtitle
    logger.info("Generating title and subtitle")
    title_subtitle = generate_title_subtitle(final_summary, report_type)
    
    logger.info("Main function completed")
    return {
        'chunk_summaries': chunk_summaries,
        'final_summary': final_summary,
        'title': title_subtitle['title'],
        'subtitle': title_subtitle['subtitle']
    }

# Make sure these functions are defined and implemented
