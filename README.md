# AuctionLive - Real-Time Auction Platform

A production-grade real-time auction platform with live bidding via WebSockets, auction categories, bid history, auto-bidding, countdown timers, and seller dashboards.

## Tech Stack

| Layer       | Technology                              |
|-------------|----------------------------------------|
| Backend     | Django 5.x, Django REST Framework, Channels |
| Frontend    | React 18, Redux Toolkit, React Router  |
| Database    | PostgreSQL 16                          |
| Cache/Broker| Redis 7                                |
| Task Queue  | Celery 5.x                            |
| Real-time   | WebSocket (Django Channels + Daphne)   |
| Proxy       | Nginx                                  |
| Containers  | Docker, Docker Compose                 |

## Features

- **Real-time bidding** via WebSocket connections with instant price updates
- **Auto-bidding** system that automatically places bids up to a user-defined maximum
- **Live countdown timers** synchronized across all connected clients
- **Auction categories** with hierarchical organization
- **Bid history** with full audit trail for every auction
- **Seller dashboards** with auction management, analytics, and revenue tracking
- **Watchlist** for tracking favorite auctions
- **Payment and escrow** system for secure transactions
- **Notification system** for outbid alerts, auction ending, and win notifications
- **Image uploads** with multiple images per auction
- **User authentication** with JWT tokens (access + refresh)
- **Role-based access** with seller and bidder profiles

## Architecture

```
Client (React) <---> Nginx <---> Daphne (ASGI)
                                    |
                         +----------+-----------+
                         |                      |
                    HTTP (DRF)          WebSocket (Channels)
                         |                      |
                    PostgreSQL             Redis (Channel Layer)
                         |
                    Celery Worker <--- Redis (Broker)
```

## Prerequisites

- Docker and Docker Compose
- Git

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/auctionlive.git
   cd auctionlive
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start all services**
   ```bash
   docker-compose up --build
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost/api/
   - Admin panel: http://localhost/api/admin/
   - WebSocket: ws://localhost/ws/auction/{auction_id}/

## API Endpoints

### Authentication
| Method | Endpoint                | Description           |
|--------|-------------------------|-----------------------|
| POST   | `/api/auth/register/`   | Register new user     |
| POST   | `/api/auth/login/`      | Obtain JWT tokens     |
| POST   | `/api/auth/refresh/`    | Refresh access token  |
| GET    | `/api/auth/profile/`    | Get user profile      |
| PUT    | `/api/auth/profile/`    | Update user profile   |

### Auctions
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | `/api/auctions/`                  | List all active auctions |
| POST   | `/api/auctions/`                  | Create new auction       |
| GET    | `/api/auctions/{id}/`             | Get auction details      |
| PUT    | `/api/auctions/{id}/`             | Update auction           |
| DELETE | `/api/auctions/{id}/`             | Delete auction           |
| GET    | `/api/auctions/categories/`       | List categories          |
| GET    | `/api/auctions/seller-dashboard/` | Seller dashboard data    |

### Bids
| Method | Endpoint                       | Description            |
|--------|--------------------------------|------------------------|
| POST   | `/api/bids/`                   | Place a bid            |
| GET    | `/api/bids/auction/{id}/`      | Bid history for auction|
| POST   | `/api/bids/auto-bid/`          | Set up auto-bidding    |
| GET    | `/api/bids/auto-bid/`          | List user's auto-bids  |
| DELETE | `/api/bids/auto-bid/{id}/`     | Cancel auto-bid        |

### Watchlist
| Method | Endpoint                    | Description              |
|--------|-----------------------------|--------------------------|
| GET    | `/api/watchlist/`           | List watchlist items     |
| POST   | `/api/watchlist/`           | Add auction to watchlist |
| DELETE | `/api/watchlist/{id}/`      | Remove from watchlist    |

### Payments
| Method | Endpoint                     | Description             |
|--------|------------------------------|-------------------------|
| POST   | `/api/payments/`             | Create payment          |
| GET    | `/api/payments/{id}/`        | Get payment details     |
| POST   | `/api/payments/{id}/confirm/`| Confirm payment         |

## WebSocket Protocol

### Connection
```
ws://localhost/ws/auction/{auction_id}/
```

### Messages (Client -> Server)
```json
{
  "type": "place_bid",
  "amount": "150.00"
}
```

### Messages (Server -> Client)
```json
{
  "type": "new_bid",
  "bid": {
    "id": 1,
    "bidder": "username",
    "amount": "150.00",
    "timestamp": "2026-01-15T10:30:00Z"
  },
  "auction": {
    "current_price": "150.00",
    "total_bids": 15
  }
}
```

```json
{
  "type": "auction_update",
  "status": "ended",
  "winner": "username",
  "final_price": "250.00"
}
```

## Development

### Running tests
```bash
docker-compose exec backend python manage.py test
```

### Accessing Django shell
```bash
docker-compose exec backend python manage.py shell
```

### Viewing logs
```bash
docker-compose logs -f backend
docker-compose logs -f celery
```

## Environment Variables

See `.env.example` for all available configuration variables.

## License

MIT License
