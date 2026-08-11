import os
from typing import Tuple


def detect_and_generate_dockerfile(repo_path: str) -> Tuple[str, str, int]:
    """
    Scans repository directory for build manifests.
    If Dockerfile exists, returns (dockerfile_path, detected_stack, default_port).
    If missing, auto-generates an optimized multi-stage Dockerfile and returns its path.
    """
    dockerfile_custom = os.path.join(repo_path, "Dockerfile")
    if os.path.exists(dockerfile_custom):
        return dockerfile_custom, "Custom Dockerfile", 8000

    dockerfile_lower = os.path.join(repo_path, "dockerfile")
    if os.path.exists(dockerfile_lower):
        return dockerfile_lower, "Custom Dockerfile", 8000

    # 1. Node.js Detection
    if os.path.exists(os.path.join(repo_path, "package.json")):
        content = """FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build --if-present

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package*.json ./
RUN npm install --only=production
COPY --from=builder /app ./
EXPOSE 3000
CMD ["npm", "start"]
"""
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(content)
        return dockerfile_path, "Node.js (Auto Generated)", 3000

    # 2. Python Detection
    if (
        os.path.exists(os.path.join(repo_path, "requirements.txt"))
        or os.path.exists(os.path.join(repo_path, "pyproject.toml"))
        or os.path.exists(os.path.join(repo_path, "Pipfile"))
        or os.path.exists(os.path.join(repo_path, "main.py"))
        or os.path.exists(os.path.join(repo_path, "app.py"))
    ):
        content = """FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "if [ -f main.py ]; then python main.py; elif [ -f app.py ]; then python app.py; else uvicorn main:app --host 0.0.0.0 --port 8000; fi"]
"""
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(content)
        return dockerfile_path, "Python (Auto Generated)", 8000

    # 3. Go Detection
    if os.path.exists(os.path.join(repo_path, "go.mod")):
        content = """FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download || true
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/server ./
EXPOSE 8080
CMD ["./server"]
"""
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(content)
        return dockerfile_path, "Go (Auto Generated)", 8080

    # 4. Rust Detection
    if os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        content = """FROM rust:1.76-alpine AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/target/release/* ./app_server
EXPOSE 8080
CMD ["./app_server"]
"""
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(content)
        return dockerfile_path, "Rust (Auto Generated)", 8080

    # 5. Static Web Site Detection
    if os.path.exists(os.path.join(repo_path, "index.html")):
        content = """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
"""
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(content)
        return dockerfile_path, "Static Web (Auto Generated)", 80

    # Default Fallback
    content = """FROM alpine:latest
WORKDIR /app
COPY . .
EXPOSE 8000
CMD ["top", "-b"]
"""
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write(content)
    return dockerfile_path, "Generic Container (Fallback)", 8000
