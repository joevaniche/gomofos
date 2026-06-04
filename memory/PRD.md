# Esports Bet Platform - PRD

## Original Problem Statement
"I want to build a web server that allows people to organise online games like FIFA and NBA or Call of Duty and stake money on the outcome of the game"

## User Choices
- Payment: Stripe
- Game verification: Automated via game API integration (currently manual via creator selection; framework ready for API integrations)
- Money flow: Platform escrow - releases to winner
- Features: Browse/join, custom tournaments, live chat, leaderboards
- Game types: All games across all platforms (user-generated catalog)

## Architecture
- Backend: FastAPI + Motor (MongoDB async) + JWT auth + bcrypt + Stripe (emergentintegrations)
- Frontend: React + React Router + Axios + Tailwind + Shadcn/UI + Phosphor Icons
- Database: MongoDB
- Design: Dark mode "Tactical Performance Pro" aesthetic - sharp edges, no rounding, Chivo/IBM Plex Sans

## User Personas
- Casual Gamer: Wants to stake on friendly games (FIFA, NBA, COD)
- Competitive Player: Wants to organize tournaments and climb leaderboards
- Tournament Host: Creates and manages competitive tournaments

## Core Requirements (Static)
1. User registration/authentication with JWT
2. Wallet system with Stripe deposits
3. Game catalog (user can add games)
4. Tournament creation and management
5. Stake escrow handled by platform
6. Real-time-ish chat between participants
7. Leaderboard rankings
8. Tournament completion with automatic payout (95% to winner, 5% platform fee)

## Implementation Status (Feb 27, 2026)
### Done
- JWT auth with httpOnly cookies (register, login, logout, me, refresh, forgot-password, reset-password)
- Brute force protection (5 attempts = 15min lockout)
- Game catalog CRUD
- Tournament CRUD with stake validation
- Tournament participants management
- Stake escrow (deducted on create/join, paid to winner on complete)
- Chat (restricted to participants only)
- Stripe deposit flow with polling
- Leaderboard with win rates
- Beautiful dark-mode UI with custom design system

## Backlog
### P1
- Game API integration for automated result verification (currently manual via creator)
- WebSocket-based real-time chat (currently polling every 3s)
- Email integration for password reset (currently console log)
- Withdrawal flow (Stripe Connect)

### P2
- Tournament brackets visualization for >2 player tournaments
- Player profiles with avatars
- Match history and stats
- Spectator mode for ongoing tournaments
- Tournament invites and private tournaments

## Deployment Target (Updated)
- **Domain:** gomofos.com
- **Server IP:** 192.168.0.124 (private LAN - requires Cloudflare Tunnel or port forwarding for public access)
- **Deployment guide:** /app/DEPLOYMENT_GUIDE.md (3 deployment paths: LAN-only, Port Forwarding, Cloudflare Tunnel)

## Iteration 4: Player Matchmaking System (Feb 28, 2026)
### Done
- Player profiles with: bio, country (ISO-2), city, timezone (IANA), platforms (PS5/PS4/Xbox/PC/Switch/Mobile), gamertags (PSN/Xbox/Steam/Epic/Battle.net/Nintendo/Riot/Activision), preferred games, stake range (min/max)
- last_active_at auto-updated on every authed request → enables "Online now" status (<10 min threshold)
- GET /api/users/search with filters: q (text), game_id, country, platform, stake_min/max overlap, min_wins, online_only
- GET /api/countries (36), GET /api/platforms-list (7)
- Direct 1v1 challenge: POST /api/challenges → creates private invite-only tournament with is_private=true and invited_user_ids
- GET /api/challenges/incoming → shows pending challenges on dashboard
- Private tournaments hidden from non-invitee public listing
- Frontend: ProfileEdit, ProfileView, PlayerSearch pages + ChallengeModal component
- Wallet balance hidden from other users' profile views
- Tested: 64/64 backend tests passing

### Backlog (deferred)
- SendGrid email integration (paused — needs API key)
- 48h auto-timeout dispute escalation emails
- Public dispute history page
- Latency threshold warnings (100ms warn, 200ms+ dispute weight)
- Multi-admin promotion UI + .env ADMIN_EMAILS list


