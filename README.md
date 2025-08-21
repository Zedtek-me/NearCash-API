# NearCash 💸  
_A geolocation-powered fintech platform for POS vendors and clients_

## 🚀 Overview
NearCash is a fintech MVP designed for the Nigerian market to make cash withdrawals and vendor-client interactions seamless.  

The platform enables:  
- **POS Vendors**: Register their businesses, configure withdrawal ranges and charge rates, and manage customer transactions.  
- **Clients**: Discover nearby vendors via geolocation, view vendor details, and get real-time route guidance to their location.  

NearCash demonstrates real-world fintech workflows, geospatial queries, and scalable backend design.

---

## ✨ Key Features
- **Vendor Management**: Sign up, configure business info, set withdrawal/charges.  
- **Client Discovery**: Locate nearby POS vendors via GPS.  
- **Geolocation + Routing**: Uses PostGIS + external APIs (Geoapify, Leaflet) for spatial queries and directions.  
- **Transaction Management**: Secure and idempotent workflows for withdrawals.  
- **Background Processing**: Celery workers handle async tasks (e.g. notifications, receipts).  
- **API-First Design**: GraphQL schema for easy integration with frontend/mobile.  
- **Dockerized Setup**: Run locally with one command.  

---

## 🛠️ Tech Stack
- **Backend**: Django + Django Graphene (GraphQL)  
- **Database**: PostgreSQL + PostGIS (geospatial support)  
- **Async Tasks**: Celery + Redis  
- **Frontend (companion)**: React + TailwindCSS (planned)  
- **Containerization**: Docker & Docker Compose  

---

## 📂 Project Structure
```bash
NearCash-API/
├── apps/                # Core business logic
│   ├── core/            # Business & vendor services
│   ├── users/           # User management
├── utils/               # Shared utilities (type hinted)
├── background_tasks/    # Celery workers
├── core/schema/         # GraphQL schema (mutations & queries)
└── docker/              # Docker configs
```

#Getting Started

# Clone repo
git clone https://github.com/Zedtek-me/NearCash-API.git
cd NearCash-API

# Run with Docker
docker-compose up --build

#Sample query

query {
  nearbyVendors(lat: 6.5244, lng: 3.3792, radius: 2000) {
    id
    name
    address
    distance
  }
}


#Sample Mutation

mutation {
  createBusiness(input: {
    name: "John's POS",
    address: "Ikeja, Lagos",
    withdrawalRange: "1000-50000",
    chargeRate: 0.02
  }) {
    business {
      id
      name
    }
  }
}

