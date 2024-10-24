# handlers.py

import io
import json
from bson.objectid import ObjectId

from config import s3_client, documents_collection
from extractors import extract_text_from_pdf, extract_text_from_audio, extract_text_from_docx, extract_text_from_xlsx, extract_text_from_pptx, extract_text_from_image
from processors import split_text_to_chunks

def lambda_handler(event):
    # Loop over each record in the 'Records' array from the S3 event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']  # Get the bucket name
        key = record['s3']['object']['key']  # Get the object key (file path)
        
        print(f"Processing file: s3://{bucket}/{key}")

        try:
            # Try to download the file from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            print(f"File downloaded successfully: {key}")
            
            # Read the file contents into a BytesIO stream
            file_stream = io.BytesIO(response['Body'].read())
            database_document_id = key.split('/')[-1]
            
            metadata = response.get('Metadata', {})
            file_type = metadata.get('fileext')

            extracted_text = ""  # Initialize the variable to store the extracted text
            print(f"File type: {file_type}")

            # Handle different file types
            if file_type == 'pdf':
                extracted_text = extract_text_from_pdf(file_stream, database_document_id)
            elif file_type in ['mp3', 'wav', 'm4a', 'mp4']:
                print("Extracting text from audio...")
                extracted_text = extract_text_from_audio(file_stream, file_type)
            elif file_type in ['doc', 'docx']:
                extracted_text = extract_text_from_docx(file_stream)
            elif file_type in ['xls', 'xlsx']:
                extracted_text = extract_text_from_xlsx(file_stream)
            elif file_type in ['txt']:
                extracted_text = file_stream.read().decode("utf-8")
            elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
                extracted_text = extract_text_from_image(file_stream, database_document_id)
            elif file_type in ['ppt', 'pptx']:
                extracted_text = extract_text_from_pptx(file_stream)
            else:
                # Return an error if the file type is unsupported
                return {
                    'statusCode': 400,
                    'body': json.dumps(f"Unsupported file type: {file_type}")
                }
            # Prepend the title to the extracted text
            document_title = metadata.get('title', 'Untitled Document')
            full_text = f"{document_title}\n{extracted_text}"

            # Convert the 'database_document_id' string to MongoDB ObjectId
            try:
                database_document_id = ObjectId(database_document_id)
            except Exception as e:
                # Return an error if the 'database_document_id' is not a valid ObjectId
                return {
                    'statusCode': 400,
                    'body': json.dumps(f"Invalid ObjectId format: {database_document_id}")
                }

            # Find the document in MongoDB
            existing_document = documents_collection.find_one({"_id": database_document_id})

            if existing_document:
                # Update its 'fulltext' field with the extracted text
                documents_collection.update_one(
                    {"_id": database_document_id},
                    {"$set": {"fulltext": full_text, "status": "processed"}}
                )
                # Split the text into chunks and store in the database
                result = split_text_to_chunks(database_document_id)
                return result
            else:
                # Return an error if the document is not found
                return {
                    'statusCode': 404,
                    'body': json.dumps(f"Document with mongoDbId {database_document_id} not found.")
                }

        except Exception as e:
            # Catch any other errors that occur during processing and return a server error
            print(e)