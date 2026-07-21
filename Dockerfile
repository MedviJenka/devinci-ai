ARG version=3.12-slim

FROM python:${version} AS build
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .

FROM build AS npc_service
CMD ["uv", "run", "python", "-m", "services.npc_service"]

FROM build AS payment_service
CMD ["uv", "run", "python", "-m", "services.payment_service"]
