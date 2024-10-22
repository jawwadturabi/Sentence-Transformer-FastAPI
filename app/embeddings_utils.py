from sentence_transformers import SentenceTransformer
import os

model_transformer = None


def embed_chunks(chunks):
    try:
        # Embed sentences using the transformer model
        print("Embedding chunks...")
        embeddings = embed_sentences(chunks)

        # Return the embeddings
        return embeddings

    except Exception as error:
        print(f"Error embedding chunks: {error}")
        raise error


def embed_sentences(sentences):
    global model_transformer
    if model_transformer is None:
        model_transformer = SentenceTransformer(
            "all-MiniLM-L6-v2", cache_folder=os.getenv("HF_HOME", "/tmp")
        )
    embeddings = model_transformer.encode(sentences)
    return embeddings
