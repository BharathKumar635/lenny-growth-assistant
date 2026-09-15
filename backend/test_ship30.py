
from agent_tools import create_ship30_essay


result = create_ship30_essay(
    "How should product teams improve product retention?"
)


print("\n" + "=" * 80)
print("SHIP 30 ESSAY")
print("=" * 80)

print(result["essay"])


print("\n" + "=" * 80)
print("QUALITY CHECK")
print("=" * 80)

print(f"Word count: {result['word_count']}")
print(f"Target: 1,250 words")
print(f"Acceptable range: 1,000 - 1,400 words")
print(f"Valid length: {result['valid_length']}")
print(f"Generation attempts: {result['attempts']}")


print("\n" + "=" * 80)
print("SOURCES")
print("=" * 80)

for source in result["sources"]:

    print(f"\nGuest: {source['guest']}")
    print(f"Episode: {source['title']}")
    print(f"URL: {source['url']}")
    print(f"Chunk: {source['chunk_index']}")



