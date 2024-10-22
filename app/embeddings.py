def calculate_similarity(phrase_embedding, embedded_chunks):
    import numpy as np
    from sentence_transformers import util

    # Convert lists to numpy arrays 
    phrase_embedding_np = np.array(phrase_embedding, dtype=np.float32)
    embedded_chunks_np = np.array(embedded_chunks, dtype=np.float32)

    # Reshape the embeddings if necessary
    if len(phrase_embedding_np.shape) == 1:
        phrase_embedding_np = phrase_embedding_np.reshape(1, -1)
    
    if len(embedded_chunks_np.shape) == 1:
        embedded_chunks_np = embedded_chunks_np.reshape(1, -1)

    # Perform semantic search
    search_results = util.semantic_search(phrase_embedding_np, embedded_chunks_np, top_k=1)

    # Extract the best match
    best_match = search_results[0][0]

    # Return the best matching chunk and its similarity score
    return {
        'chunks': [embedded_chunks[best_match['corpus_id']]],  # The best matching chunk
        'similarity': float(best_match['score'])  # The similarity score of the match
    }