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
- **P2**: SendGrid sender verification on `helpdesk@gomofos.com` for emails to actually deliver.
- **P2**: Add a "view leaderboard" affordance on game cards (currently the entire card is clickable but has no visual cue).


## Iteration 11: Backend Refactor — Monolith Split into Modular Routers (Feb 2026)
### Done
- **`server.py`: 3,575 → 91 lines.** The previous monolith was split into a thin entry point that wires together purpose-built modules. All endpoint paths, request/response shapes, and behaviour are byte-identical to before — pure structural refactor.
- **New `/app/backend/core.py`** (132 LOC) — single source of truth for: `app`, `api_router`, Mongo `db`/`client`, `logger`, JWT helpers (`hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `create_decline_token`), `get_current_user`, and ALL module-level constants (`WELCOME_BONUS`, `REFERRAL_BONUS`, `LATENCY_WARN_MS=100`, `LATENCY_HIGH_MS=200`, `DISPUTE_HOLD_THRESHOLD=0.66`, `DISPUTE_HOLD_MIN_MATCHES=3`, storage paths, `HIGHLIGHT_*`, `TWOFA_*`).
- **New `/app/backend/models.py`** (196 LOC) — every Pydantic request/response model (UserRegister/Login/Response, GameCreate/Response, TournamentCreate/Response, ChatMessage*, DepositRequest, ForgotPassword*, ResetPassword*, ProfileUpdate, PublicProfileResponse, ChallengeCreate, CompetitionCreate, CompetitionMatchLog, PrizeFeat/Create/Equip, AdminDisputeResolution, ReferralInvite, TwoFAChallenge).
- **New `/app/backend/services.py`** (495 LOC) — cross-domain helpers that more than one router needs: `init_storage`/`put_object`/`get_object`/`_ensure_local_dir` (storage), `build_public_profile`, `require_admin`, `cleanup_expired_tournaments`, `award_winner_and_close`, `compute_latency_advantage*`, `recompute_user_dispute_status`, `competition_to_dict`, `stats_for_user`, `check_feat_unlocked`, `prize_dict`, `SEED_PRIZES`, `twilio_client`, `send_whatsapp`, `start_admin_2fa`, `dispatch_tournament_reminder`, `reminder_scheduler_loop`. All depend ONLY on `core` — never on routers, so zero circular imports.
- **New `/app/backend/routers/` package** with 13 modules — auth, users, challenges, games, tournaments, competitions, chat, wallet, admin, prizes, highlights, referrals, misc. Each module imports `api_router` from `core` and registers its endpoints with `@api_router.get/post/...` decorators at import time. **83 routes total** across all routers.
- **`server.py` final shape**: imports core+services+all 13 routers (so routes auto-register via side effect), then `app.include_router(api_router)`, mounts CORS, and keeps the existing `@app.on_event("startup"/"shutdown")` hooks (index creation, admin seed, storage init, reminder loop kickoff).

### Bug found & fixed during regression
- **`routers/auth.py` brute-force lockout was returning HTTP 500 instead of 429** — Mongo persists timezone-naive datetime, but `locked_until` was written tz-aware and read back tz-naive, causing `TypeError: can't compare offset-naive and offset-aware datetimes`. Pre-existing bug exposed by iter11's broader test pass. **Fix**: normalize `lockout_until` to UTC-aware before comparison (`routers/auth.py` L108-112).

### Verified
- **Backend pytest 38/38 PASS** (1 pre-existing skip) across 3 suites: iter9 decline+refund (12/12), iter10 health+game-leaderboard (5/5), new iter11 broad regression (21/21 covering boot/auth/profile/games/tournaments/challenges/wallet/prizes/admin/referrals/competitions/highlights).
- **Frontend Playwright smoke PASS** — login as davidjovanic@yahoo.com.au; navigated /dashboard, /games, /tournaments, /competitions, /prizes, /leaderboard, /players, /profile, /games/{id}/leaderboard. Every page rendered with TopNav, 0 console errors. Game-card click → GameLeaderboard worked.
- **Manual smoke** — POST /api/auth/login → cookies set; GET /api/auth/me → 200; GET /api/games → 100 games; GET /api/health/time → 200; GET /api/games/{id}/leaderboard → 200; GET /api/leaderboard → 200; GET /api/countries → 200; GET /api/competitions → 200; GET /api/prizes → 200; GET /api/referrals/mine → 200.

### Files added/changed
- `/app/backend/core.py` (NEW)
- `/app/backend/models.py` (NEW)
- `/app/backend/services.py` (NEW)
- `/app/backend/routers/__init__.py` (NEW)
- `/app/backend/routers/auth.py` (NEW)
- `/app/backend/routers/users.py` (NEW)
- `/app/backend/routers/challenges.py` (NEW)
- `/app/backend/routers/games.py` (NEW)
- `/app/backend/routers/tournaments.py` (NEW)
- `/app/backend/routers/competitions.py` (NEW)
- `/app/backend/routers/chat.py` (NEW)
- `/app/backend/routers/wallet.py` (NEW)
- `/app/backend/routers/admin.py` (NEW)
- `/app/backend/routers/prizes.py` (NEW)
- `/app/backend/routers/highlights.py` (NEW)
- `/app/backend/routers/referrals.py` (NEW)
- `/app/backend/routers/misc.py` (NEW)
- `/app/backend/server.py` (REWRITTEN — 3,575 → 91 lines, entry-point only)
- `/app/backend/tests/test_iter11_refactor_regression.py` (NEW, 21 cases)
- `/app/backend/tests/test_iter8_latency_email.py` (updated test_latency_constants_exist to read `core.py` instead of `server.py`)

### Backlog (still open)
- **P2**: SendGrid sender verification on `helpdesk@gomofos.com` for emails to actually deliver.
- **P2**: Add a "view leaderboard" affordance on game cards (currently the entire card is clickable but has no visual cue).


## Iteration 12: Advertising Platform + Logo Refresh + Admin Latency Graph (Feb 2026)
### Done
- **NEW LOGO** (Logo 3rd.png — red shooter + blue racer crest). `/app/frontend/public/gomofos-logo.png` replaced; centralized `<Logo />` component flows the new image to every page. Favicon + `<title>` updated to `GoMofos — Esports Staking`.

- **ADVERTISING — admin-managed sidebar ads**:
  - **Backend** (`/app/backend/routers/ads.py`, NEW, 11 endpoints): full CRUD on `advertisements` collection (name, image_url, click_url, active, impression_count, click_count, created_by/_username). Public `GET /api/ads/rotation` returns active ads; client-side `<AdRail />` picks 3 and rotates each slot every ~5 sec. `POST /api/ads/{id}/impression` records views. `GET /api/ads/{id}/click` does a 302 redirect + bumps counter (no auth so analytics survive logout). Image upload at `POST /api/admin/ads/upload-image` (4 MB cap, PNG/JPG/WEBP/GIF). Search by name or URL via `?q=`.
  - **Permission model**: site `admin` always has access. Site admins promote other users via `POST /api/admin/ad-managers { user_id }` which sets `can_manage_ads=True`. `GET /api/admin/ad-managers` lists admins + ad-managers. `DELETE /api/admin/ad-managers/{id}` revokes. Ad-managers can do `/admin/ads` CRUD but CANNOT touch disputes, latency, or user admin (escalation boundary verified by automated test).
  - **UserResponse.can_manage_ads**: bool, default False — exposed on `/auth/me`, `/login`, `/register`, `/2fa/verify` so the frontend can gate the ADS tab.
  - **Frontend**:
    - `/app/frontend/src/components/AdRail.js` — fixed right-rail (xl+ viewports), 3 stacked slots, staggered ~5 sec rotation, impression-once-per-session.
    - `/app/frontend/src/components/ProtectedRoute.js` — renders AdRail alongside protected children (one mount, no per-page changes).
    - `/app/frontend/src/pages/AdminAds.js` — searchable list, create form with inline image upload, active toggle, delete.
    - `/app/frontend/src/pages/AdminAdManagers.js` — search-by-username, grant/revoke access.
    - `/app/frontend/src/components/TopNav.js` — DISPUTES + LATENCY tabs for admin, ADS tab for admin OR ad-manager.

- **ADMIN LATENCY GRAPH** (admin-only):
  - **Backend** (`/app/backend/routers/admin_latency.py`, NEW):
    - `GET /admin/latency/tournament/{id}` → per-tournament line-chart payload: `{series:[{user_id,username,points:[{t,ms}],avg_ms,max_ms,status}], thresholds:{warn:100, high:200}}`.
    - `GET /admin/latency/competition/{id}?match_id=...` → same shape for h2h matches.
    - `GET /admin/latency/dashboard?q=` → searchable list of every match with samples, disputed ones first.
    - `POST /admin/latency/tournament/{id}/extend-retention?days=N` (1..730) → bulk-updates `tournament_latency.expires_at` for that match + sets `tournaments.latency_retention_extended_until`. Same for competition.
  - **TTL retention**: every latency sample now has `expires_at = now + 30 days`. Mongo TTL index auto-deletes old rows. Startup backfills `expires_at` on pre-iter12 samples so the policy applies retroactively.
  - **Auto-ping every 60 sec**: new `useLatencyPing` hook in `/app/frontend/src/hooks/useLatencyPing.js` runs an HTTP RTT ping to `/api/health/time` every 60 sec while a tournament is `in_progress` OR a competition match is `pending_confirmation`. Wired into `TournamentDetails.js` + `CompetitionDetails.js`. Existing WebSocket-based ping continues to coexist for sub-second sampling during live play.
  - **Frontend**:
    - `/app/frontend/src/components/LatencyGraph.js` — recharts `<LineChart />` with one line per player + dashed reference lines at warn (100ms) + high (200ms). Per-player summary chips show avg / peak / status.
    - `/app/frontend/src/pages/AdminLatency.js` — left list of matches, right pane shows graph. Deep-link via `?kind=tournament&id=...&match_id=...`. EXTEND RETENTION button prompts for days.
    - `/app/frontend/src/pages/AdminDisputes.js` — each dispute card now shows "VIEW FULL SPIKE/DIP GRAPH →" link that deep-links to the right `/admin/latency` URL.

### Verified
- **Backend pytest 28/28 PASS** in `/app/backend/tests/test_iter12_ads_latency.py` + iter11 baseline still 38/38.
- **Frontend Playwright PASS** — admin sees DISPUTES/LATENCY/ADS tabs; regular user does not; granting `can_manage_ads` makes ADS appear (only); /admin/ads, /admin/ad-managers, /admin/latency all render for admin and redirect non-admin to /dashboard; AdRail renders 3 stacked ad-slots when ads exist + null when empty (no error); /admin/disputes deep-link works.
- **Manual smoke screenshots** confirmed AdminLatency already discovered an existing disputed "Call of Duty: MW3" tournament with 6 latency samples and rendered the disputed pill in red — feature is wired correctly to real data.

### Files added/changed
- `/app/backend/routers/ads.py` (NEW)
- `/app/backend/routers/admin_latency.py` (NEW)
- `/app/backend/routers/tournaments.py` (latency samples now persist `expires_at`)
- `/app/backend/routers/competitions.py` (same)
- `/app/backend/routers/auth.py` (UserResponse populates `can_manage_ads`)
- `/app/backend/models.py` (added `can_manage_ads: bool` to UserResponse)
- `/app/backend/server.py` (registers 2 new routers, creates TTL + ads indexes, backfills `expires_at`)
- `/app/frontend/src/components/AdRail.js` (NEW)
- `/app/frontend/src/components/LatencyGraph.js` (NEW)
- `/app/frontend/src/components/ProtectedRoute.js` (mounts AdRail)
- `/app/frontend/src/components/TopNav.js` (admin/ad-manager tabs)
- `/app/frontend/src/hooks/useLatencyPing.js` (NEW)
- `/app/frontend/src/pages/AdminAds.js` (NEW)
- `/app/frontend/src/pages/AdminAdManagers.js` (NEW)
- `/app/frontend/src/pages/AdminLatency.js` (NEW)
- `/app/frontend/src/pages/AdminDisputes.js` (deep-link to latency graph)
- `/app/frontend/src/pages/TournamentDetails.js` + `CompetitionDetails.js` (auto-ping hook)
- `/app/frontend/src/App.js` (3 new routes)
- `/app/frontend/public/gomofos-logo.png` (REPLACED — new crest)
- `/app/frontend/public/index.html` (favicon + title)
- `/app/backend/tests/test_iter12_ads_latency.py` (NEW, 28 cases)

### Backlog (still open)
- **P2**: SendGrid sender verification on `helpdesk@gomofos.com` for emails to actually deliver.
- **P2**: Add a "view leaderboard" affordance on game cards (currently the entire card is clickable but has no visual cue).


## Iteration 13: Ad Analytics + Logo Cache Fix + AdRail Redesign + Site Footer (Feb 2026)
### Done
- **🎯 AD ANALYTICS DASHBOARD** (`/admin/ads/analytics`):
  - Backend: `GET /api/admin/ads/analytics?days=N` (1..365, default 7) returns `{window_days, totals, rows[]}` per ad with window + lifetime impressions/clicks/CTR. `GET /api/admin/ads/analytics/export?days=N` returns invoice-ready CSV with attachment Content-Disposition. Reuses `ads_analytics()` so CSV and JSON can never diverge. Both endpoints gated by `_require_ad_admin` (admin OR ad-manager).
  - Event logging: new `ad_events` collection (kind: impression/click, ad_id, timestamp, expires_at). TTL 90 days + compound index `(ad_id, timestamp DESC)`. Impression on **inactive** ad is silently dropped (no counter bump, no event).
  - Frontend: KPI cards (total impressions/clicks/CTR/active), 1D/7D/30D window selector (refetches data), CSV export button (opens browser download via cookie session), per-ad table sorted by window impressions.

- **🎨 LOGO CACHE FIX**:
  - Copied logo to a **new filename** (`/gomofos-crest.png`) + appended `?v=3` query string in `<Logo />`. Both invalidate browser + CDN edge caches. Live server will fetch fresh on next visit.
  - Updated favicon + apple-touch-icon in `index.html` to the new path.
  - The old `/gomofos-logo.png` stays in place to avoid breaking any external email references.

- **📐 AD RAIL REDESIGN** (`/app/frontend/src/components/AdRail.js` — REWRITTEN):
  - **Desktop (xl+)**: `xl:absolute xl:right-6 xl:top-24 xl:w-[170px]` — scrolls 1:1 with the page (parent in ProtectedRoute is `position: relative`), no longer fixed. Verified test: 204px page scroll = 204px rail Y delta.
  - **Mobile/tablet**: inline `w-full max-w-md mx-auto px-6 py-8 flex flex-col gap-12` — renders at the bottom of every page (was hidden before).
  - **Ad dimensions**: image area now `aspectRatio: '10 / 7'` (~30% shorter than the previous square).
  - **Vertical spacing**: `gap-12` (3rem) between slots — more breathing room.
  - **Content-overlap fix**: `ProtectedRoute` wraps children in `xl:pr-[200px]` so page text reserves the right column. No more text-under-ads.

- **🦶 SITE FOOTER**:
  - New `<Footer />` with the new logo + 6 links: ABOUT US, CAREERS, SUPPORT, CONTACT, TERMS OF USE, PRIVACY POLICY (each `data-testid`'d for tests).
  - Rendered on every protected page (via `ProtectedRoute`) AND on the public `LandingPage`. Placeholder pages at `/about, /careers, /support, /contact, /terms, /privacy` via a shared `<StaticPage />` template — public routes (no auth) for now.

### Verified
- **Backend pytest 79/79 PASS** — 13/13 new iter13 (`test_iter13_ad_analytics.py`: analytics JSON, CSV export, ad_events logging incl. 90-day TTL, inactive-ad guard, ad-manager access) + iter12 28/28 + iter11 21/21 + iter10 5/5 + iter9 12/12. Zero regressions.
- **Frontend Playwright PASS** — logo cache-bust (200 OK on `/gomofos-crest.png?v=3`); Footer + 6 testid'd links on every route; static pages render with testids; AdRail desktop scroll-with-page verified pixel-perfect; AdRail mobile inline; analytics page KPI + window selector + CSV export; non-admin/non-ad-manager redirected; no content-under-ads overlap.

### Files added/changed
- `/app/frontend/public/gomofos-crest.png` (NEW physical file)
- `/app/frontend/src/components/Logo.js` (new filename + `?v=3` cache-bust)
- `/app/frontend/src/components/AdRail.js` (REWRITTEN)
- `/app/frontend/src/components/ProtectedRoute.js` (relative wrapper + Footer)
- `/app/frontend/src/components/Footer.js` (NEW)
- `/app/frontend/src/components/StaticPage.js` (NEW shared template)
- `/app/frontend/src/pages/About.js, Careers.js, Support.js, Contact.js, Terms.js, Privacy.js` (NEW)
- `/app/frontend/src/pages/AdminAdAnalytics.js` (NEW)
- `/app/frontend/src/pages/AdminAds.js` (VIEW ANALYTICS button)
- `/app/frontend/src/pages/LandingPage.js` (mounts Footer)
- `/app/frontend/src/App.js` (8 new routes)
- `/app/frontend/public/index.html` (favicon updated)
- `/app/backend/routers/ads.py` (ad_events logging on impression+click, analytics JSON + CSV endpoints)
- `/app/backend/server.py` (TTL + compound index on ad_events)
- `/app/backend/tests/test_iter13_ad_analytics.py` (NEW, 13 tests)

### Backlog (still open)
- **P2**: SendGrid sender verification on `helpdesk@gomofos.com` for emails to actually deliver.
- **P2**: Add a "view leaderboard" affordance on game cards.
- **P3** (nice-to-have from iter13 testing): Return non-200 when `/api/ads/{id}/impression` is fired against an inactive ad so clients can detect a stale rotation cache.
- **P3** (nice-to-have): Stream CSV in chunks if ad catalog ever exceeds 1000 ads.
- **P3** (a11y): Add `aria-label="analytics-window"` to the 1D/7D/30D selector group.

