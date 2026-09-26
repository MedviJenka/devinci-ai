ARG version=3.12-slim

FROM python:${version} AS build
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen

FROM build AS npc_service
CMD ["uv", "run", "python", "-m", "services.npc_service"]
