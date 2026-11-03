FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8001

WORKDIR /app
COPY mcp_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN useradd --create-home --uid 10001 appuser
COPY mcp_service/sales_mcp_server.py /app/sales_mcp_server.py
USER appuser

EXPOSE 8001
CMD ["python", "sales_mcp_server.py"]
