import ollama


response = ollama.embed(
    model="nomic-embed-text",
    input="How do I improve product growth?",
)

embedding = response["embeddings"][0]

print("Embedding generated successfully!")
print("Dimensions:", len(embedding))
print("First 5 values:", embedding[:5])