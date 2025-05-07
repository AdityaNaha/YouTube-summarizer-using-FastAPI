import os
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter
import google.generativeai as genai

from fastapi import FastAPI
app=FastAPI()

def fetch_youtube_transcript(video_id):
    """Fetches the transcript of a YouTube video and returns it as plain text."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en']) or transcript_list.find_transcript(['en-US'])
        transcript_data = transcript.fetch()
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_data)
        print(f"Transcript length: {len(transcript_text)} characters")
        return transcript_text
    except (TranscriptsDisabled, NoTranscriptFound):
        return "Error: Transcript is disabled or not available."
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"

def generate_gemini_summary(transcript_text):
    """Calls Gemini API to generate a JSON summary of the transcript."""
    try:
        # Check API key
        api_key = "AIzaSyDEsBB_W_khE5m_8pJpKeqQgobxW7OQbSM"
        if not api_key:
            return "Error: GEMINI_API_KEY is not set."

        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Truncate transcript to 10,000 characters to avoid model limits
        max_length = 10000
        if len(transcript_text) > max_length:
            transcript_text = transcript_text[:max_length] + "... [Truncated]"
            print(f"Transcript truncated to {max_length} characters.")

        # Simplified prompt
        prompt = f"""Summarize the following YouTube transcript in JSON format:
{{
  "topic_name": "name of topic",
  "topic_summary": "brief summary of topic"
}}
Transcript:
{transcript_text}"""

        print(f"Prompt length: {len(prompt)} characters")

        # Call Gemini API (non-streaming)
        response = model.generate_content(prompt)
        if not hasattr(response, 'text') or not response.text:
            return f"Error: Empty or invalid Gemini response: {response}"

        # Clean and validate response
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()  # Remove ```json ... ```
        try:
            json.loads(response_text)
            return response_text
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON response: {response_text}\nJSON Error: {str(e)}"
    except Exception as e:
        return f"Error generating summary with Gemini: {str(e)}"

def extract_youtube_id(url):
    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("/")[-1]
    else:
        raise ValueError(" Invalid YouTube URL")

def main():
    video_id = extract_youtube_id(url="https://www.youtube.com/watch?v=pxiP-HJLCx0")
    transcript_text = fetch_youtube_transcript(video_id)
    if "Error" in transcript_text:
        print(transcript_text)
        return
    summary = generate_gemini_summary(transcript_text)
    print("Summary:")
    print(summary)

@app.get("/summarize")
def get_summary(url: str):
    video_id = extract_youtube_id(url)
    transcript = fetch_youtube_transcript(video_id)  # Fixed: Added '='
    if transcript:
        summary = generate_gemini_summary(transcript)  # Fixed: Changed to generate_gemini_summary
        return summary
    else:
        return {"error": "Transcript not found"}