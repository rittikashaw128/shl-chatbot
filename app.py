from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import requests
import json
import re

app = FastAPI()

# =========================
# LOAD DATASET
# =========================

url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog"

try:
    response = requests.get(url, timeout=10)

    raw_text = response.text

    clean_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)

    data = json.loads(clean_text)

except Exception as e:
    print("DATA LOAD ERROR:", e)
    data = []

# =========================
# LOAD EMBEDDING MODEL
# =========================

model = SentenceTransformer("all-MiniLM-L6-v2")

catalog_texts = []

for item in data:

    text = f"""
    name: {item.get('name', '')}
    description: {item.get('description', '')}
    category: {item.get('category', '')}
    """

    catalog_texts.append(text)

catalog_embeddings = model.encode(catalog_texts)

# =========================
# CONVERSATION MEMORY
# =========================

conversation_memory = {}

STAGES = {
    "START": "start",
    "EXPERIENCE": "experience",
    "LOCATION": "location",
    "FINAL": "final"
}

# =========================
# REQUEST MODELS
# =========================

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]

# =========================
# INITIALIZE SESSION
# =========================

def initialize_session(session_id):

    if session_id not in conversation_memory:

        conversation_memory[session_id] = {
            "stage": STAGES["START"],
            "role_interest": None,
            "experience": None,
            "location": None,
            "recommendations": []
        }

# =========================
# SEARCH FUNCTION
# =========================

def search_recommendations(query):

    if len(data) == 0:
        return []

    query_embedding = model.encode([query])

    similarities = cosine_similarity(
        query_embedding,
        catalog_embeddings
    )[0]

    top_indices = np.argsort(similarities)[::-1][:5]

    recommendations = []

    for idx in top_indices:

        item = data[idx]

        recommendations.append({
            "name": item.get("name"),
            "category": item.get("category"),
            "description": item.get("description"),
            "score": float(similarities[idx])
        })

    return recommendations

# =========================
# HOME ROUTE
# =========================

@app.get("/")
def home():
    return {
        "message": "SHL Chatbot Running Successfully"
    }

# =========================
# CHAT ROUTE
# =========================

@app.post("/chat")
def chat(req: ChatRequest):

    session_id = req.session_id

    initialize_session(session_id)

    state = conversation_memory[session_id]

    latest_message = req.messages[-1].content.lower()

    # START STAGE
    if state["stage"] == STAGES["START"]:

        state["role_interest"] = latest_message
        state["stage"] = STAGES["EXPERIENCE"]

        return {
            "response": "What experience level are you looking for?",
            "stage": state["stage"]
        }

    # EXPERIENCE STAGE
    elif state["stage"] == STAGES["EXPERIENCE"]:

        state["experience"] = latest_message
        state["stage"] = STAGES["LOCATION"]

        return {
            "response": "Do you prefer remote or onsite opportunities?",
            "stage": state["stage"]
        }

    # LOCATION STAGE
    elif state["stage"] == STAGES["LOCATION"]:

        state["location"] = latest_message

        combined_query = f"""
        {state['role_interest']}
        {state['experience']}
        {state['location']}
        """

        recommendations = search_recommendations(
            combined_query
        )

        state["recommendations"] = recommendations
        state["stage"] = STAGES["FINAL"]

        return {
            "response": "Based on your preferences, here are the best matches.",
            "recommendations": recommendations,
            "conversation_complete": True,
            "total_results": len(recommendations)
        }

    # FINAL STAGE
    return {
        "response": "Conversation already completed.",
        "recommendations": state["recommendations"],
        "conversation_complete": True
    }