## Iteration 6: Custom Branding Rollout (June 4, 2026)
### Done
- Replaced default branding with user-supplied Gomofos assets: `/public/gomofos-logo.png`, `/public/gomofos-bg.mp4`, `/public/gomofos-bg-poster.jpg`
- Global `<BackgroundVideo />` mounted once at App.js level (z-index -10, 35% opacity, dark gradient overlay) — exactly one `<video>` element per route, verified across 9 routes
- `<Logo />` component (link to `/`, `data-testid="site-logo"`) added to every page including auth pages (Login/Register now show `<Logo size="large" />` centered above the form)
- Landing page hero: "GAME ON MOFOS!" tagline + staggered reveal of `STAKE.` / `COMPETE.` / `DOMINATE.` words using refs + setTimeout (delays 100/600/1600/2600/3400ms) with 0.8s opacity+transform CSS transition
- Description paragraph + "START COMPETING" CTA fade in after the headline words
- All page backgrounds set to semi-transparent so the video shows through (`body { background: transparent !important }`)

### Verified
- Frontend testing agent passed 10/10 assertions: logo present, exactly 1 video per page, hero animation reaches opacity 1 within 5s, registration → /dashboard with 1000 CR balance, admin login + traversal of /dashboard, /games, /wallet, /leaderboard, /players, /profile, /create-tournament

### Known Non-Blocking Console Warning
- `/create-tournament` emits a React hydration warning `<span> cannot be a child of <option>` — likely from a dev-time instrumentation wrapper around the game name. Does not affect functionality. Defer fix.

## Backlog (after branding)
### P1
- SendGrid email notifications (dispute alerts, match invites) — needs API key from user
- Auto-timeout disputes after 48h with admin escalation email
- Latency threshold enforcement (>100ms warn, >200ms block/dispute risk)

### P2
- Public dispute history page for trust
- Auto-fill missing game covers via IGDB API
- Refactor monolithic `/app/backend/server.py` (~1,500 lines) into modular routes

## Iteration 7: Highlight Reels + Flex on X (June 4, 2026)
### Done
- **Highlight Reels** — backend `db.highlight_reels` collection + endpoints:
  - `POST /api/highlights` (multipart upload, 60s / 50 MB cap, MP4/MOV/WebM, public by default, server-side validation + Emergent Object Storage persist)
  - `GET /api/highlights/user/{user_id}` (public list, newest first)
  - `GET /api/highlights/{reel_id}` (metadata + view-count increment)
  - `GET /api/highlights/{reel_id}/stream` (video bytes, public)
  - `DELETE /api/highlights/{reel_id}` (owner only)
  - Indexes: `(user_id, created_at desc)` + unique `id`
- **`<HighlightReels />` component** on `ProfileView`: grid of reels with thumbnail + duration badge + view count; owner sees "UPLOAD CLIP" button; click-to-play modal; client-side duration/size validation before upload; progress bar
- **Tournament Share Card** — `GET /api/share/tournament/{tournament_id}` returns standalone HTML with full Open Graph + Twitter Card meta tags so X embeds a rich preview. Optional `?reel={reel_id}` adds `og:video` + `twitter:card=player` + `twitter:player:stream` for video embedding directly in tweet timelines
- **"FLEX ON X" button** on TournamentDetails — only visible when `tournament.winner_id === user.id` and `status==='completed'`. Opens a modal where the winner picks which of their highlight reels to attach (or none), with auto-pick by matching game. Renders the share text (`Just took down @opponent for 200 CR on @gomofos playing FIFA! 🏆`) and the share URL; "POST TO X" opens Twitter web intent in a new window; "COPY" puts text + URL on clipboard

### Verified
- Backend pytest 12/12 PASS — including 51 MB oversize rejection, image/png rejection, empty-title rejection, owner-only DELETE (403/200), OG meta tags rendered correctly, OG video meta on `?reel=` param
- Frontend Playwright 9/9 PASS — own profile shows upload button, other profile doesn't; upload modal opens; uploaded reel shows in grid; winner sees "FLEX ON X"; share modal exposes reel picker + post/copy; clipboard copies expected text + URL
- Landing branding regression OK

### Notes / Future Polish
- POST `/api/highlights` buffers full file in memory before size check (fine at 50 MB; if cap increases later, switch to streaming with early abort)
- `/stream` endpoint returns full body in one response (no HTTP Range support yet); first-frame for 50 MB clips may take a beat. Future: `StreamingResponse` + Range header
- View count returns post-increment value on the same GET — first GET of a new reel shows "1 view" immediately

### Files touched
- `/app/backend/server.py` (+~220 lines for highlight reels + share card; index registration; HTMLResponse + Form import)
- `/app/frontend/src/components/HighlightReels.js` (NEW)
- `/app/frontend/src/pages/ProfileView.js` (load games, render `<HighlightReels />` block)
- `/app/frontend/src/pages/TournamentDetails.js` (winner gets "FLEX ON X" button + `<ShareOnXModal />`)
- `/app/backend/tests/test_highlights_share.py` (NEW pytest, 12 cases)

