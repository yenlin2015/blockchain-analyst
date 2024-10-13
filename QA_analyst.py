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

# ... (rest of your QA_analyst.py code remains unchanged)
