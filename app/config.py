import os
from dotenv import load_dotenv
from pymongo import MongoClient
import whisper
import boto3

# Load environment variables
load_dotenv()

# MongoDB client
MONGODB_URI = os.environ['MONGODB_URI']
client = MongoClient(MONGODB_URI)
db = client['primavera']  # Name of the MongoDB database
documents_collection = db['documents']  # Collection to store the extracted texts
chunks_collection = db['chunks']
# model_whisper = whisper.load_model("tiny")

# Initialize the S3 client
s3_client = boto3.client('s3')
bucket_name = 'primavera-bucket'