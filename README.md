# NearCash API 💸

> **A geolocation-driven liquidity marketplace for Africa** — connecting clients who need cash or foreign exchange with nearby verified vendors, in real time.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![GraphQL](https://img.shields.io/badge/GraphQL-API-E10098?style=flat&logo=graphql&logoColor=white)](https://graphql.org)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![PostGIS](https://img.shields.io/badge/PostGIS-Geospatial-336791?style=flat)](https://postgis.net)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--time-010101?style=flat)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

🌐 **Live:** [nearcash.cadencepay.us](https://nearcash.cadencepay.us) &nbsp;|&nbsp; 📦 **Frontend:** [NearCash Frontend](https://github.com/Zedtek-me/NearCash-Frontend)

---

## What is NearCash?

Think **Uber — but for cash and foreign exchange liquidity**.

In Nigeria and across Africa, accessing physical cash or foreign currency (USD, GBP, EUR) is a real, daily friction. POS vendors and FX bureaus are scattered, their availability is unknown, and rates are opaque. People walk to multiple kiosks only to find a vendor is out of cash, unavailable, or expensive.

**NearCash solves this** by geo-matching clients with nearby available vendors in real time — with live tracking, transparent rates, KYC-verified identities, and a smart fallback matching engine when a chosen vendor is unavailable.

---

## Core Features

### 🗺️ Geolocation-Powered Vendor Discovery
- Clients see vendors ranked by proximity using **PostGIS spatial queries**
- Configurable search radius: 3km → 5km → 15km (expands automatically if results are sparse)
- Supports both **local currency (NGN)** POS vendors and **FX vendors** (USD, GBP, EUR, etc.)

### ⚡ Real-Time Transaction Matching Engine
The heart of NearCash is a smart, event-driven transaction flow:

1. Client requests cash from a chosen vendor
2. Vendor has **30 seconds** to respond
3. If vendor delays or is unavailable, client gets three options:
   - **Wait** — system notifies the original vendor again
   - **Auto-Search** — system discovers other nearby vendors with sufficient liquidity and **broadcasts the transaction opportunity** to them simultaneously; first vendor to accept wins
   - **Cancel** — transaction is terminated cleanly
4. If no vendor accepts the broadcast within 30 seconds, client is notified to retry

### 📡 Live Location Tracking via WebSockets
- `navigator.geolocation.watchPosition` captures both vendor and client positions continuously
- Location updates are streamed to the backend and pushed in real time over **WebSockets** (Django Channels)
- Both parties see each other's live location on an embedded map during an active transaction — eliminating the overhead of repeated HTTP polling

### 🏦 Vendor Liquidity Management
- Vendors declare available liquidity on daily login and can update it anytime
- Vendors configure a **liquidity threshold** — when balance drops below it, the system sends automatic **email + push notifications**
- Transactions are only routed to vendors with sufficient liquidity to fulfill the request amount

### 🪪 KYC Onboarding
- Full KYC flow for both vendors and clients
- Collects: National Identity Number (NIN), real-time facial capture / photograph, business details (for vendors)
- Ensures every participant on the platform is a verified, accountable identity

### ⭐ Vendor Ratings *(in development)*
- Clients will be able to rate vendors post-transaction
- Ratings feed into vendor trust scores and will influence broadcast priority ordering

### 🔔 Background Task Processing
- Celery workers handle async workloads: liquidity threshold alerts, transaction notifications, email receipts
- Redis as the message broker

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django + Django Graphene (GraphQL) |
| **API** | GraphQL (queries, mutations, subscriptions) |
| **Real-Time** | Django Channels + WebSockets |
| **Database** | PostgreSQL + PostGIS |
| **Async Tasks** | Celery + Redis |
| **Maps & Routing** | Google Maps API + Geoapify |
| **Auth** | JWT-based authentication |
| **Containerization** | Docker + Docker Compose |
| **Web Server** | Nginx (reverse proxy) |
| **CI/CD** | GitHub Actions |
| **Deployment** | Contabo VPS |

---

## Project Structure

```
NearCash-API/
├── apps/                    # Core Django applications
│   ├── users/               # Auth, KYC, user management
│   ├── transactions/        # Transaction lifecycle & matching engine
│   ├── notifications/       # Push & email notification handlers
│   └── core/                # Shared business logic
├── background_tasks/        # Celery task definitions
├── dtos/                    # Data Transfer Objects (typed input/output contracts)
├── interfaces/              # Abstract interfaces & base classes
├── utils/                   # Shared utilities (type-hinted helpers)
├── near_cash/               # Django project settings & routing
├── templates/               # Email templates
├── .github/workflows/       # CI/CD pipelines
├── Dockerfile               # Production image
├── Dockerfile.staging       # Staging image
├── nearcash-compose.yml     # Production Docker Compose
├── nearcash-local-compose.yml # Local dev Docker Compose
├── nginx.conf               # Nginx reverse proxy config
└── start.sh                 # Production entrypoint
```

---

## Getting Started (Local Development)

### Prerequisites
- Docker & Docker Compose
- A `.env` file (see `sample.env` for required variables)

### Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/Zedtek-me/NearCash-API.git
cd NearCash-API

# 2. Copy environment variables
cp sample.env .env
# Fill in your values (DB credentials, Google Maps API key, etc.)

# 3. Start all services
docker compose -f nearcash-local-compose.yml up --build
```

The API will be available at `http://localhost:8000/graphql`

---

## Example GraphQL Operations

### Discover Nearby Vendors
```graphql
query {
  nearbyVendors(lat: 6.5244, lng: 3.3792, radiusKm: 3) {
    id
    businessName
    distance
    availableLiquidity
    vendorType        # POS or FX
    supportedCurrencies
    deliveryPolicy    # WALK_IN or DELIVERY
    rating
  }
}
```

### Initiate a Cash Request
```graphql
mutation {
  requestCash(input: {
    vendorId: "uuid-here"
    amount: 50000
    currency: "NGN"
  }) {
    transaction {
      id
      status
      vendorResponseDeadline
    }
  }
}
```

### Trigger Auto-Search Broadcast
```graphql
mutation {
  broadcastTransactionRequest(input: {
    transactionId: "txn-uuid"
    radiusKm: 5
  }) {
    broadcastedTo
    status
  }
}
```

---

## Architecture Highlights

**Why GraphQL?**
A single flexible API serves both the web frontend and the upcoming mobile app without needing separate REST endpoint versions.

**Why PostGIS?**
Native geospatial indexing enables sub-millisecond proximity queries at scale — far more efficient than application-level distance calculations.

**Why WebSockets over polling?**
Live transaction tracking requires continuous bi-directional updates. WebSockets eliminate repeated TCP handshake overhead and deliver smoother real-time UX.

**Why DTOs + Interfaces?**
Enforces strict input/output contracts across service boundaries, making the codebase more maintainable as the system scales and new engineers join.

---

## Roadmap

- [x] Vendor & client KYC onboarding
- [x] Geolocation vendor discovery (PostGIS)
- [x] Real-time transaction matching engine
- [x] WebSocket live location tracking
- [x] Vendor liquidity management + threshold alerts
- [x] FX vendor support
- [x] CI/CD pipeline (GitHub Actions)
- [ ] Vendor ratings & trust scoring
- [ ] Priority ordering in broadcast matching
- [ ] Vendor-to-vendor liquidity sourcing (wholesale layer)
- [ ] Mobile app (React Native)
- [ ] Public vendor API for third-party integrations

---

## Author

**Zechariah Adebayo** — Backend & Full-Stack Engineer, Lagos Nigeria

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/zechariah-adebayo)
[![GitHub](https://img.shields.io/badge/GitHub-Zedtek--me-181717?style=flat&logo=github)](https://github.com/Zedtek-me)

---

*NearCash is actively in development. Vendor and client onboarding coming soon.*
