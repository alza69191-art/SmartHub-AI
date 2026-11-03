import logging
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smarthub")

app = FastAPI(title="SmartHub AI API", version="1.1.0")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origin.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[dict] = Field(default_factory=list)

def build_messages(payload):
    messages = [{
        "role": "system",
        "content": "You are SmartHub AI, a helpful, accurate assistant. Reply in the user's language. Be concise, structured, and honest about uncertainty."
    }]
    for item in payload.history[-10:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:4000]})
    messages.append({"role": "user", "content": payload.message})
    return messages

def ask_groq(messages):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    result = Groq(api_key=key).chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.7,
        max_tokens=1200,
    )
    return result.choices[0].message.content or ""

def ask_gemini(messages):
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    contents = []
    system_text = ""
    for item in messages:
        if item["role"] == "system":
            system_text = item["content"]
        else:
            contents.append({
                "role": "model" if item["role"] == "assistant" else "user",
                "parts": [{"text": item["content"]}]
            })
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        params={"key": key},
        json={
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(
        part.get("text", "")
        for part in data["candidates"][0]["content"]["parts"]
        if "text" in part
    )

def ask_huggingface(messages):
    key = os.getenv("HF_TOKEN")
    if not key:
        raise RuntimeError("HF_TOKEN is not configured")
    response = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-oss-120b:fastest",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"].get("content") or ""

@app.get("/")
def root():
    return {"service": "SmartHub AI API", "status": "online"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "providers": {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "huggingface": bool(os.getenv("HF_TOKEN")),
        },
    }

@app.post("/api/chat")
def chat(payload: ChatRequest):
    messages = build_messages(payload)
    providers = [
        ("Groq", ask_groq),
        ("Google Gemini", ask_gemini),
        ("Hugging Face", ask_huggingface),
    ]
    errors = []
    for name, provider in providers:
        try:
            reply = provider(messages)
            if reply.strip():
                logger.info("Chat request completed with %s", name)
                return {"reply": reply, "provider": name}
            raise RuntimeError("Provider returned an empty response")
        except Exception as exc:
            # Log provider errors server-side without exposing API keys to the browser.
            logger.exception("%s request failed", name)
            errors.append(f"{name}: {type(exc).__name__}")
    raise HTTPException(
        status_code=502,
        detail="All configured AI providers failed. Check Render logs and verify API keys, model access, and quotas. " + "; ".join(errors),
    )
