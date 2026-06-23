# Energy Analytics Pipeline ⚡📊

> End-to-end data engineering platform for energy consumption analytics — built with Python, SQL, Apache Airflow, and PostgreSQL.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Airflow 2.7](https://img.shields.io/badge/Airflow-2.7-green.svg)](https://airflow.apache.org/)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Overview

This project is a **production-quality data engineering portfolio project** that demonstrates how to build a real-world data platform from scratch. It ingests smart meter energy consumption data, validates data quality, transforms raw data through a three-layer architecture (raw → staging → analytics), orchestrates workflows with Apache Airflow, and provides dashboards for reporting.

### Key Features

- **Three-layer data architecture** (Medallion pattern): raw → staging → analytics
- **Star schema** data model with fact and dimension tables (including SCD Type 2)
- **Apache Airflow** orchestration with production-grade DAGs
- **Data quality framework** with null checks, duplicate detection, range validation, and outlier detection
- **Idempotent pipelines** — safe to re-run for any date
- **Structured JSON logging** for observability
- **Docker Compose** for one-command local development
- **Comprehensive test suite** with unit and integration tests

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  DATA SOURCES        ORCHESTRATION          STORAGE         │
│                                                             │
│  CSV/JSON ──────▶  Apache Airflow  ──────▶  PostgreSQL     │
│  Smart Meter        ┌──────────┐           ┌───────────┐   │
│  Telemetry          │ Ingest   │           │ raw       │   │
│  Weather            │ Validate │           │ staging   │   │
│                     │ Transform│           │ analytics │   │
│                     └──────────┘           │ dq        │   │
│                                            └───────────┘   │
│                                                             │
│  PRESENTATION              MONITORING                       │
│  Superset/Grafana          Structured Logging + Alerts      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Python 3.10+](https://www.python.org/downloads/) (for local development)
- [Make](https://www.gnu.org/software/make/) (comes pre-installed on macOS/Linux)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/energy-analytics-pipeline.git
cd energy-analytics-pipeline
cp .env.example .env
```

### 2. Start services

```bash
make up
```

This starts PostgreSQL, Airflow (webserver + scheduler), and Grafana.

### 3. Initialize the database

```bash
make init-db
```

Creates all schemas, tables, indexes, and seeds dimension tables.

### 4. Generate sample data

```bash
make generate-data
```

Generates 30 days of realistic meter readings (~200K rows) with intentional data quality issues.

### 5. Run the pipeline

```bash
make run-pipeline
```

### 6. Access services

| Service | URL | Credentials |
|---|---|---|
| Airflow UI | [http://localhost:8080](http://localhost:8080) | admin / admin |
| PostgreSQL | localhost:5432 | energy_user / energy_pass |
| Grafana | [http://localhost:3000](http://localhost:3000) | admin / admin |

---

## 📁 Project Structure

```
energy-analytics-pipeline/
├── dags/                    # Airflow DAG definitions
├── src/                     # Core application code
│   ├── ingestion/           #   CSV → raw layer ingestion
│   ├── quality/             #   Data quality framework
│   ├── transforms/          #   Transformation utilities
│   └── utils/               #   Config, DB, logging helpers
├── sql/
│   ├── schema/              # DDL scripts (run in order: 001-007)
│   ├── transforms/          # ELT SQL transformations
│   └── queries/             # Analytical queries
├── scripts/                 # Utility scripts (data gen, DB init)
├── tests/                   # Test suite (unit + integration)
├── config/                  # YAML configs (DQ checks, Grafana)
├── docker/                  # Dockerfiles
├── data/                    # Local data (gitignored)
├── docs/                    # Documentation
├── docker-compose.yml       # Local dev stack
├── Makefile                 # Task automation
└── pyproject.toml           # Python project config
```

---

## 🗄️ Data Model

### Star Schema

```
              dim_date
                 │
dim_customer ── fact_consumption ── dim_meter
                 │                     │
              dim_time            dim_location
```

- **fact_consumption**: One row per (meter, 15-minute reading) — consumption_kwh, cost_usd, peak_demand_kw
- **dim_customer**: SCD Type 2 — tracks tariff/status changes over time
- **dim_meter**: Meter metadata linked to customer and location
- **dim_date**: Pre-populated 2010–2030 (7,670 rows)
- **dim_time**: 96 rows (one per 15-minute interval)
- **dim_location**: Physical sites

---

## 🧪 Testing

```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Lint and format
make lint
make format
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Orchestration | Apache Airflow 2.7 | Pipeline scheduling, dependency management |
| Database | PostgreSQL 15 | Data storage across all layers |
| Language | Python 3.10+ | Ingestion, DQ checks, utilities |
| Transforms | SQL | ELT transformations (raw→staging→analytics) |
| Containerization | Docker Compose | One-command local environment |
| Code Quality | ruff, black, mypy | Linting, formatting, type checking |
| Testing | pytest | Unit and integration tests |
| Monitoring | Grafana | Pipeline and DB metrics |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
