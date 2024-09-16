# Stage 1: Build stage
FROM python:3.9-slim AS builder
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final stage
FROM python:3.9-alpine AS runner
WORKDIR /app
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
EXPOSE 5000
CMD ["python3.9", "app.py"]
