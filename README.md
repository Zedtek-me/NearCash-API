# NearCash API

> A geolocation-driven cash and FX liquidity marketplace for Africa — connecting clients who need cash with nearby verified vendors in real time.

<!-- BADGES — you'll add these yourself (see notes below) -->
![CI](https://github.com/Zedtek-me/NearCash-API/actions/workflows/<your-workflow-file>.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Live App:** [nearcash.cadencepay.us](https://nearcash.cadencepay.us)

---

## The Problem

In Nigeria and across Africa, physical cash remains essential for everyday commerce — yet access is uneven. POS agents hold liquidity that clients nearby can't find, and clients hold cash that FX vendors nearby need. There's no efficient marketplace connecting them in real time.

NearCash solves this by turning proximity into a transaction — matching demand to supply within a configurable radius, with live tracking and real-time coordination via WebSockets.

---

## How It Works

1. A client requests cash (or FX) and their location is captured.
2. The system queries nearby vendors using PostGIS, ranked by distance.
3. The nearest available vendor receives a real-time transaction opportunity via WebSocket and has **30 seconds to accept**.
4. If no response, the system expands the search radius (3km → 5km → 15km) or broadcasts to multiple vendors.
5. Once accepted, both parties track each other live. The transaction is completed and confirmed on-chain in the app.

---

## Architecture

Client / Vendor (Browser/Mobile)
│
▼
Django (GraphQL API)          ← Graphene, JWT Auth
│
┌────┴────────────────────┐
│                         │
Django Channels           Celery Workers
(WebSocket Server)        (Background Tasks)
│                         │
Redis (Channel Layer)    RabbitMQ (Message Broker)
│
PostgreSQL + PostGIS     ← Geospatial queries



> **Note:** Full architecture diagram coming soon.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | Django 4.x + Graphene (GraphQL) |
| Real-time | Django Channels + WebSockets |
| Database | PostgreSQL + PostGIS |
| Background Tasks | Celery + RabbitMQ |
| Auth | JWT (JSON Web Tokens) |
| Maps | Google Maps API + Geoapify |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions → Contabo VPS |

---

## Key Features

**Proximity Matching**
PostGIS-powered vendor discovery with automatic radius expansion (3km → 5km → 15km fallback) when no vendors are available in the nearest range.

**Real-time Transaction Flow**
WebSocket-driven event system. Vendors receive opportunity notifications instantly and have a 30-second response window. Clients can wait, trigger an auto-broadcast to all nearby vendors, or cancel.

**Live Location Tracking**
During an active transaction, both client and vendor share live location updates via WebSocket for coordination.

**Liquidity Management**
Vendors declare available funds and configure alert thresholds. Email and push notifications fire automatically when liquidity drops below threshold.

**KYC Onboarding**
Full identity verification collecting NIN and facial capture for both clients and vendors before any transaction is permitted.

**FX Support** *(in development)*
Platform is being extended to support peer-to-peer foreign exchange liquidity alongside naira cash transactions.

---

## Project Structure
NearCash-API/
├── apps/
│   ├── core/          # Shared models, base types, GraphQL schema
│   ├── users/         # Auth, KYC, profiles
│   ├── transactions/  # Transaction lifecycle, matching logic
│   └── notifications/ # WebSocket consumers, push notifications
├── background_tasks/  # Celery task definitions
├── dtos/              # Data transfer objects
├── interfaces/        # Abstract base classes
├── utils/             # Shared helpers
└── docker/            # Container configuration
---

## Getting Started

### Prerequisites
- Docker + Docker Compose
- Google Maps API key
- Geoapify API key

### Setup

```bash
git clone https://github.com/Zedtek-me/NearCash-API.git
cd NearCash-API
cp .env.example .env   # fill in your environment variables
docker compose -f nearcash-local-compose.yml up --build

GraphQL Playground
Once running, the API is available at:
http://localhost:8000/api/v1/graph/

WebSocket Endpoint
ws://localhost:8000/ws/notification/<user_id>/

Environment Variables
Variable	Description
SECRET_KEY	Django secret key
DATABASE_URL	PostgreSQL connection string
GOOGLE_MAPS_API_KEY	For geocoding and distance
GEOAPIFY_API_KEY	For geolocation enrichment
CELERY_BROKER_URL	RabbitMQ connection string
REDIS_URL	Django Channels layer
JWT_SECRET	Token signing key

License
MIT © Zechariah Adebayo


---

**What you need to do yourself:**

1. **CI badge** — replace `<your-workflow-file>` with the actual filename in `.github/workflows/`. Check what it's called and update that one line.

2. **Architecture diagram** — the ASCII version above is a placeholder. When you have time, make a proper diagram on [Excalidraw](https://excalidraw.com) (free, no login needed) and drop the image into the repo. Replace the ASCII block with it.

3. **Add MIT license** — go to your repo on GitHub → Add file → Create new file → name it `LICENSE` → GitHub will offer you a license template picker → choose MIT → commit. Done in 2 minutes.

4. **Add `.env.example`** — a copy of your `.env` file with all values blanked out. Helps anyone cloning understand what's needed. Don't commit the real `.env`.

5. **Screenshots** — one screenshot of the live app or GraphQL playground at the top would go a long way. Optional but high impact.
