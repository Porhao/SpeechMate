# Deploying SpeechMate (frontend on Vercel)

**Recommended:** the Next.js frontend on Vercel, and the backend (FastAPI, Postgres, Kokoro voice) on one Linux server with Docker.

- **Why not the backend on Vercel too?** A Vercel function has:
  - no ffmpeg or LibreOffice;
  - no lasting disk;
  - a 500 MB size cap (the analysis models alone are about 2 GB);
  - nothing that runs after the response is sent, which is how session analysis works.

  Moving the backend there would lose pronunciation, eye contact, posture and emotion scoring, and .pptx upload (Option B below).
- **The server keeps every feature as it runs today:** it is the same `docker compose` stack.

```
Browser ──► speechmate.vercel.app      (Vercel: Next.js)
        └─► api.<your-domain>          (your server: Caddy HTTPS → backend → Postgres, Kokoro)
                 └─► Groq (speech-to-text), Gemini (LLM)
```

## 1. The server

### Size

You need **2 vCPU, 4 GB RAM (8 GB is more comfortable), 40 GB disk, Ubuntu 24.04, x86-64**. The analysis models load on first use and need about 2–3 GB while a session is analysed.

| Option | Cost for an FYP |
|---|---|
| DigitalOcean (GitHub Student Developer Pack: US$200 credit) | 4 GB droplet ≈ US$24/month: about 8 months free |
| Azure for Students (US$100 credit, no card) | B2s VM ≈ US$30/month: about 3 months free |
| Oracle Cloud Always Free (ARM, 24 GB) | free, but ARM: the image is untested there |

### Setup

1. **Open the ports.** In the provider's firewall, open 22, 80 and 443 only.
2. **Install Docker.** SSH in, then:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER   # log out and back in
   ```
3. **Copy the project to the server** (from your machine):
   ```bash
   rsync -av --exclude node_modules --exclude .next --exclude fine-tune --exclude .venv ./ user@SERVER_IP:speechmate/
   ```
4. **Create `backend/.env`** on the server from `backend/.env.example`:
   - your Groq and Gemini keys;
   - a new secret from `python3 -c "import secrets; print(secrets.token_hex(32))"`;
   - `TTS_BASE_URL=http://kokoro:8880/v1`.

   Never copy `.env` into Git.
5. **Change the database password.** It is hard-coded in `docker-compose.yml` (`speechmate_password`): change it in both `POSTGRES_PASSWORD` and `DATABASE_URL`. With the production override, Postgres can't be reached from outside, but use a real password anyway.

## 2. A domain for the API

HTTPS needs a domain name pointing at the server. Caddy then gets and renews the certificate by itself.

| Choice | How | Trade-off |
|---|---|---|
| **Your own domain** (recommended; free `.me` with the GitHub Student Pack via Namecheap) | DNS `A` record: `api` → server IP. Optionally add the frontend on Vercel as `app.<domain>` | `app.` and `api.` are the *same site*, so the sign-in cookie works in every browser, Safari included. Set `COOKIE_SAMESITE=lax` |
| **No domain:** `SERVER-IP.sslip.io` (for example `203-0-113-5.sslip.io`) | Nothing to set up | Vercel and the API are *different sites*. The sign-in cookie needs `SameSite=None`, and Safari (and browsers that block third-party cookies) drop it: users are signed out when their 30-minute access token expires |

## 3. Start the backend

On the server:

```bash
cd speechmate
export API_DOMAIN=api.example.com                    # or 203-0-113-5.sslip.io
export FRONTEND_ORIGIN=https://speechmate.vercel.app # your Vercel URL (or https://app.example.com)
export COOKIE_SAMESITE=lax                           # only with your own domain; leave unset otherwise
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile tts up -d --build db backend kokoro caddy
```

`docker-compose.prod.yml` does four things:
- it exposes only Caddy (80 and 443);
- it turns off the demo accounts;
- it sets the cookie to HTTPS-only;
- it allows only your frontend's origin (CORS).

Migrations run automatically when the backend starts.

**Check:** `curl https://$API_DOMAIN/health` should answer.

**To update later:** rsync again, then run the same `up -d --build` command.

## 4. The frontend on Vercel

1. **Push the code.** Vercel deploys from GitHub, so the code has to be on GitHub first.
2. **Import the project.** At vercel.com/new, import the repo:
   - **Root Directory:** `frontend`;
   - **Framework:** Next.js (detected; pnpm comes from `packageManager`).
3. **Set the environment variables** (Production):

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://<API_DOMAIN>/api` |
   | `NEXT_PUBLIC_SHOW_DEMO_LOGIN` | `false` (the demo accounts don't exist in production) |

4. **Deploy.** Every push to the main branch then redeploys automatically.

   `NEXT_PUBLIC_*` values are built into the bundle, so after changing one, use **Redeploy**.
5. **Optional custom domain.** Under Settings → Domains, add `app.<domain>` (a `CNAME` to `cname.vercel-dns.com`), then:
   - set `FRONTEND_ORIGIN=https://app.<domain>` on the server;
   - restart the backend.

**Check:** open the site, register, then do a short conversation session. The results should appear in about a minute.

`.github/workflows/deploy-vercel.yml` is an optional manual pipeline: Supabase migrations, then Vercel. It isn't needed with the Git integration above and a server-side database.

## 5. Before inviting participants

- [ ] `SEED_DEMO_DATA=false` (the production override sets it).
- [ ] A new `SECRET_KEY` and database password.
- [ ] Back up the database:
  ```bash
  docker compose exec db pg_dump -U speechmate speechmate_db > backup-$(date +%F).sql
  ```
  A daily cron job is enough.
- [ ] Watch Groq and Gemini usage (`details.usage` on each session). A short conversation session costs about US$0.001.
- [ ] Check that the privacy page and consent gate match the consent form (`fine-tune/docs/CONSENT_FORM.md`).

---

## Option B: everything on Vercel (not recommended)

Running the backend as a Vercel Python function would need:
- **Analysis:** the analysis jobs would move into requests (a 300 s cap).
- **ffmpeg:** it would come from `imageio-ffmpeg`.
- **Slides:** .pptx would be dropped (PDF only, through PyMuPDF).
- **Storage:** files would go to Vercel Blob.
- **Partner voice:** Kokoro would run only in the browser (`kokoro-js`, already used once loaded).
- **Analysis models:** all of them would be dropped, so pronunciation, eye contact, posture and emotion would report "unavailable".
- **Database:** Postgres would run on Supabase, using the session pooler on port 5432 with `postgresql+asyncpg://`, not the 6543 transaction pooler.

The manual workflow already has its jobs, and the backend job stays switched off until `DEPLOY_BACKEND=true`.
