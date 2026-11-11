
# AI Crypto Trading Bot — System Architecture

## 1. Project Overview

An AI-powered, multi-agent cryptocurrency trading platform with human approval before trade execution.

The initial trial focuses on spot trading and paper execution.

## 2. Technology Stack

- Language: Python 3.12
- Backend: FastAPI
- Database: PostgreSQL 16
- Cache and coordination: Redis 7
- ORM: SQLAlchemy
- Database migrations: Alembic
- AI integration: Claude API
- Containerization: Docker
- Exchange integration: CCXT / supported exchange APIs
- Strategy framework: Freqtrade

## 3. Specialist Agents

1. Market Data & Universe Agent
2. Technical Analysis Agent
3. News & Sentiment Agent
4. Small-Cap Research Agent
5. Strategy Agent
6. Head of Desk Agent
7. Risk Management Agent
8. Guardian Agent
9. Accounting & Tax Agent

## 4. Core Infrastructure

### PostgreSQL

Stores users, strategies, trades, orders, risk configurations, and historical records.

### Redis

Handles caching, temporary data, agent coordination, and heartbeat information.

### FastAPI

Provides backend APIs and connects application components.

### Claude API

Provides language-model capabilities for research, sentiment analysis, and decision support.

## 5. Trading Workflow

1. Collect market data.
2. Analyze technical indicators.
3. Analyze news and sentiment.
4. Research relevant assets.
5. Generate strategy signals.
6. Head of Desk evaluates trade proposals.
7. Risk Agent validates trade parameters.
8. User approves or rejects the proposal.
9. Paper Executor simulates the approved order.
10. Accounting Agent records trade results.
11. Guardian monitors system health and safety.

## 6. Safety Principles

- Spot trading only during the trial.
- No leverage or futures.
- No live-money execution during the trial.
- Human approval required before execution.
- Risk validation must happen before execution.
- Guardian can pause trading independently.
- Exchange credentials must never have withdrawal permissions.
- API keys and passwords must never be committed to Git.

## 7. Current Development Status

Day 1:
- Python environment configured.
- Docker configured.
- PostgreSQL connected.
- Redis connected.
- SQLAlchemy configured.
- Alembic configured.
- Initial User model created.
- First database migration applied.
