FROM node:24-bookworm-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend ./
RUN FIGMA_PUBLIC_URL=/app-ui pnpm build

FROM node:24-bookworm-slim AS mobile

WORKDIR /mobile
COPY mobile/package.json mobile/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY mobile ./
RUN pnpm build

FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY --from=frontend /frontend/dist ./app/static/app-ui
COPY --from=mobile /mobile/dist ./app/static/mobile-ui

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
