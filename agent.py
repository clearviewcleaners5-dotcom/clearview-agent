"""
CVC Content Agent
-----------------
Runs two scheduled jobs:
  1. 6:00 AM Mountain Time daily  → Generate a video concept + script
  2. 5:00 PM Mountain Time Mon/Wed/Fri → Pull latest video from Dropbox, post to Facebook

Required environment variables (set these in Vercel):
  ANTHROPIC_API_KEY      - Your Claude API key
  DROPBOX_ACCESS_TOKEN   - Dropbox app access token
  META_PAGE_ACCESS_TOKEN - Facebook Page access token
  META_PAGE_ID           - Your Facebook Page ID
  INSTAGRAM_ACCOUNT_ID   - Your Instagram Business Account ID
"""

import os
import io
import requests
import dropbox
from dropbox.exceptions import ApiError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import anthropic
from datetime import datetime
from flask import Flask, jsonify, Response

app = Flask(__name__)

MOUNTAIN = pytz.timezone("America/Edmonton")
DROPBOX_FOLDER = "/CVC videos"
META_API_VERSION = "v20.0"
META_BASE = f"https://graph.facebook.com/{META_API_VERSION}"

CONTENT_THEMES = [
    "satisfying before/after transformation",
    "water fed pole technique close-up",
    "squeegee ASMR / oddly satisfying",
    "storytime - funny customer moment",
    "educational: why soft wash beats pressure wash",
    "team culture / day in the life",
    "storytime - most satisfying job ever",
    "myth bust: DIY window cleaning mistakes",
    "client testimonial / reaction",
    "timelapse of full house exterior clean",
]


def get_clients():
    claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    dbx = dropbox.Dropbox(os.environ.get("DROPBOX_ACCESS_TOKEN"))
    return claude, dbx


def generate_daily_concept():
    claude, _ = get_clients()
    today = datetime.now(MOUNTAIN).strftime("%A, %B %d")
    theme = CONTENT_THEMES[datetime.now(MOUNTAIN).timetuple().tm_yday % len(CONTENT_THEMES)]

    prompt = f"""You are a social media strategist for Clearest View Cleaners (CVC), a window cleaning,
soft washing, pressure washing, and gutter cleaning company in Medicine Hat, Alberta, Canada.
They post short-form vertical video (Reels / TikTok style) 3x per week.

Today is {today}. Generate a video concept based on this theme: "{theme}".

Return EXACTLY this structure with these exact section headers and emoji markers:

🎬 VIDEO CONCEPT OF THE DAY
Theme: {theme}
Date: {today}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎣 HOOK (first 3 seconds on screen):
[Write a punchy hook line — this is the first thing viewers see or hear]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 SCRIPT OUTLINE (30–60 seconds):
Step 1: [what to say/show]
Step 2: [what to say/show]
Step 3: [what to say/show]
Step 4: [what to say/show]
Step 5: [end card or CTA]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 FILMING TIPS:
• [tip 1]
• [tip 2]
• [tip 3]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✂️ EDITING NOTES:
• Speed / pacing: [note]
• Music vibe: [note]
• Text overlays: [note]
• Transitions: [note]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📘 FACEBOOK CAPTION:
[Write the full Facebook caption here — conversational, local Medicine Hat feel, ends with a CTA]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📸 INSTAGRAM CAPTION:
[Write the full Instagram caption here — punchy opener, same video, include hashtags at the bottom]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ POST: Monday, Wednesday, or Friday at 5 PM Mountain Time
"""

    message = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )
    concept = message.content[0].text
    print(f"\nCVC DAILY CONCEPT — {today}\n{concept}")
    return concept


def get_latest_video_from_dropbox():
    _, dbx = get_clients()
    try:
        result = dbx.files_list_folder(DROPBOX_FOLDER)
        video_files = [
            f for f in result.entries
            if isinstance(f, dropbox.files.FileMetadata)
            and f.name.lower().endswith(('.mp4', '.mov', '.avi', '.m4v'))
        ]
        if not video_files:
            return None, None
        latest = sorted(video_files, key=lambda f: f.server_modified, reverse=True)[0]
        _, response = dbx.files_download(latest.path_lower)
        return response.content, latest.name
    except ApiError as e:
        print(f"Dropbox error: {e}")
        return None, None


def post_to_facebook(video_bytes, caption):
    page_id = os.environ.get("META_PAGE_ID")
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    upload_url = f"{META_BASE}/{page_id}/videos"
    files = {"source": ("video.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"description": caption, "access_token": token, "published": "true"}
    resp = requests.post(upload_url, files=files, data=data)
    result = resp.json()
    if "id" in result:
        print(f"Posted to Facebook! Video ID: {result['id']}")
        return True
    print(f"Facebook post failed: {result}")
    return False


def post_scheduled_content():
    claude, _ = get_clients()
    today = datetime.now(MOUNTAIN).strftime("%A")
    video_bytes, filename = get_latest_video_from_dropbox()
    if not video_bytes:
        print("No video to post.")
        return
    msg = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": f"Write a short punchy Facebook caption for Clearest View Cleaners, a window cleaning and exterior services company in Medicine Hat, Alberta. Under 150 words, conversational, end with a call to action. Today is {today}."}]
    )
    caption = msg.content[0].text
    post_to_facebook(video_bytes, caption)


scheduler = BackgroundScheduler(timezone=MOUNTAIN)
scheduler.add_job(generate_daily_concept, CronTrigger(hour=6, minute=0, timezone=MOUNTAIN), id="daily_concept")
scheduler.add_job(post_scheduled_content, CronTrigger(day_of_week="mon,wed,fri", hour=17, minute=0, timezone=MOUNTAIN), id="scheduled_post")
scheduler.start()


@app.route("/")
def index():
    return jsonify({"status": "CVC Content Agent is running ✅"})


@app.route("/test-concept")
def test_concept():
    concept = generate_daily_concept()
    # Return as plain text so it's readable in the browser
    return Response(concept, mimetype="text/plain; charset=utf-8")


@app.route("/test-post")
def test_post():
    post_scheduled_content()
    return jsonify({"status": "Post triggered"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
