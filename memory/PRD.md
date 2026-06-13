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


## Iteration 8: SendGrid Emails + Latency Tie-Breaker (June 4, 2026)
### Done
- **SendGrid integration** (`backend/email_service.py`) — async, fire-and-forget, never blocks API responses and swallows SendGrid errors so the request flow stays green even when sender is unverified
  - Triggers wired: `POST /api/challenges` → match-invite email to challenged player; submit-result dispute branch → dispute-alert email to every non-opener participant
  - Admin escalation NOT wired (user deferred this) — backlog item
  - Branded HTML template + plain-text fallback for both email types (FIFA-stadium black/red Chivo styling matching the app)
- **Latency thresholds** (matches backend `LATENCY_WARN_MS=100`, `LATENCY_HIGH_MS=200`):
  - Frontend in-match banners: <100ms = no banner; 100–199ms = yellow `data-testid="latency-banner-warn"` ("connection unstable, may weigh against you"); ≥200ms = red `data-testid="latency-banner-high"` ("HIGH LATENCY, dispute tie-break goes against you")
  - **Policy: ALLOW the match but flag** — no blocking; high-latency player simply loses the tie-breaker
- **Latency advantage tie-breaker** (`_compute_latency_advantage` in server.py):
  - Eligibility: ≥3 samples per player
  - Logic: if any player has peak ≥200ms (`status=high`) AND another doesn't, the non-high player wins advantage; otherwise lower avg wins
  - New endpoint `GET /api/tournaments/{id}/latency-advantage` (participant or admin only)
  - Dispute creation now embeds `latency_advantage` directly on the tournament document so the frontend can render the tie-breaker callout inside the dispute banner
- **Latency log** — already had `tournament_latency` collection; added `(tournament_id, user_id, timestamp)` compound index for fast aggregation
- **Frontend dispute banner** now shows `latency-advantage-callout` with the advantaged player's name + per-player breakdown (avg ms, peak ms, sample count, color-coded status)
- **Tournament detail GET** now exposes `latency_advantage` (null pre-dispute)

### Verified
- Backend pytest 9/9 PASS (`test_iter8_latency_email.py`)
- Frontend Playwright 4/4 PASS (forced banner-high, forced banner-warn, dispute callout with seeded asymmetric latency, landing regression)
- SendGrid 403 from unverified sender confirmed swallowed gracefully (exit code 0)

### ACTION REQUIRED FROM USER
- **Verify `helpdesk@gomofos.com` in SendGrid Sender Auth** — until this is done, emails return 403 and are silently dropped (no user-facing impact, but no emails delivered either). Go to https://app.sendgrid.com/settings/sender_auth/senders or authenticate the gomofos.com domain. Once verified, emails start flowing with zero code change.

### Files touched
- `/app/backend/email_service.py` (NEW)
- `/app/backend/server.py` (+~140 lines: email service imports, fire emails in challenges + submit-result dispute, latency advantage helper + endpoint, latency_advantage in tournament detail, tournament_latency index)
- `/app/backend/.env` (+`SENDGRID_API_KEY`, `SENDER_EMAIL`)
- `/app/backend/requirements.txt` (+`sendgrid==6.12.5`)
- `/app/frontend/src/pages/TournamentDetails.js` (latency thresholds, in-match banners, dispute latency-advantage callout)
- `/app/backend/tests/test_iter8_latency_email.py` (NEW, 9 cases)


## Iteration 9: One-click Decline & Refund (June 4, 2026)
### Done
- **`create_decline_token`** — signed JWT (HS256, 7-day expiry) embedding `{tid, uid, type:'decline_challenge'}` so the email link is self-authenticated without requiring login.
- **`GET /api/challenges/decline?token=...`** (mounted on `app`, not `api_router`, with literal `/api/` prefix) — public HTML page that:
  - Validates the token (handles expired, invalid, wrong-uid)
  - Refunds every participant who had paid into the tournament (in practice just the challenger, since the invitee never commits a stake at invite time)
  - Flips tournament `status: 'declined'`, stamps `declined_by` + `declined_at` + `refunded_user_ids`
  - Is **idempotent** — second click on the same token shows "Already declined" without double-refunding
  - Renders a branded GoMofos confirmation page with the actual refunded amount
- **`POST /api/challenges/{id}/decline`** (authenticated) — in-app version for the Dashboard button, enforces `user.id ∈ invited_user_ids` or 403
- **Email template update** — `send_match_invite` now renders a **dual CTA block**: red `ACCEPT CHALLENGE` + outlined `DECLINE & REFUND`. Plain-text email also includes both URLs. Footer copy updated to clarify "Declining refunds X CR to the challenger's wallet — you haven't paid anything yet."
- **Dashboard challenge cards** — each `incoming-challenges` card now has `accept-challenge-{id}` (red, navigates) + `decline-challenge-{id}` (outlined, window.confirm → POST + toast + remove card + refresh wallet via `checkAuth`)

