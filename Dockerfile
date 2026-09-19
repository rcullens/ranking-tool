FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY sixman_rankings ./sixman_rankings
COPY app.py ./
RUN pip install --no-cache-dir -e . && pip install --no-cache-dir -r requirements.txt

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn sixman_rankings.web.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
