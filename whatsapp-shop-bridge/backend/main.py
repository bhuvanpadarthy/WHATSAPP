"""
FastAPI Server for WhatsApp Cross-Platform Price Sync.
Handles Chrome Extension triggers, Meta Facebook Developer WhatsApp Cloud API,
storage optimization analytics, and live configuration dashboard.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db
import scraper

# Load environment variables
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_FILE)

STATIC_DIR = Path(__file__).parent / "static"


def get_active_meta_credentials():
    """
    Retrieves Meta Developer credentials with priority:
    1. Saved in SQLite meta_config table
    2. Environment variables from .env
    """
    db_config = db.get_meta_config()
    token = db_config.get("whatsapp_token") or os.getenv("WHATSAPP_TOKEN", "").strip()
    phone_id = db_config.get("phone_number_id") or os.getenv("PHONE_NUMBER_ID", "").strip()
    waba_id = db_config.get("waba_id") or os.getenv("WABA_ID", "").strip()
    target_phone = db_config.get("target_phone") or os.getenv("TARGET_PHONE", "919876543210").strip()
    verify_token = os.getenv("VERIFY_TOKEN", "shop_bridge_verify_token_2026").strip()
    callmebot_key = os.getenv("CALLMEBOT_API_KEY", "").strip()

    return {
        "token": token,
        "phone_number_id": phone_id,
        "waba_id": waba_id,
        "target_phone": target_phone,
        "verify_token": verify_token,
        "callmebot_key": callmebot_key
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    db.init_db()
    # Sync initial env values to DB if not present
    env_token = os.getenv("WHATSAPP_TOKEN", "").strip()
    env_phone_id = os.getenv("PHONE_NUMBER_ID", "").strip()
    if env_token and env_phone_id:
        db.save_meta_config(env_token, env_phone_id)
    print("Database & Meta configuration ready.")
    yield


app = FastAPI(
    title="WhatsApp Cross-Platform Price Sync",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for Chrome Extension and Web Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Schemas
class SettingsPayload(BaseModel):
    phone: str
    allow_all: bool


class MetaConfigPayload(BaseModel):
    whatsapp_token: str
    phone_number_id: str
    waba_id: Optional[str] = ""
    target_phone: Optional[str] = ""


class TriggerSearchPayload(BaseModel):
    phone: Optional[str] = None
    query: str
    current_site: Optional[str] = "Web Browser"


class SimulateChatPayload(BaseModel):
    phone: str
    text: str


@app.get("/")
async def serve_dashboard():
    """Serves the Live Control Dashboard & WhatsApp Manager."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="static/index.html not found")
    return FileResponse(str(index_file))


@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    """Updates user's phone number and 'Allow All' status."""
    clean_phone = "".join(filter(str.isdigit, payload.phone))
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    user = db.upsert_user(clean_phone, payload.allow_all)

    # Persist as the active target recipient phone in Meta config as well
    meta_cfg = db.get_meta_config()
    db.save_meta_config(
        token=meta_cfg.get("whatsapp_token", ""),
        phone_number_id=meta_cfg.get("phone_number_id", ""),
        waba_id=meta_cfg.get("waba_id", ""),
        target_phone=clean_phone
    )

    try:
        if ENV_FILE.exists():
            set_key(str(ENV_FILE), "TARGET_PHONE", clean_phone)
    except Exception as e:
        print(f"Warning: Could not update TARGET_PHONE in .env: {e}")

    return {
        "status": "success",
        "message": f"Allow All is {'enabled' if payload.allow_all else 'disabled'} for {clean_phone}",
        "user": user,
        "target_phone": clean_phone
    }


