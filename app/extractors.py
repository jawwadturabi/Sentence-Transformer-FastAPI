# extractors.py

import os
import tempfile
import PyPDF2
# import whisper
from config import model_whisper
from utils import upload_pdf_images_to_s3, call_openai_to_extract_from_images

# model_whisper = None


def extract_text_from_pdf(file_stream, database_document_id):
    """Extract text from a PDF file and create images for each page if necessary"""
    try:
        # Try to extract the text using PyPDF2 first
        reader = PyPDF2.PdfReader(file_stream)
        full_text = ""
        # for page in reader.pages:
        #     page_text = page.extract_text()
        #     if page_text:  # If text is found
        #         full_text += page_text

        # If no text is found, convert pages to images and process with OpenAI
        if not full_text:
            print("No text found, uploading pages as images and sending to OpenAI.")
            image_urls = upload_pdf_images_to_s3(file_stream, database_document_id)
            print(f"Uploaded {len(image_urls)} images to S3.")
            full_text = call_openai_to_extract_from_images(image_urls)
            print(f"Extracted text from images: {full_text}")
        return full_text

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


def extract_text_from_audio(file_stream):
    global model_whisper

    """Transcribe audio using Whisper"""
    # Create a temporary file to store the audio file
    print("Creating temporary audio file...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        temp_audio_file.write(file_stream.read())
        temp_audio_path = temp_audio_file.name

    # Use Whisper to transcribe the audio
    print(f"Transcribing audio file: {temp_audio_path}")
    # if model_whisper is None:
    #     model_whisper = whisper.load_model("large-v2")
    result = model_whisper.transcribe(temp_audio_path)
    print(f"Transcription done")

    # Delete the temporary file after use
    os.remove(temp_audio_path)

    return result["text"]
