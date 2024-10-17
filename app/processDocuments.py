from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from pdf2image import convert_from_bytes
import requests
import json
import boto3
import whisper
import PyPDF2
import io
import os
import re
import tempfile

load_dotenv()

# Connecting to MongoDB Atlas
MONGODB_URI = os.environ['MONGODB_URI']
client = MongoClient(MONGODB_URI)
db = client['primavera']  # Name of the MongoDB database
documents_collection = db['documents']  # Collection to store the extracted texts
chunks_collection = db['chunks']

# Initialize the S3 client
s3_client = boto3.client('s3')
bucket_name = 'primavera-bucket'  # Replace with your actual bucket name

# Load the Whisper model for audio files
model = whisper.load_model("base")

def lambda_handler(event):
    # Retrieve file information from the S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Check if the file is in the 'documents/' directory
    if not key.startswith('documents/'):
        return {
            'statusCode': 400,
            'body': json.dumps('The file is not in the documents directory.')
        }

    try:
        # Download the file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_stream = io.BytesIO(response['Body'].read())
        file_type = key.split('.')[-1].lower()

        # Extract the 'mongoDbId' metadata from the S3 object
        metadata = response.get('Metadata', {})
        dataBaseId = metadata.get('databaseid')
        
        if not dataBaseId:
            return {
                'statusCode': 400,
                'body': json.dumps('No mongoDbId found in the metadata.')
            }

        extracted_text = ""
        
        # Handle different file types
        if file_type == 'pdf':
            extracted_text = extract_text_from_pdf(file_stream, dataBaseId)
        elif file_type in ['mp3', 'wav', 'm4a', 'mp4']:
            extracted_text = extract_text_from_audio(file_stream)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Unsupported file type: {file_type}")
            }
        
        # Convert dataBaseId from string to ObjectId before querying MongoDB
        try:
            object_id = ObjectId(dataBaseId)
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Invalid ObjectId format: {dataBaseId}")
            }

        # Find the MongoDB document corresponding to the ObjectId
        existing_document = documents_collection.find_one({"_id": object_id})

        if existing_document:
            # Update the 'fulltext' field with the extracted text
            documents_collection.update_one(
                {"_id": object_id},
                {"$set": {"fulltext": extracted_text}}
            )
            result = split_text_to_chunks(dataBaseId)
            return result
        else:
            return {
                'statusCode': 404,
                'body': json.dumps(f"Document with mongoDbId {dataBaseId} not found.")
            }

    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error processing the file {key}")
        }

def extract_text_from_pdf(file_stream, document_id):
    """Extract text from a PDF file and create images for each page if necessary"""
    try:
        # Try to extract the text using PyPDF2 first
        reader = PyPDF2.PdfReader(file_stream)
        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:  # If text is found
                full_text += page_text
        
        # If no text is found, convert pages to images and process with OpenAI
        if not full_text:
            print("No text found, uploading pages as images and sending to OpenAI.")
            image_urls = upload_pdf_images_to_s3(file_stream, document_id)
            full_text = call_openai_to_extract_from_images(image_urls, document_id)
        return full_text

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def upload_pdf_images_to_s3(file_stream, document_id):
    """Convert PDF pages to images and upload them to S3"""
    images = convert_from_bytes(file_stream.getvalue())
    image_urls = []

    for i, image in enumerate(images):
        # Save the image temporarily
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
            temp_image_path = temp_image.name 
            image.save(temp_image_path, format="PNG")

            # Upload to S3
            s3_key = f"images/{document_id}/page-{i + 1}.png"
            s3_client.upload_file(temp_image.name, bucket_name, s3_key)

            # Get the URL of the uploaded image
            image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
            image_urls.append(image_url)
            
            # Remove the temporary image file after upload
            try:
                os.remove(temp_image_path)
            except Exception as e:
                print(f"Error deleting temp file {temp_image_path}: {e}")

    return image_urls