@app.post("/api/meta-config")
async def save_meta_config_endpoint(payload: MetaConfigPayload):
    """
    Saves Meta Facebook Developer Account WhatsApp credentials.
    Persists to SQLite and writes to .env for persistence.
    """
    token = payload.whatsapp_token.strip()
    phone_id = payload.phone_number_id.strip()
    waba = payload.waba_id.strip() if payload.waba_id else ""
    target = "".join(filter(str.isdigit, payload.target_phone or ""))

    if not token or not phone_id:
        raise HTTPException(status_code=400, detail="Both whatsapp_token and phone_number_id are required")

    # Save to SQLite
    db.save_meta_config(token, phone_id, waba, target)

    # Also persist to .env
    try:
        if ENV_FILE.exists():
            set_key(str(ENV_FILE), "WHATSAPP_TOKEN", token)
            set_key(str(ENV_FILE), "PHONE_NUMBER_ID", phone_id)
            if waba:
                set_key(str(ENV_FILE), "WABA_ID", waba)
            if target:
                set_key(str(ENV_FILE), "TARGET_PHONE", target)
    except Exception as e:
        print(f"Warning: Could not write to .env file: {e}")

    # Test the connection immediately
    test_result = await scraper.test_meta_credentials(token, phone_id)

    return {
        "status": "success",
        "message": "Meta Facebook Account credentials saved successfully",
        "validation": test_result
    }


@app.post("/api/meta-test")
async def test_meta_connection():
    """Validates the saved Meta Facebook Developer WhatsApp credentials."""
    creds = get_active_meta_credentials()
    if not creds["token"] or not creds["phone_number_id"]:
        return {
            "valid": False,
            "error": "No Meta credentials configured yet. Please enter your Phone Number ID and Access Token."
        }

    result = await scraper.test_meta_credentials(creds["token"], creds["phone_number_id"])
    return result


@app.post("/api/meta-send-test")
async def send_meta_test_message(payload: Optional[dict] = None):
    """Sends a real test price comparison message from your Meta Business account to verify setup."""
    creds = get_active_meta_credentials()
    target_phone = (payload and payload.get("phone")) or creds["target_phone"] or "919876543210"

    if not creds["token"] or not creds["phone_number_id"]:
        raise HTTPException(status_code=400, detail="Meta credentials are not configured")

    sample_query = "Ergonomic Office Chair"
    comparison, summary = scraper.get_comparison_data(sample_query, "Meta Test Suite")
    test_msg = scraper.format_whatsapp_message(sample_query, "Meta Test Suite", comparison, summary)

    dispatch_res = await scraper.send_meta_whatsapp_message(
        phone=target_phone,
        text=test_msg,
        token=creds["token"],
        phone_number_id=creds["phone_number_id"]
    )

    db.save_message(
        phone=target_phone,
        query=f"TEST: {sample_query}",
        source_site="Meta Test Suite",
        whatsapp_text=test_msg,
        delivery_status=dispatch_res.get("status", "test"),
        winner_platform=summary["winner_platform"],
        lowest_price=summary["lowest_price"]
    )

    return {
        "status": dispatch_res.get("status"),
        "target_phone": target_phone,
        "gateway_response": dispatch_res
    }


@app.get("/api/storage")
async def get_storage_diagnostics():
    """Returns database size, message counts, and storage health metrics."""
    return db.get_storage_stats()


@app.post("/api/storage/vacuum")
async def vacuum_storage():
    """Runs VACUUM to reclaim space and minimize file footprint."""
    return db.vacuum_database()


@app.post("/api/storage/clear")
async def clear_storage():
    """Wipes old message logs and shrinks DB to near zero."""
    return db.clear_message_history()


@app.get("/api/state")
async def get_state():
    """Returns full application state for dashboard and extension."""
    creds = get_active_meta_credentials()
    users = db.get_all_users()
    messages = db.get_recent_messages(limit=25)
    storage = db.get_storage_stats()

    # Mask token for safe UI display (e.g. EAABw...k19Z)
    raw_token = creds["token"]
    masked_token = (raw_token[:6] + "..." + raw_token[-4:]) if len(raw_token) > 12 else ("Set" if raw_token else "")

    return {
        "meta_configured": bool(creds["token"] and creds["phone_number_id"]),
        "meta_details": {
            "phone_number_id": creds["phone_number_id"],
            "token_masked": masked_token,
            "waba_id": creds["waba_id"],
            "target_phone": creds["target_phone"]
        },
        "callmebot_configured": bool(creds["callmebot_key"]),
        "users": users,
        "messages": messages,
        "storage": storage
    }