### Verified
- Backend pytest 12/12 PASS — valid token decline + refund, idempotency, invalid/expired/wrong-uid tokens, started-match no-refund, authenticated 403 for non-invitee, 404 for missing tournament, `/challenges/incoming` filter excludes declined
- Frontend Playwright 5/5 PASS — both buttons rendered, confirm-cancel keeps card, confirm-accept fires POST + toast + state update, ACCEPT navigation works
- No regressions on iterations 6–8 (branding, highlight reels, X share, SendGrid, latency tie-breaker)

### Files touched
- `/app/backend/server.py` (+~110 lines: `create_decline_token`, `_decline_challenge_core`, HTML endpoint, authenticated POST decline endpoint, refund count-based message)
- `/app/backend/email_service.py` (dual CTA block + plain-text dual URL + accurate copy on refund target)
- `/app/frontend/src/pages/Dashboard.js` (Accept/Decline buttons on each incoming-challenge card, window.confirm + decline POST + state + wallet refresh)
- `/app/backend/tests/test_iter9_decline_refund.py` (NEW, 12 cases)


## Iteration 10: Server Timezone Health, Per-Game Leaderboard, Dashboard Tournaments Table (Feb 2026)
### Done
- **Backend `GET /api/health/time`** — public endpoint that returns `server_time_utc`, `server_time_local`, `server_timezone`, `tz_offset_hours`. Useful for debugging tournament time display mismatches on the live server.
- **Backend `GET /api/games/{game_id}/leaderboard`** — per-game leaderboard. Counts every completed tournament + confirmed h2h match on this specific game; ranks by `(wins desc, net_credits desc)`. Returns `game_id`, `game_name`, `platform`, `category`, `rows[]` with `user_id`, `username`, `wins`, `losses`, `total_matches`, `net_credits`, `equipped_thumbs` (so leaderboard shows bling). 404 on missing or malformed id.
- **`Dashboard.js` — "MY ACTIVE TOURNAMENTS" table** — refactored from card grid to a single table matching the Tournaments tab. Columns: Opponent, Game, Platform, Date & Time, Stake, Status. Opponent label handles 1v1 vs >2-player cases; status mapping covers open/in_progress/pending_confirmation/disputed with colour codes; row click navigates to tournament detail.
- **`GameLeaderboard.js`** — new page at `/games/:id/leaderboard`, rendered with `<TopNav />`, "All games" back link, category/platform tag, Trophy icon, and either an empty state or the ranked table with current-user highlight (`bg-[#FF3B30]/10` + "(YOU)" badge).
- **`BrowseGames.js`** — game cards now navigate to `/games/{id}/leaderboard` on click.

### Verified
- Backend pytest 5/5 PASS (`test_iter10_health_and_game_leaderboard.py`) — health endpoint shape, leaderboard 200 happy path, 404 for malformed + non-existent id, row schema. 1 sort-order assertion SKIPPED because DB has no game with ≥2 leaderboard rows yet.
- Frontend Playwright PASS — login as davidjovanic@yahoo.com.au, dashboard renders `no-tournaments` empty state with `TopNav`, /games shows 101 cards with `TopNav`, clicking the first card navigates to `/games/{id}/leaderboard`, GameLeaderboard renders back link + heading + empty state + TopNav, back link returns to /games.
- No regressions on iterations 6–9.

### Files touched
- `/app/backend/server.py` (added /api/health/time and /api/games/{game_id}/leaderboard near line 3420)
- `/app/frontend/src/pages/Dashboard.js` (table refactor for MY ACTIVE TOURNAMENTS)
- `/app/frontend/src/pages/GameLeaderboard.js` (NEW)
- `/app/frontend/src/pages/BrowseGames.js` (card click → leaderboard route)
- `/app/frontend/src/App.js` (route `/games/:id/leaderboard`)
- `/app/backend/tests/test_iter10_health_and_game_leaderboard.py` (NEW)

### Pending User Actions
- **SendGrid Click Tracking** — user still needs to disable Click Tracking in SendGrid dashboard to fix the `url1461.gomofos.com` SSL cert error on referral email links. No code change required.

### Backlog (still open)
- **P1**: Refactor `server.py` (3,575 lines) into modular APIRouters (auth, tournaments, competitions, admin, prizes, referrals, highlights). Becoming a context-window liability.
- **P2**: SendGrid sender verification on `helpdesk@gomofos.com` for emails to actually deliver.
- **P2**: Add a "view leaderboard" affordance on game cards (currently the entire card is clickable but has no visual cue).