def call_openai_to_extract_from_images(image_urls, document_id):
    """Call OpenAI API to extract text from images and delete images after processing"""
    full_text = ""
    for image_url in image_urls:
        
        try:
            response = requests.post(
                'https://sq-consulting-openai.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-06-01',
                headers={
                    'api-key': os.environ['OPENAI_API_KEY'],
                    'Content-Type': 'application/json'
                },
                json={
                    "model": "gpt-4o",
                    "temperature": 0,
                    "max_tokens": 16000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url}
                                }
                            ]
                        },
                        {
                            "role": "user",
                            "content": "Please transcribe all text from this image without modifying it, if the image is blank, don't write anything"
                        }
                    ]
                }
            )

            # Process the response
            if response.status_code == 200:
                text = response.json().get('choices')[0]['message']['content']
                full_text += text + "\n"
            else:
                print(f"Error from OpenAI: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error calling OpenAI: {e}")

            # Delete the image from S3 after processing
            try:
                s3_key = image_url.split(f"https://{bucket_name}.s3.amazonaws.com/")[-1]
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                print(f"Deleted image from S3: {s3_key}")
            except Exception as e:
                print(f"Error deleting image from S3: {e}")

    return full_text

def extract_text_from_audio(file_stream):
    """Transcribe audio using Whisper"""
    # Create a temporary file to store the audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        temp_audio_file.write(file_stream.read())
        temp_audio_path = temp_audio_file.name

    # Use Whisper to transcribe the audio using the temporary file path
    result = model.transcribe(temp_audio_path)
    
    # Optionally, delete the temporary file after use
    os.remove(temp_audio_path)
    
    return result['text']

# Function to process the document by splitting its text into chunks
def split_text_to_chunks(document_id):
    try:
        if not document_id:
            raise ValueError("No document ID provided")
        
        # Fetch the document from MongoDB
        try:
            object_id = ObjectId(document_id)
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Invalid ObjectId format: {document_id}")
            }
        document = documents_collection.find_one({"_id": object_id})
        if not document:
            raise ValueError("Document not found")
        
        fulltext = document.get('fulltext')
        
        if not fulltext:
            raise ValueError("No fulltext found in document")
        
        # Split the text into sentences
        text_chunks = split_text_into_sentences(fulltext)

        chunk_ids = []
        chunks_texts = []  # List to store text chunks for embedding

        for index, chunk in enumerate(text_chunks):
            # Prepare chunk data for MongoDB insertion
            chunk_data = {
                "documentId": document_id,
                "text": chunk,
                "chunkNumber": index + 1,
                "creationDate": datetime.now()
            }
            
            # Insert each chunk into the 'chunks' collection and store the chunk ID
            result = chunks_collection.insert_one(chunk_data)
            chunk_ids.append(result.inserted_id)  # Save the inserted chunk ID
            chunks_texts.append(chunk)  # Save the chunk text for embedding

        print(f"Document processed successfully with {len(text_chunks)} chunks.")

        # Call the /embed endpoint to get embeddings after all chunks are inserted
        embeddings = embed_chunks(chunks_texts)

        # Update each chunk with its corresponding embedding
        for idx, chunk_id in enumerate(chunk_ids):
            chunks_collection.update_one(
                {"_id": chunk_id},
                {"$set": {"embeddedChunk": embeddings[idx]}}
            )

        print(f"Document chunks embedded successfully.") 
        return {
            'statusCode': 200,
            'body': json.dumps(f"Document processed successfully with {len(text_chunks)} chunks.")
        }
    
    except Exception as e:
        print(f"Error in process_document: {e}")
        raise e

# Function to call the /embed API and get embeddings for the chunks
def embed_chunks(chunks):
    try:
        # Send POST request to the /embed endpoint
        response = requests.post('http://localhost:4200/embed', json={"sentences": chunks})

        if response.status_code != 200:
            raise Exception(f"Error in calling /embed endpoint: {response.status_code}")

        # Return the embeddings from the API response
        return response.json().get('embeddings')
    
    except Exception as error:
        print(f"Error calling /embed endpoint: {error}")
        raise error

# Function to split the text into sentences
def split_text_into_sentences(text):
    
    print("Splitting text into sentences...")
    
    # Regular expression to find sentence-ending punctuation ('.', '!', or '?')
    sentence_splitter = re.compile(r'(?<=[.!?])\s+')
    
    # Split the text into a list of sentences
    sentences = sentence_splitter.split(text)
    
    print(f"Sentences: {sentences}")
    return sentences
