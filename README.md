# Insights Machine

Insights Machine is a web application that transforms transcripts into actionable insights using advanced natural language processing techniques. It's designed to help users quickly extract key information from lengthy transcripts, making it ideal for researchers, analysts, and decision-makers who need to process large amounts of textual data efficiently.

## Features

- Transcript analysis and summarization
- Real-time processing with live updates
- Two-stage summarization for comprehensive insights
- Automatic generation of report titles and subtitles
- Downloadable PDF reports
- User-friendly web interface

## Technologies Used

- Backend: Python, Flask
- Frontend: HTML, CSS (Tailwind CSS), JavaScript (React)
- NLP: OpenAI GPT models

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/insights-machine.git
   cd insights-machine
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your API key: `OPENAI_API_KEY=your_api_key_here`

5. Run the application:
   ```
   python app.py
   ```

6. Open a web browser and navigate to `http://localhost:5000`

## Usage

1. Paste your transcript into the text area on the home page.
2. Click "Generate Insights" to start the analysis.
3. Watch as the application processes your transcript in real-time.
4. Once complete, view the chunk summaries and final analysis.
5. Download the report as a PDF if desired.

## File Structure

- `app.py`: Main Flask application
- `QA_analyst.py`: Contains the core NLP functions
- `templates/index.html`: Main page template
- `templates/result.html`: Result page template (currently unused)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.