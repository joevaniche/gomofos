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
