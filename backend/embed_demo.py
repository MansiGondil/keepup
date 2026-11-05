"""Step 4a: turn headlines into embeddings and compare them.

Run from the backend folder:  python embed_demo.py
The first run downloads the model (about 90 MB) and caches it on disk.
"""

from sentence_transformers import SentenceTransformer

# A small, free model that turns a sentence into a list of 384 numbers
# (an "embedding"). Sentences with similar meaning get similar numbers.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

HEADLINES = {
    "A": "Major cloud provider restores service after six-hour regional outage",
    "B": "Cloud provider says regional outage fixed after configuration error",
    "C": "Central bank holds interest rates steady for third meeting",
    "D": "Lawmakers pass framework for testing high-risk AI systems",
}


def main():
    model = SentenceTransformer(MODEL_NAME)

    labels = list(HEADLINES)
    # One embedding (row of numbers) per headline. normalize_embeddings=True
    # scales each row to length 1, so cosine similarity is a simple dot product.
    embeddings = model.encode(list(HEADLINES.values()), normalize_embeddings=True)
    print(f"embedding size: {embeddings.shape[1]} numbers per headline")
    print()

    for label, headline in HEADLINES.items():
        print(f"{label}: {headline}")
    print()

    # Cosine similarity: 1.0 = same meaning, around 0 = unrelated.
    similarity = model.similarity(embeddings, embeddings)

    # Print a table: one row and one column per headline.
    print("      " + "".join(f"{label:>7}" for label in labels))
    for i, row_label in enumerate(labels):
        cells = "".join(f"{float(similarity[i][j]):7.2f}" for j in range(len(labels)))
        print(f"{row_label:>6}{cells}")


if __name__ == "__main__":
    main()
