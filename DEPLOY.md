# Deploying Living Reading to Render

## 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/livingreading.git
git push -u origin main
```

If the repo already exists on GitHub, skip `git init` / `git remote add` and just push.

---

## 2. Create a Render Web Service

1. Go to [render.com](https://render.com) and sign in.
2. Click **New → Web Service**.
3. Connect your GitHub account and select the `livingreading` repository.
4. Render will detect `render.yaml` automatically — click **Apply** to use it, or fill in the fields below manually.

---

## 3. Build command

```
pip install -r requirements.txt
```

---

## 4. Start command

```
gunicorn -k eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

> **Why `-w 1`?**  
> Socket.IO keeps game state in memory. Multiple workers would each have their own isolated state.  
> One worker with eventlet's async concurrency handles 30+ simultaneous WebSocket connections easily.

---

## 5. Environment variables

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Any long random string. Render can generate one automatically if you use `render.yaml`. |
| `PORT` | Set by Render | Do not set this manually — Render injects it. |

To set `SECRET_KEY` manually: in the Render dashboard → your service → **Environment** → **Add Environment Variable**.

---

## 6. After deploy

- Your app URL will be `https://livingreading.onrender.com` (or similar).
- Open `/stage` on the presenter's device: `https://livingreading.onrender.com/stage`
- The QR code on the stage view already uses `window.location.origin`, so it will show the correct public URL for participants to scan.

---

## Notes for live sessions

- **Free tier hibernation:** Render's free tier puts services to sleep after 15 minutes of inactivity. Upgrade to the **Starter** plan ($7/month) before a session so the service stays awake.
- **Concurrent users:** 15–30 participants over WebSocket is well within limits. The eventlet worker handles async I/O with a single process.
- **No database:** All game state is in-memory and resets when the service restarts. This is intentional — each session is ephemeral.
