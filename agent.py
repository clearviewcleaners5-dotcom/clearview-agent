"""
CVC Content Agent
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
from flask import Flask, jsonify

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
They post short-form vertical video 3x per week. Today is {today}.
Generate a video concept based on this theme: "{theme}".

Return EXACTLY this structure:

VIDEO CONCEPT OF THE DAY
Theme: {theme}

HOOK (first 3 seconds):
[punchy hook]

SCRIPT OUTLINE (30-60 seconds):
[step by step]

FILMING TIPS:
[2-3 phone filming tips]

EDITING NOTES:
[cuts, music, text overlays]

FACEBOOK CAPTION:
[conversational, local, ends with CTA]

INSTAGRAM CAPTION:
[with hashtags]"""

    message = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    concept = message.content[0].text
    print(f"CVC DAILY CONCEPT — {today}\n{concept}")
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
    return jsonify({"status": "CVC Content Agent is running"})

@app.route("/test-concept")
def test_concept():
    concept = generate_daily_concept()
    return jsonify({"concept": concept})

@app.route("/test-post")
def test_post():
    post_scheduled_content()
    return jsonify({"status": "Post triggered"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
