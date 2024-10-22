from datetime import datetime
from bson.objectid import ObjectId
import json

from config import documents_collection, chunks_collection
from embeddings_utils import embed_chunks
from utils import split_text_into_sentences

def split_text_to_chunks(database_document_id):
    try:
        if not database_document_id:
            raise ValueError("No document ID provided")
        
        # Fetch the document from MongoDB
        try:
            object_id = ObjectId(database_document_id)
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Invalid ObjectId format: {database_document_id}")
            }
        document = documents_collection.find_one({"_id": object_id})
        if not document:
            raise ValueError("Document not found")
        
        fulltext = document.get('fulltext')
        
        if not fulltext:
            raise ValueError("No fulltext found in document")
        
        # Split the text into sentences
        text_chunks = split_text_into_sentences(fulltext)
        
        # Clean previous chunks for this document
        chunks_collection.delete_many({"documentId": database_document_id})

        chunk_ids = []
        chunks_texts = []  # List to store text chunks for embedding

        for index, chunk in enumerate(text_chunks):
            # Prepare chunk data for MongoDB insertion
            chunk_data = {
                "documentId": database_document_id,
                "text": chunk,
                "chunkNumber": index + 1,
                "creationDate": datetime.now()
            }
            
            # Insert each chunk into the 'chunks' collection
            result = chunks_collection.insert_one(chunk_data)
            chunk_ids.append(result.inserted_id)  # Save the inserted chunk ID
            chunks_texts.append(chunk)  # Save the chunk text for embedding

        print(f"Document processed successfully with {len(text_chunks)} chunks.")

        # Get embeddings after all chunks are inserted
        embeddings = embed_chunks(chunks_texts)

        # Update each chunk with its corresponding embedding
        print("Updating chunks with embeddings...")
        for idx, chunk_id in enumerate(chunk_ids):
            embedding_list = embeddings[idx].tolist() 
            chunks_collection.update_one(
                {"_id": chunk_id},
                {"$set": {"embeddedChunk": embedding_list}}
            )

        print(f"Document chunks embedded successfully.") 
        return {
            'statusCode': 200,
            'body': json.dumps(f"Document processed successfully with {len(text_chunks)} chunks.")
        }
    
    except Exception as e:
        print(f"Error in process_document: {e}")
        raise e