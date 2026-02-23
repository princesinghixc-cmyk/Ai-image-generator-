import requests
import time
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
TOKEN = "8593E"
COMFY_URL = "http:"
ADMIN_ID = 7152425  # <-- apna Telegram user ID daalo
FREE_DAILY_LIMIT = 10
# ==========================================

# In-memory usage tracking
user_usage = {}

# 🔞 Block Words
BLOCKED_WORDS = [
    "nude","gay",naked", "sex", "porn", "nsfw",
    "boobs", "breast", "ass", "pussy", "xxx"
]

BAD_WORDS = [
    "sexy", "babe", "fuck", "slut", "bitch"
]

def is_valid_english_prompt(text):
    if not re.fullmatch(r"[A-Za-z0-9 ,.]+", text):
        return False
    if len(text.split()) < 3:
        return False
    return True

def contains_blocked_words(text):
    text = text.lower()
    for word in BLOCKED_WORDS + BAD_WORDS:
        if word in text:
            return True
    return False

def enhance_prompt(prompt):
    return f"ultra realistic {prompt}, cinematic lighting, 8k resolution, sharp focus, professional photography"

def check_daily_limit(user_id):
    today = datetime.utcnow().date()

    if user_id not in user_usage:
        user_usage[user_id] = {"count": 0, "date": today}

    if user_usage[user_id]["date"] != today:
        user_usage[user_id] = {"count": 0, "date": today}

    if user_usage[user_id]["count"] >= FREE_DAILY_LIMIT:
        return False

    user_usage[user_id]["count"] += 1
    return True

def generate_image(prompt_text):

    workflow = {
        "3": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "realisticVisionV60B1_v51HyperVAE.safetensors"
            }
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1}
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["3", 1]}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "blurry, low quality", "clip": ["3", 1]}
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["4", 0],
                "seed": int(time.time() * 1000),
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1
            }
        },
        "8": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "vae-ft-mse-840000-ema-pruned.ckpt"}
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["8", 0]}
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["9", 0], "filename_prefix": "telegram"}
        }
    }

    response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow})
    response.raise_for_status()
    prompt_id = response.json()["prompt_id"]

    while True:
        history = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
        if prompt_id in history:
            break
        time.sleep(0.2)

    image_filename = list(history[prompt_id]["outputs"].values())[0]["images"][0]["filename"]

    return requests.get(
        f"{COMFY_URL}/view?filename={image_filename}&type=output"
    ).content


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    if not is_valid_english_prompt(user_text):
        await update.message.reply_text("❌  Use proper sentence only (first add create image).")
        return

    if contains_blocked_words(user_text):
        await update.message.reply_text("❌ Unsafe content detected.")
        return

    if user_id != 7177843812:
        if not check_daily_limit(user_id):
            await update.message.reply_text("🚫 Daily free limit reached (1000000000000000 images). Come back tomorrow.")
            return

    enhanced_prompt = enhance_prompt(user_text)

    await update.message.reply_text("⚡ Generating image...")

    try:
        image = generate_image(enhanced_prompt)
        await update.message.reply_photo(photo=image)
    except Exception:
        await update.message.reply_text("❌ Image generation failed.")


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Bot running with Monetization + Prompt Enhancer...")
app.run_polling()
