FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# gcc and others might be needed for some python packages
# netcat-openbsd is useful for wait-for-it scripts if needed, but we rely on python logic or fails
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Make script executable
RUN chmod +x scripts/prestart.sh

# Environment variables
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Entrypoint using the prestart script
ENTRYPOINT ["scripts/prestart.sh"]

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
