import logging
import json
import os
import base64
import threading
import re
import uuid
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from jose import jwt, JWTError
from fastapi import Depends
from starlette.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
from database import initialize_database, database_is_ready
from security import install_security

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smarthub")

app = FastAPI(title="SmartHub AI API", version="1.2.0")
install_security(app)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origin.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.on_event("startup")
def startup():
    try:
        initialize_database()
    except Exception:
        logger.exception("PostgreSQL initialization failed")

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
        "database": "connected" if database_is_ready() else "unavailable",
        "providers": {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "huggingface": bool(os.getenv("HF_TOKEN")),
            "cloudflare_image": bool(os.getenv("CLOUDFLARE_ACCOUNT_ID") and os.getenv("CLOUDFLARE_API_TOKEN")),
            "ovh_image": True,
            "pollinations_image": bool(os.getenv("POLLINATIONS_API_KEY")),
            "gemini_image": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "ltx_video_public": True,
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


# Image generation through OVHcloud SDXL, Pollinations FLUX, or Cloudflare FLUX.
class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    provider: str = Field(default="gemini", pattern="^(gemini|ovh|pollinations|cloudflare)$")
    quality: str = Field(default="speed", pattern="^(speed|quality)$")


class ImageEditRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    image_base64: str = Field(min_length=100, max_length=17000000)
    mime_type: str = Field(pattern="^(image/png|image/jpeg|image/webp)$")


def image_data_uri(image_bytes, content_type="image/png"):
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return "data:" + content_type + ";base64," + encoded


def extract_gemini_image(data):
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data") or {}
            encoded = inline.get("data")
            mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            if encoded:
                return image_data_uri(base64.b64decode(encoded), mime)
    raise RuntimeError("Google Gemini returned no image data")


def call_gemini_image(parts):
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent",
        params={"key": key},
        json={
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        },
        timeout=240,
    )
    if not response.ok:
        logger.error("Gemini image API returned HTTP %s: %s", response.status_code, response.text[:1200])
    response.raise_for_status()
    return extract_gemini_image(response.json())


def generate_gemini_image(payload):
    image = call_gemini_image([{"text": payload.prompt.strip()}])
    return {
        "image": image,
        "model": "Gemini 3.1 Flash Image (Nano Banana 2)",
        "provider": "Google Gemini",
    }


def generate_ovh_image(payload):
    # OVHcloud permits anonymous inference with a limit of 2 requests/minute/model/IP.
    # An access token is optional and raises the documented rate limit.
    endpoint = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/images/generations"
    headers = {"Content-Type": "application/json"}
    token = os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    response = requests.post(
        endpoint,
        headers=headers,
        json={
            "model": "stable-diffusion-xl-base-v10",
            "prompt": payload.prompt.strip(),
            "n": 1,
            "size": "1024x1024",
        },
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    items = data.get("data") or []
    image_base64 = items[0].get("b64_json") if items and isinstance(items[0], dict) else None
    if not image_base64:
        raise RuntimeError("OVHcloud returned no image data")
    return {
        "image": "data:image/png;base64," + image_base64,
        "model": "Stable Diffusion XL",
        "provider": "OVHcloud AI Endpoints",
    }


def generate_pollinations_image(payload):
    api_key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("POLLINATIONS_API_KEY is not configured")
    from urllib.parse import quote
    prompt = quote(payload.prompt.strip(), safe="")
    endpoint = "https://gen.pollinations.ai/image/" + prompt
    response = requests.get(
        endpoint,
        params={"model": "black-forest-labs/flux.1-schnell"},
        headers={"Authorization": "Bearer " + api_key},
        timeout=180,
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
    if not content_type.startswith("image/"):
        raise RuntimeError("Pollinations returned a non-image response")
    return {
        "image": image_data_uri(response.content, content_type),
        "model": "FLUX.1 schnell",
        "provider": "Pollinations",
    }


def generate_cloudflare_image(payload):
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not api_token:
        raise RuntimeError("Cloudflare Workers AI credentials are not configured")
    prompt = payload.prompt.strip()
    if len(prompt) > 2048:
        raise ValueError("FLUX.1 schnell accepts prompts up to 2048 characters")
    endpoint = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + account_id
        + "/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    response = requests.post(
        endpoint,
        headers={
            "Authorization": "Bearer " + api_token,
            "Content-Type": "application/json",
        },
        json={"prompt": prompt, "steps": 4 if payload.quality == "speed" else 8},
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    result = data.get("result") or {}
    image_base64 = result.get("image") if isinstance(result, dict) else None
    if not image_base64:
        raise RuntimeError("Cloudflare returned no generated image")
    return {
        "image": "data:image/jpeg;charset=utf-8;base64," + image_base64,
        "model": "FLUX.1 schnell",
        "provider": "Cloudflare Workers AI",
    }


IMAGE_PROVIDERS = {
    "gemini": generate_gemini_image,
    "ovh": generate_ovh_image,
    "pollinations": generate_pollinations_image,
    "cloudflare": generate_cloudflare_image,
}


# Authentication and support API
bearer = HTTPBearer(auto_error=False)
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)
    admin_setup_key: str = Field(default="", max_length=200)

class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=10000)

class TicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

class ReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

def db_connect():
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url:
        raise HTTPException(status_code=503, detail="قاعدة البيانات غير مهيأة")
    return psycopg.connect(url, connect_timeout=10, row_factory=dict_row)

def ensure_auth_config():
    if len(JWT_SECRET) < 32:
        raise HTTPException(status_code=503, detail="أضف JWT_SECRET بطول 32 حرفاً على الأقل في Render")

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + digest.hex()

def password_matches(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        candidate = password_hash(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except Exception:
        return False

def admin_email(email):
    allowed = {x.strip().lower() for x in os.getenv("ADMIN_EMAILS", "").split(",") if x.strip()}
    return email.lower() in allowed

def make_token(profile):
    ensure_auth_config()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(profile["id"]), "iat": now,
                       "exp": now + timedelta(hours=24)}, JWT_SECRET, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    ensure_auth_config()
    if not credentials:
        raise HTTPException(status_code=401, detail="سجّل الدخول أولاً")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = str(uuid.UUID(payload.get("sub", "")))
    except Exception:
        raise HTTPException(status_code=401, detail="جلسة الدخول غير صالحة")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,email,display_name,role,created_at FROM profiles WHERE id=%s", (user_id,))
            user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="الحساب غير موجود")
    return user

@app.post("/api/images/edit")
async def edit_image(payload: ImageEditRequest, user=Depends(current_user)):
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
        if len(image_bytes) > 12 * 1024 * 1024:
            raise ValueError("حجم الصورة يتجاوز الحد المسموح (12 MB).")
        result_image = await run_in_threadpool(
            call_gemini_image,
            [
                {"text": payload.prompt.strip()},
                {"inline_data": {
                    "mime_type": payload.mime_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }},
            ],
        )
        logger.info("Google Gemini image edited for user %s", user["id"])
        return {
            "image": result_image,
            "model": "Gemini 3.1 Flash Image (Nano Banana 2)",
            "provider": "Google Gemini",
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Gemini image editing failed")
        raise HTTPException(
            status_code=502,
            detail="تعذر تعديل الصورة عبر Google Gemini: " + type(exc).__name__ + ". تحقق من المفتاح وحصة الاستخدام وسجلات Render.",
        )


@app.post("/api/images/generate")
async def generate_image(payload: ImageGenerateRequest, user=Depends(current_user)):
    try:
        provider = IMAGE_PROVIDERS[payload.provider]
        result = await run_in_threadpool(provider, payload)
        logger.info("%s image generated for user %s", result["provider"], user["id"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("%s image generation failed", payload.provider)
        raise HTTPException(
            status_code=502,
            detail="تعذر توليد الصورة عبر المزود المختار (" + payload.provider + "): " + type(exc).__name__ + ". تحقق من إعداد المزود وسجلات Render.",
        )

def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية للإدارة فقط")
    return user

@app.post("/api/auth/register")
def register(payload: RegisterRequest):
    ensure_auth_config()
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="البريد الإلكتروني غير صالح")
    user_id = uuid.uuid4()
    setup_key = os.getenv("ADMIN_SETUP_KEY", "")
    is_admin = bool(setup_key) and admin_email(email) and hmac.compare_digest(payload.admin_setup_key, setup_key)
    role = "admin" if is_admin else "user"
    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO profiles (id,auth_subject,email,display_name,role,password_hash)
                               VALUES (%s,%s,%s,%s,%s,%s)
                               RETURNING id,email,display_name,role,created_at""",
                            (str(user_id),str(user_id),email,payload.display_name.strip(),role,password_hash(payload.password)))
                profile = cur.fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="هذا البريد مسجل مسبقاً")
    return {"token": make_token(profile), "user": profile}

@app.post("/api/auth/google")
def google_login(payload: GoogleLoginRequest):
    ensure_auth_config()
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="تسجيل Google غير مهيأ على الخادم")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        claims = id_token.verify_oauth2_token(payload.credential, google_requests.Request(), client_id, clock_skew_in_seconds=10)
        if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com") or claims.get("email_verified") is not True:
            raise ValueError("Untrusted Google identity")
        subject = str(claims["sub"])
        email = str(claims["email"]).strip().lower()
        display_name = str(claims.get("name") or email.split("@")[0])[:80]
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Invalid email")
    except Exception:
        logger.warning("Google sign-in token verification failed")
        raise HTTPException(status_code=401, detail="تعذر التحقق من حساب Google. حاول مجدداً.")
    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id,email,display_name,role,created_at FROM profiles WHERE auth_subject=%s", ("google:" + subject,))
                profile = cur.fetchone()
                if not profile:
                    cur.execute("SELECT id,email,display_name,role,created_at FROM profiles WHERE LOWER(email)=LOWER(%s)", (email,))
                    profile = cur.fetchone()
                if profile:
                    cur.execute("""UPDATE profiles SET auth_subject=%s,email=%s,
                                   display_name=COALESCE(NULLIF(display_name,''),%s)
                                   WHERE id=%s RETURNING id,email,display_name,role,created_at""",
                                ("google:" + subject,email,display_name,str(profile["id"])))
                else:
                    cur.execute("""INSERT INTO profiles (id,auth_subject,email,display_name,role)
                                   VALUES (%s,%s,%s,%s,'user') RETURNING id,email,display_name,role,created_at""",
                                (str(uuid.uuid4()),"google:" + subject,email,display_name))
                profile = cur.fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="هذا الحساب مرتبط مسبقاً بحساب آخر")
    if profile["role"] == "admin" and not admin_email(email):
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE profiles SET role='user' WHERE id=%s RETURNING id,email,display_name,role,created_at", (str(profile["id"]),))
                profile = cur.fetchone()
    return {"token": make_token(profile), "user": profile}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    ensure_auth_config()
    email = payload.email.strip().lower()
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,email,display_name,role,password_hash,created_at FROM profiles WHERE email=%s", (email,))
            profile = cur.fetchone()
            if not profile or not profile.get("password_hash") or not password_matches(payload.password, profile["password_hash"]):
                raise HTTPException(status_code=401, detail="البريد أو كلمة المرور غير صحيحة")
            role = "admin" if (profile["role"] == "admin" and admin_email(email)) else "user"
            cur.execute("UPDATE profiles SET role=%s WHERE id=%s RETURNING id,email,display_name,role,created_at", (role,str(profile["id"])))
            profile = cur.fetchone()
    return {"token": make_token(profile), "user": profile}

@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return {"user": user}

@app.post("/api/support/tickets")
def create_ticket(payload: TicketRequest, user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO support_tickets (user_id,subject,message) VALUES (%s,%s,%s) RETURNING id,subject,message,status,priority,created_at,updated_at",
                        (str(user["id"]),payload.subject.strip(),payload.message.strip()))
            return cur.fetchone()

@app.get("/api/support/tickets")
def list_tickets(user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            if user["role"] == "admin":
                cur.execute("""SELECT t.id,t.user_id,p.email,t.subject,t.message,t.status,t.priority,t.created_at,t.updated_at
                               FROM support_tickets t JOIN profiles p ON p.id=t.user_id ORDER BY t.updated_at DESC LIMIT 200""")
            else:
                cur.execute("""SELECT id,user_id,subject,message,status,priority,created_at,updated_at
                               FROM support_tickets WHERE user_id=%s ORDER BY updated_at DESC""",(str(user["id"]),))
            return {"tickets":cur.fetchall()}

@app.get("/api/support/tickets/{ticket_id}/replies")
def list_replies(ticket_id: int, user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM support_tickets WHERE id=%s",(ticket_id,))
            ticket=cur.fetchone()
            if not ticket: raise HTTPException(status_code=404,detail="التذكرة غير موجودة")
            if user["role"]!="admin" and str(ticket["user_id"])!=str(user["id"]):
                raise HTTPException(status_code=403,detail="لا يمكنك الوصول إلى هذه التذكرة")
            cur.execute("""SELECT r.id,r.ticket_id,r.sender_role,r.message,r.created_at,p.display_name
                           FROM support_replies r LEFT JOIN profiles p ON p.id=r.sender_user_id
                           WHERE r.ticket_id=%s ORDER BY r.created_at""",(ticket_id,))
            return {"replies":cur.fetchall()}

@app.post("/api/support/tickets/{ticket_id}/replies")
def add_reply(ticket_id: int,payload: ReplyRequest,user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM support_tickets WHERE id=%s FOR UPDATE",(ticket_id,))
            ticket=cur.fetchone()
            if not ticket: raise HTTPException(status_code=404,detail="التذكرة غير موجودة")
            if user["role"]!="admin" and str(ticket["user_id"])!=str(user["id"]):
                raise HTTPException(status_code=403,detail="لا يمكنك الرد على هذه التذكرة")
            role="admin" if user["role"]=="admin" else "user"
            cur.execute("""INSERT INTO support_replies (ticket_id,sender_user_id,sender_role,message)
                           VALUES (%s,%s,%s,%s) RETURNING id,ticket_id,sender_role,message,created_at""",
                        (ticket_id,str(user["id"]),role,payload.message.strip()))
            reply=cur.fetchone()
            cur.execute("UPDATE support_tickets SET status=%s,updated_at=NOW() WHERE id=%s",
                        ("answered" if role=="admin" else "in_progress",ticket_id))
            return reply

@app.patch("/api/support/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: int,status: str,user=Depends(require_admin)):
    if status not in {"open","in_progress","answered","closed"}:
        raise HTTPException(status_code=422,detail="حالة التذكرة غير صالحة")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE support_tickets SET status=%s,updated_at=NOW() WHERE id=%s RETURNING id,status",(status,ticket_id))
            result=cur.fetchone()
            if not result: raise HTTPException(status_code=404,detail="التذكرة غير موجودة")
            return result



# Free public LTX-Video model hosted on Hugging Face Spaces.
# No paid video-provider account or API key is required. An optional HF_TOKEN
# can improve public Space rate limits, but anonymous requests are supported.
LTX_SPACE_URL = "https://lightricks-ltx-video-distilled.hf.space"
_video_jobs = {}
_video_jobs_lock = threading.Lock()


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    duration: float = Field(default=5, ge=0.3, le=8.5)
    aspect_ratio: str = Field(default="16:9", pattern="^(16:9|9:16|1:1)$")


def _ltx_headers():
    headers = {"Content-Type": "application/json"}
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _extract_ltx_video(payload):
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if isinstance(payload, dict):
        video = payload.get("video", payload)
        if isinstance(video, dict):
            return video.get("url") or video.get("path")
        if isinstance(video, str):
            return video
    if isinstance(payload, str) and payload.startswith(("http://", "https://")):
        return payload
    return None


def _run_ltx_video_job(job_id, prompt, duration, aspect_ratio, owner_id):
    try:
        dimensions = {
            "16:9": (432, 768),
            "9:16": (768, 432),
            "1:1": (512, 512),
        }
        height, width = dimensions[aspect_ratio]
        # Arguments follow the public Lightricks Space text_to_video API.
        data = [
            prompt,
            "worst quality, blurry, distorted, watermark",
            "",
            "",
            height,
            width,
            "text-to-video",
            float(duration),
            9,
            42,
            True,
            1,
            True,
        ]
        submit = requests.post(
            LTX_SPACE_URL + "/gradio_api/call/text_to_video",
            headers=_ltx_headers(),
            json={"data": data},
            timeout=45,
        )
        submit.raise_for_status()
        event_id = submit.json().get("event_id")
        if not event_id:
            raise RuntimeError("لم يُرجع نموذج الفيديو رقم المهمة.")

        with _video_jobs_lock:
            if job_id in _video_jobs:
                _video_jobs[job_id]["status"] = "running"

        with requests.get(
            LTX_SPACE_URL + "/gradio_api/call/text_to_video/" + event_id,
            headers=_ltx_headers(),
            stream=True,
            timeout=(20, 300),
        ) as response:
            response.raise_for_status()
            event_name = None
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8", "replace")
                line = raw_line.strip()
                if line.startswith("event:"):
                    event_name = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and event_name in ("complete", "error"):
                    raw_data = line.split(":", 1)[1].strip()
                    if event_name == "error":
                        raise RuntimeError("تعذر على النموذج إكمال التوليد.")
                    result = json.loads(raw_data)
                    video_url = _extract_ltx_video(result)
                    if not video_url:
                        raise RuntimeError("أعاد النموذج نتيجة دون رابط فيديو.")
                    with _video_jobs_lock:
                        if job_id in _video_jobs:
                            _video_jobs[job_id].update({
                                "status": "complete",
                                "video_url": video_url,
                                "error": None,
                            })
                    return

        raise RuntimeError("انتهى اتصال النموذج قبل وصول الفيديو.")
    except Exception as exc:
        logger.exception("Public LTX video generation failed for job %s", job_id)
        with _video_jobs_lock:
            if job_id in _video_jobs:
                _video_jobs[job_id].update({
                    "status": "error",
                    "error": str(exc)[:400],
                })


@app.post("/api/video/generate")
def generate_video(payload: VideoGenerateRequest, user=Depends(current_user)):
    job_id = uuid.uuid4().hex
    with _video_jobs_lock:
        _video_jobs[job_id] = {
            "owner_id": str(user["id"]),
            "status": "queued",
            "video_url": None,
            "error": None,
        }
    worker = threading.Thread(
        target=_run_ltx_video_job,
        args=(job_id, payload.prompt.strip(), payload.duration, payload.aspect_ratio, str(user["id"])),
        daemon=True,
    )
    worker.start()
    logger.info("Public LTX video job %s queued for user %s", job_id, user["id"])
    return {"project_id": job_id, "status": "queued", "provider": "LTX-Video"}


@app.get("/api/video/status/{project_id}")
def video_status(project_id: str, user=Depends(current_user)):
    if not re.fullmatch(r"[A-Fa-f0-9]{32}", project_id):
        raise HTTPException(status_code=422, detail="رقم المهمة غير صالح.")
    with _video_jobs_lock:
        job = _video_jobs.get(project_id)
        if not job or job["owner_id"] != str(user["id"]):
            raise HTTPException(status_code=404, detail="المهمة غير موجودة أو لا تملك صلاحية الوصول إليها.")
        return {
            "project_id": project_id,
            "status": job["status"],
            "video_url": job["video_url"],
            "error": job["error"],
        }
