# utils.py

import boto3
import os
import tempfile
from pdf2image import convert_from_bytes
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import s3_client, bucket_name

def generate_presigned_url(bucket_name, key, expiration=3600):
    try:
        s3_client = boto3.client('s3')
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name, 'Key': key},
                                                    ExpiresIn=expiration)
    except Exception as e:
        print(e)
        return None
    return response

def upload_pdf_images_to_s3(file_stream, database_document_id):
    """Convert PDF pages to images and upload them to S3 in parallel"""
    thread_count = 4  # Or use os.cpu_count()
    
    # Convert PDF to images using multiple threads
    images = convert_from_bytes(
        file_stream.getvalue(),
        thread_count=thread_count
    )
    image_urls = []

    def process_image(args):
        i, image = args
        temp_image_path = None
        try:
            # Save the image temporarily
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
                temp_image_path = temp_image.name
                image.save(temp_image_path, format="PNG")

            # Upload to S3
            s3_key = f"images/{database_document_id}/page-{i + 1}.png"
            s3_client.upload_file(temp_image_path, bucket_name, s3_key)

            # Generate a presigned URL
            image_url = generate_presigned_url(bucket_name, s3_key)
            if image_url:
                return image_url
            else:
                print(f"Error generating presigned URL for {s3_key}")
                return None

        except Exception as e:
            print(f"Error processing image {i}: {e}")
            return None

        finally:
            # Remove the temporary image file after upload
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                except Exception as e:
                    print(f"Error deleting temp file {temp_image_path}: {e}")

    # Use ThreadPoolExecutor to process images in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Prepare arguments for each image
        args_list = [(i, image) for i, image in enumerate(images)]
        # Submit tasks to the executor
        futures = {executor.submit(process_image, args): args for args in args_list}

        # Collect results as they complete
        for future in as_completed(futures):
            image_url = future.result()
            if image_url:
                image_urls.append(image_url)

    return image_urls

def call_openai_to_extract_from_images(image_urls):
    """Call OpenAI API to extract text from images and delete images after processing in parallel"""
    full_text = ""

    # Using ThreadPoolExecutor to parallelize the image processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}

        for image_url in image_urls:
            futures[executor.submit(requests.post,
                os.environ['OPENAI_API_LINK'],
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
            )] = image_url

        for future in as_completed(futures):
            image_url = futures[future]
            try:
                response = future.result()

                # Process the response
                if response.status_code == 200:
                    text = response.json().get('choices')[0]['message']['content']
                    full_text += text + "\n"
                else:
                    print(f"Error from OpenAI: {response.status_code} - {response.text}")

                # Delete the image from S3 after processing
                try:
                    s3_key = image_url.split(f"https://{bucket_name}.s3.amazonaws.com/")[-1]
                    s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                except Exception as e:
                    print(f"Error deleting image from S3: {e}")

            except Exception as e:
                print(f"Error processing image {image_url}: {e}")

    return full_text

def split_text_into_sentences(text):
    import re
    print("Splitting text into sentences...")
    
    # Regular expression to find sentence-ending punctuation
    sentence_splitter = re.compile(r'(?<=[.!?])\s+')
    
    # Split the text into a list of sentences
    sentences = sentence_splitter.split(text)
    
    print(f"Sentences: {sentences}")
    return sentences