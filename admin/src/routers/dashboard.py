import time

from fastapi import APIRouter, Depends, Request

from core.auth import require_admin, token_expiry
from core.config import templates
from core.settings import setting
from utils.format import humanize_seconds

router = APIRouter(dependencies=[Depends(require_admin)])


SERVICES_CATALOG = [
    {
        "id": "postgres",
        "name": "PostgreSQL",
        "category": "database",
        "category_label": "Database",
        "badge": "PG",
        "badge_color": "text-kube",
        "description": "Relational SQL database engine with ACID compliance, JSONB support, and full-text search capability.",
        "port": "5432",
        "port_label": "Default Port",
        "version": "v16.2",
        "status": "Ready",
        "subtitle": "Postgres Relational DB",
    },
    {
        "id": "mongodb",
        "name": "MongoDB",
        "category": "database",
        "category_label": "Database",
        "badge": "MDB",
        "badge_color": "text-ok",
        "description": "High-performance document-oriented NoSQL database for flexible JSON-like records.",
        "port": "27017",
        "port_label": "Default Port",
        "version": "v7.0.5",
        "status": "Ready",
        "subtitle": "NoSQL Document Store",
    },
    {
        "id": "redis",
        "name": "Redis",
        "category": "database",
        "category_label": "Database",
        "badge": "RDS",
        "badge_color": "text-crit",
        "description": "Ultra-fast in-memory key-value data structure store, cache layer, and pub/sub message broker.",
        "port": "6379",
        "port_label": "Default Port",
        "version": "v7.2.4",
        "status": "Ready",
        "subtitle": "In-Memory Cache & Key-Value",
    },
    {
        "id": "rabbitmq",
        "name": "RabbitMQ",
        "category": "database",
        "category_label": "Database",
        "badge": "RMQ",
        "badge_color": "text-warn",
        "description": "Enterprise AMQP message broker for task queues, background jobs, and event-driven architecture.",
        "port": "5672 / 15672",
        "port_label": "Default Port",
        "version": "v3.13.0",
        "status": "Ready",
        "subtitle": "AMQP Message Queue Broker",
    },
    {
        "id": "zincsearch",
        "name": "ZincSearch",
        "category": "database",
        "category_label": "Database",
        "badge": "ZNC",
        "badge_color": "text-ember",
        "description": "Lightweight search engine and log indexer designed as a low-resource Elasticsearch alternative.",
        "port": "4080",
        "port_label": "Default Port",
        "version": "v0.4.8",
        "status": "Ready",
        "subtitle": "Search Engine & Log Indexer",
    },
    {
        "id": "garage",
        "name": "Garage Storage",
        "category": "uploads",
        "category_label": "Uploads",
        "badge": "GRG",
        "badge_color": "text-ember",
        "description": "Geo-distributed, S3-compatible object storage designed for media uploads, buckets, and asset storage.",
        "port": "3900",
        "port_label": "S3 API Port",
        "version": "v1.0.0",
        "status": "Ready",
        "subtitle": "S3 Object Storage",
    },
    {
        "id": "registry",
        "name": "Image Registry",
        "category": "registry",
        "category_label": "Image Registry",
        "badge": "REG",
        "badge_color": "text-kube",
        "description": "Private OCI-compliant container image registry for storing, pushing, and pulling docker cluster images.",
        "port": "5000",
        "port_label": "Registry Port",
        "version": "OCI v2",
        "status": "Ready",
        "subtitle": "OCI Container Registry",
    },
]


@router.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {"services": SERVICES_CATALOG},
    )


@router.get("/dashboard/status")
def dashboard_status(request: Request):
    expires_at = token_expiry(request.cookies.get(setting.COOKIE_NAME))
    remaining = expires_at - int(time.time()) if expires_at else 0

    return templates.TemplateResponse(
        request,
        "partials/status.html",
        {"remaining": humanize_seconds(remaining)},
    )
