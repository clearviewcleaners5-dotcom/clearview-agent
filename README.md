# CVC Content Agent 🪟

Automated social media agent for Clearest View Cleaners.

## What It Does
- **6:00 AM Mountain Time daily** → Generates a video concept, hook, script outline, filming tips, editing notes, and captions for both Facebook and Instagram
- **5:00 PM Mon / Wed / Fri** → Pulls the latest video from your Dropbox "CVC Videos" folder and posts it to Facebook with an AI-generated caption

---

## Setup Steps

### 1. Install dependencies (local testing)
```bash
pip install -r requirements.txt
```

### 2. Set your environment variables
Copy `.env.example` to `.env` and fill in your values:
- `ANTHROPIC_API_KEY` → Your Claude API key from console.anthropic.com
- `DROPBOX_ACCESS_TOKEN` → From your Dropbox developer app
- `META_PAGE_ACCESS_TOKEN` → From your Meta for Developers app dashboard
- `META_PAGE_ID` → Your Facebook Page ID (find in Facebook Page settings)
- `INSTAGRAM_ACCOUNT_ID` → Your Instagram Business Account ID (in Meta Business Suite)

### 3. Test locally
```bash
python agent.py
```
This will run a concept generation test and check your Dropbox connection immediately.

### 4. Deploy to Vercel
1. Push this folder to a GitHub repo
2. Connect that repo to Vercel
3. Add all environment variables in Vercel → Settings → Environment Variables
4. Deploy

---

## How to Use Day-to-Day

1. Film your video based on the 6 AM concept brief
2. Edit it (CapCut recommended)
3. Upload the finished video to your **Dropbox > CVC Videos** folder
4. The agent automatically posts it at 5 PM on the next Mon/Wed/Fri

---

## Finding Your Facebook Page ID
Go to your Facebook Page → About → scroll down → Page ID is listed there.

## Finding Your Instagram Account ID
In Meta Business Suite → Settings → Accounts → Instagram Accounts → click your account → the ID is in the URL.

---

## Upgrading Later
- Add Discord webhook to send the 6 AM brief to your phone via Discord
- Add leaderboard/sales agent once Homebase 360 API is unlocked
- Add TikTok posting once you have TikTok for Business API access
