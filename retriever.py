import requests
import json
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# DOWNLOAD DATASET
url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"

response = requests.get(url)

raw_text = response.text

clean_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)

data = json.loads(clean_text)

# SAVE CLEAN DATASET
with open("catalog.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Dataset loaded!")

# CREATE SEARCHABLE TEXTS
texts = []

for item in data:
    text = f"""
    {item.get('name', '')}
    {item.get('description', '')}
    {item.get('job_levels', '')}
    {item.get('languages', '')}
    {item.get('keys', '')}
    """

    texts.append(text)

# LOAD EMBEDDING MODEL
model = SentenceTransformer('all-MiniLM-L6-v2')

# CREATE EMBEDDINGS
embeddings = model.encode(texts)

print("Embeddings created!")

# USER QUERY
query = "Java developer with communication skills"

# QUERY EMBEDDING
query_embedding = model.encode([query])

# CALCULATE SIMILARITY
scores = cosine_similarity(query_embedding, embeddings)[0]

# GET TOP RESULTS
top_indices = np.argsort(scores)[::-1][:5]

print("\nTop Recommendations:\n")

for idx in top_indices:
    item = data[idx]

    print("Name:", item.get("name"))
    print("URL:", item.get("link"))
    print("Score:", scores[idx])
    print("-" * 50)