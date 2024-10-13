import os
from openai import OpenAI
import json
import traceback
from dotenv import load_dotenv
import tiktoken

# Load environment variables
load_dotenv()

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

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

def summarize_chunk(text, model="gpt-4", max_tokens=2000, max_input_tokens=6000):
    """First round summarization: Summarize the text focusing on key takeaways with details."""
    prompt = (
        "As a professional blockchain analyst, your task is to summarize the following text. "
        "Focus on key takeaways while preserving as much detail and figures as possible. "
        "Include all specific data points, quotes, statistics, and any projections mentioned. "
        "Ensure that the summary is comprehensive and includes all important points. "
        "Present the summary in a structured bullet point format, using the following structure:\n\n"
        "• Main Point 1\n"
        "  - Supporting detail\n"
        "  - Supporting detail\n"
        "• Main Point 2\n"
        "  - Supporting detail\n"
        "  - Supporting detail\n"
        "...\n\n"
        "Be concise but thorough, and maintain a professional tone throughout."
    )
    
    # Calculate tokens
    prompt_tokens = num_tokens_from_string(prompt)
    text_tokens = num_tokens_from_string(text)
    
    if prompt_tokens + text_tokens > max_input_tokens:
        # Split the text and summarize in parts
        mid_point = len(text) // 2
        first_half = summarize_chunk(text[:mid_point], model, max_tokens, max_input_tokens)
        second_half = summarize_chunk(text[mid_point:], model, max_tokens, max_input_tokens)
        combined_summary = first_half + "\n\n" + second_half
        return summarize_chunk(combined_summary, model, max_tokens, max_input_tokens)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
        ],
        max_tokens=max_tokens,
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def extract_key_takeaways(summaries, report_type="analyst", model="gpt-4", max_tokens=3000):
    """Second round summarization: Extract key takeaways from the summaries in the specified format."""
    combined_summaries = "\n\n".join(summaries)
    
    if report_type == "analyst":
        prompt = (
            "As a professional blockchain analyst preparing a report for senior stakeholders, your task is to synthesize the following summaries into a cohesive report. "
            "Structure your report as follows:\n\n"
            "1. Executive Summary (2-3 sentences overview)\n"
            "2. Key Findings (4-6 main points)\n"
            "3. Detailed Analysis (Expand on each key finding)\n"
            "4. Market Implications (2-3 paragraphs)\n"
            "5. Future Outlook (1-2 paragraphs)\n\n"
            "For each section:\n"
            "- Use bolded headings to introduce each main point or section\n"
            "- Provide detailed explanations and analysis\n"
            "- Include specific figures, statistics, and data points to support your analysis\n"
            "- Maintain a formal, analytical tone appropriate for senior stakeholders\n"
            "- Ensure clarity and conciseness in your writing\n"
            "- Avoid referring to 'the speaker' or 'they'; focus directly on the subject matter"
        )
    elif report_type == "medium":
        prompt = (
            "As a blockchain enthusiast writing an engaging Medium post, your task is to create an interesting yet professional article based on the following summaries. "
            "Structure your article as follows:\n\n"
            "1. Attention-grabbing introduction (1-2 paragraphs)\n"
            "2. Main body (3-5 main points with subheadings)\n"
            "3. Conclusion with a call-to-action or reflection\n\n"
            "For each section:\n"
            "- Use a conversational tone that's accessible to a general audience while maintaining professionalism\n"
            "- Include specific examples, anecdotes, and data points to illustrate your points\n"
            "- Engage the reader by asking thought-provoking questions and providing insights\n"
            "- Balance being informative and entertaining\n"
            "- Use bolded subheadings to introduce each main point\n"
            "- Incorporate relevant blockchain terminology, explaining complex concepts in simple terms"
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
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

def generate_title_subtitle(summary, report_type="analyst", model="gpt-4", max_tokens=150):
    """Generate a title and subtitle based on the final summary and report type."""
    if report_type == "analyst":
        prompt = (
            "Based on the following summary of a blockchain analysis report, generate:\n"
            "1. A concise, professional title (max 10 words)\n"
            "2. A one-sentence subtitle that captures the essence of the report\n\n"
            "The title should be clear and informative, suitable for a professional analyst report. "
            "The subtitle should provide a brief overview of the main findings or implications. "
            "Return the result as a JSON object with 'title' and 'subtitle' keys."
        )
    elif report_type == "medium":
        prompt = (
            "Based on the following summary of a blockchain-related Medium post, generate:\n"
            "1. An engaging and catchy title (max 12 words)\n"
            "2. A one-sentence subtitle that would attract readers\n\n"
            "The title should be intriguing but not clickbait, suitable for a Medium article about blockchain technology. "
            "The subtitle should give a glimpse of the main topic or insight of the article. "
            "Return the result as a JSON object with 'title' and 'subtitle' keys."
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
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Error in generate_title_subtitle: {e}")
        print(traceback.format_exc())
        return {"title": "Blockchain Analysis Report", "subtitle": "Key insights and future implications in the blockchain space"}

def main(transcript, report_type):
    # Step 1: Split the text into manageable chunks
    chunks = split_text(transcript)
    
    # Step 2: First round summarization for each chunk
    chunk_summaries = [summarize_chunk(chunk) for chunk in chunks]
    
    # Step 3: Second round summarization to extract key takeaways
    final_summary = extract_key_takeaways(chunk_summaries, report_type)
    
    # Step 4: Generate title and subtitle
    title_subtitle = generate_title_subtitle(final_summary, report_type)
    
    return {
        'chunk_summaries': chunk_summaries,
        'final_summary': final_summary,
        'title': title_subtitle['title'],
        'subtitle': title_subtitle['subtitle']
    }

# Make sure these functions are defined and implemented
