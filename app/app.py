from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
# import numpy as np
from mangum import Mangum
import uvicorn
# from processDocuments import lambda_handler
import os


app = FastAPI()

###############################################################################
#   Handler for AWS Lambda                                                    #
###############################################################################

handler = Mangum(app)


@app.get("/")
def get():
    print("testing")
    return "Hello World"

model = SentenceTransformer("all-MiniLM-L6-v2",cache_folder=os.getenv('HF_HOME', '/tmp')) # Loaded once globally

@app.post("/processDocument")
def process_document():
    try:
        # Simuler l'événement S3 pour appeler lambda_handler
        event_payload = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "primavera-bucket"},
                        "object": {
                            "key": "documents/Unilever/UNILEVER_ICA_2015_16_17.pdf"
                        },
                    }
                }
            ]
        }

        # Appeler la fonction lambda_handler
        # result = lambda_handler(event_payload)

        return "result"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {e}")


class SimilarityInput(BaseModel):
    phraseEmbedding: list
    embeddedChunks: list


class TextChunks(BaseModel):
    sentences: list


# def calculate_similarity(phrase_embedding, embedded_chunks):
#     try:
#         phrase_embedding_np = np.array(phrase_embedding)
#         embedded_chunks_np = np.array(embedded_chunks)
#         similarities = util.cos_sim(phrase_embedding_np, embedded_chunks_np)
#         best_match_idx = np.argmax(similarities)
#         return {
#             "chunk": embedded_chunks[best_match_idx],
#             "similarity": float(similarities[0][best_match_idx]),
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Error calculating similarity: {e}"
#         )


# def embed_sentences(sentences):
#     try:
#         embeddings = model.encode(sentences)
#         return embeddings
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error generating embeddings: {e}")


# @app.post("/embed")
# def get_embeddings(text_chunks: TextChunks):
#     if not text_chunks.sentences:
#         raise HTTPException(status_code=400, detail="No sentences provided")
#     embeddings = embed_sentences(text_chunks.sentences)
#     return {"embeddings": embeddings.tolist()}


# @app.post("/calculate_similarity")
# def get_similarity(input_data: SimilarityInput):
#     result = calculate_similarity(input_data.phraseEmbedding, input_data.embeddedChunks)
#     return result




###############################################################################
#   Run the self contained application                                        #
###############################################################################

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=5000)