@app.post("/trigger-search")
async def trigger_search(payload: TriggerSearchPayload):
    """
    Receives search queries detected on Amazon, Flipkart, Meesho, or Myntra.
    1. Validates Allow-All permission.
    2. Deduplicates query (60s cooldown).
    3. Generates 4-platform price & rating comparison.
    4. Automatically dispatches via Meta Facebook Developer WhatsApp Cloud API.
    5. Saves to SQLite with auto-pruning to guarantee minimal storage.
    """
    creds = get_active_meta_credentials()

    # Determine destination phone (prioritize configured target if payload is empty or dummy default)
    clean_payload_phone = "".join(filter(str.isdigit, payload.phone or "")) if payload.phone else ""
    configured_target = "".join(filter(str.isdigit, creds.get("target_phone", "") or ""))

    if configured_target and (not clean_payload_phone or clean_payload_phone == "919876543210"):
        clean_phone = configured_target
    elif clean_payload_phone:
        clean_phone = clean_payload_phone
    elif configured_target:
        clean_phone = configured_target
    else:
        clean_phone = "919876543210"

    clean_query = payload.query.strip()
    if not clean_query:
        return {"status": "ignored", "message": "Empty query"}

    # Fetch user or auto-register with default allow_all=True
    user = db.get_user(clean_phone)
    if not user:
        user = db.upsert_user(clean_phone, allow_all=True)

    # 1. Check Allow All permission
    if not user["allow_all"]:
        return {
            "status": "blocked",
            "message": f"Sync skipped: 'Allow All' is disabled for {clean_phone}.",
            "allow_all": False
        }

    # 2. Deduplicate: Ignore exact same query within 60s
    if db.is_duplicate_recent(clean_phone, clean_query, cooldown_seconds=60):
        return {
            "status": "deduplicated",
            "message": f"Query '{clean_query}' was already synced within the last 60 seconds.",
            "query": clean_query
        }

    # Update search timestamp
    db.update_user_search(clean_phone, clean_query)

    # 3. Generate structured 4-platform comparison
    comparison, summary = scraper.get_comparison_data(clean_query, payload.current_site or "")
    formatted_msg = scraper.format_whatsapp_message(clean_query, payload.current_site or "", comparison, summary)
    wa_direct = scraper.generate_whatsapp_direct_links(clean_phone, formatted_msg)

    # 4. Dispatch via Meta WhatsApp Cloud API (Primary) or Fallback
    delivery_status = "Simulated / Link Ready"
    meta_response = None

    if creds["token"] and creds["phone_number_id"]:
        meta_result = await scraper.send_meta_whatsapp_message(
            phone=clean_phone,
            text=formatted_msg,
            token=creds["token"],
            phone_number_id=creds["phone_number_id"]
        )
        meta_response = meta_result
        if meta_result.get("status") == "sent":
            delivery_status = "Delivered via Meta WhatsApp Cloud API"
        else:
            delivery_status = f"Meta Error: {meta_result.get('error', 'check credentials')}"

    elif creds["callmebot_key"]:
        cmb_result = await scraper.send_callmebot_whatsapp_message(clean_phone, formatted_msg, creds["callmebot_key"])
        if cmb_result.get("status") == "sent":
            delivery_status = "Delivered to Phone via CallMeBot"
        else:
            delivery_status = f"CallMeBot: {cmb_result.get('text', 'sent')}"
    else:
        delivery_status = "Ready (Direct WhatsApp Web/App Link)"

    # 5. Log to DB with auto-pruning (guarantees ultra-low storage)
    msg_id = db.save_message(
        phone=clean_phone,
        query=clean_query,
        source_site=payload.current_site or "Web Browser",
        whatsapp_text=formatted_msg,
        delivery_status=delivery_status,
        winner_platform=summary["winner_platform"],
        lowest_price=summary["lowest_price"]
    )

    return {
        "status": "success",
        "message_id": msg_id,
        "phone": clean_phone,
        "query": clean_query,
        "source_site": payload.current_site,
        "delivery_status": delivery_status,
        "meta_response": meta_response,
        "summary": summary,
        "comparison": comparison,
        "whatsapp_preview": formatted_msg,
        "whatsapp_web_url": wa_direct["web_link"],
        "whatsapp_app_url": wa_direct["app_link"],
        "storage": db.get_storage_stats()
    }


