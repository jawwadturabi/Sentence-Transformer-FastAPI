from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mangum import Mangum
from embeddings_utils import calculate_similarity

app = FastAPI()
handler = Mangum(app)

@app.get("/")
def get():
    return "Hello from calculate similarity app"


class SimilarityInput(BaseModel):
    phraseEmbedding: list
    embeddedChunks: list


@app.post("/calculate_similarity")
def get_similarity(input_data: SimilarityInput):
    try:
        # Call the function to calculate similarity using semantic search
        result = calculate_similarity(
            input_data.phraseEmbedding, input_data.embeddedChunks
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating similarity: {e}"
        )
