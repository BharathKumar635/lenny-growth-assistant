import ollama

response = ollama.chat(
    model="qwen2.5:3b",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a helpful writing assistant. "
                "Write clear Markdown prose. "
                "Do not output HTML, JSON, product listings, prices, "
                "or unrelated information."
            ),
        },
        {
            "role": "user",
            "content": (
                "Write about 100 words explaining product retention. "
                "Use only this idea: Product teams should understand "
                "why users continue to get value from a product."
            ),
        },
    ],
    options={
        "temperature": 0.2,
        "num_ctx": 4096,
    },
)

print(response["message"]["content"])