@app.post("/api/simulate-chat")
async def simulate_incoming_chat(payload: SimulateChatPayload):
    """Allows simulated chat commands ('STOP', 'ALLOW ALL') or direct queries."""
    clean_phone = "".join(filter(str.isdigit, payload.phone)) or "919876543210"
    user_text = payload.text.strip()
    upper_text = user_text.upper()

    user = db.get_user(clean_phone)
    if not user:
        user = db.upsert_user(clean_phone, allow_all=True)

    if upper_text in ("STOP", "PAUSE", "DISABLE", "OFF"):
        db.upsert_user(clean_phone, allow_all=False)
        reply = "🛑 *Price Sync Paused*\n\nReply *ALLOW ALL* anytime to resume automatic deal alerts."
        db.save_message(clean_phone, "CMD: STOP", "WhatsApp", reply, "Command Processed")
        return {"status": "paused", "allow_all": False, "reply": reply}

    elif upper_text in ("ALLOW ALL", "ALLOWALL", "START", "RESUME", "ENABLE", "ON"):
        db.upsert_user(clean_phone, allow_all=True)
        reply = "✅ *Price Sync Activated!*\n\nSearch any item on Amazon, Flipkart, Meesho, or Myntra to receive live comparisons."
        db.save_message(clean_phone, "CMD: ALLOW ALL", "WhatsApp", reply, "Command Processed")
        return {"status": "activated", "allow_all": True, "reply": reply}

    else:
        comparison, summary = scraper.get_comparison_data(user_text, "Direct WhatsApp")
        reply = scraper.format_whatsapp_message(user_text, "Direct WhatsApp", comparison, summary)
        db.save_message(clean_phone, user_text, "Direct WhatsApp", reply, "Query Processed", summary["winner_platform"], summary["lowest_price"])
        return {"status": "success", "reply": reply, "comparison": comparison, "summary": summary}


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Meta WhatsApp Cloud API Webhook Verification."""
    creds = get_active_meta_credentials()
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == creds["verify_token"]:
        print("Meta Webhook verified successfully.")
        return Response(content=challenge, media_type="text/plain")
    else:
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receives inbound messages from Meta WhatsApp Business Cloud API."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"status": "invalid json"}, status_code=400)

    try:
        creds = get_active_meta_credentials()
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        sender_phone = msg.get("from")
        msg_type = msg.get("type")

        if msg_type == "text" and sender_phone:
            user_text = msg.get("text", {}).get("body", "").strip().upper()
            
            if user_text in ("STOP", "PAUSE"):
                db.upsert_user(sender_phone, allow_all=False)
                reply = "🛑 Cross-Platform Price Sync has been PAUSED. Reply *ALLOW ALL* to resume."
            elif user_text in ("ALLOW ALL", "START", "RESUME"):
                db.upsert_user(sender_phone, allow_all=True)
                reply = "✅ Cross-Platform Price Sync is ACTIVE!"
            else:
                comparison, summary = scraper.get_comparison_data(user_text, "Meta Inbound")
                reply = scraper.format_whatsapp_message(user_text, "Meta Inbound", comparison, summary)

            if creds["token"] and creds["phone_number_id"]:
                await scraper.send_meta_whatsapp_message(
                    phone=sender_phone,
                    text=reply,
                    token=creds["token"],
                    phone_number_id=creds["phone_number_id"]
                )

            db.save_message(sender_phone, f"INBOUND: {user_text}", "Meta Webhook", reply, "Webhook Handled")

        return {"status": "processed"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
