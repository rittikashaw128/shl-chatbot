from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import requests
import json
import re

app = FastAPI()

conversation_state = {}

# LOAD DATASET
url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog"

response = requests.get(url)

raw_text = response.text

clean_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)

data = json.loads(clean_text)

# CREATE SEARCHABLE TEXTS
texts = []

for item in data:
    text = f"""
    name: {item.get('name', '')}
    description: {item.get('description', '')}
    category: {item.get('category', '')}
    """
    texts.append(text.lower())


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


@app.get("/")
def home():
    return {"message": "SHL Chatbot Running Successfully"}


@app.post("/chat")
def chat(request: ChatRequest):

    latest_message = request.messages[-1].content.lower()

    # SIMPLE KEYWORD SEARCH
    scores = []

    query_words = latest_message.split()

    for text in texts:

        score = 0

        for word in query_words:
            if word in text:
                score += 1

        scores.append(score)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:5]

    recommendations = []

    for idx in top_indices:

        item = data[idx]

        recommendations.append({
            "name": item.get("name", ""),
            "url": item.get("url", ""),
            "category": item.get("category", "")
        })

    return {
        "query": latest_message,
        "recommendations": recommendations
    }