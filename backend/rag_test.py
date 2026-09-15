import ollama


response = ollama.chat(
    model="mymodel:latest",
    messages=[
        {
            "role": "system",
            "content": "Answer the question clearly using the provided context.",
        },
        {
            "role": "user",
            "content": """
Context:

Ada Chen Rekhi discusses feeling stuck at work and recognizing when it
may be time to leave a job.

Question:

What is this context about?

Answer in 2 simple sentences.
""",
        },
    ],
    options={
        "temperature": 0.2,
        "num_ctx": 2048,
    },
)

print("RAW RESPONSE:")
print(response)

print("\nGENERATED TEXT:")
print(response["message"]["content"])