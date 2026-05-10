from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
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
# MEMORY
# =========================

conversation_memory = {}

STAGES = {
    "START": "start",
    "EXPERIENCE": "experience",
    "LOCATION": "location",
    "FINAL": "final"
}

# =========================
# MODELS
# =========================

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]

# =========================
# SESSION
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
# LIGHTWEIGHT SEARCH
# =========================

def search_recommendations(query):

    results = []

    query_words = query.lower().split()

    for item in data:

        searchable_text = f"""
        {item.get('name', '')}
        {item.get('description', '')}
        {item.get('category', '')}
        """.lower()

        score = 0

        for word in query_words:

            if word in searchable_text:
                score += 1

        if score > 0:

            results.append({
                "name": item.get("name"),
                "category": item.get("category"),
                "description": item.get("description"),
                "score": score
            })

    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:5]

# =========================
# HOME
# =========================

@app.get("/")
def home():

    return {
        "message": "SHL Chatbot Running Successfully"
    }

# =========================
# CHAT
# =========================

@app.post("/chat")
def chat(req: ChatRequest):

    session_id = req.session_id

    initialize_session(session_id)

    state = conversation_memory[session_id]

    latest_message = req.messages[-1].content.lower()

    # START
    if state["stage"] == STAGES["START"]:

        state["role_interest"] = latest_message
        state["stage"] = STAGES["EXPERIENCE"]

        return {
            "response": "What experience level are you looking for?",
            "stage": state["stage"]
        }

    # EXPERIENCE
    elif state["stage"] == STAGES["EXPERIENCE"]:

        state["experience"] = latest_message
        state["stage"] = STAGES["LOCATION"]

        return {
            "response": "Do you prefer remote or onsite opportunities?",
            "stage": state["stage"]
        }

    # LOCATION
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

    return {
        "response": "Conversation already completed.",
        "recommendations": state["recommendations"],
        "conversation_complete": True
    }