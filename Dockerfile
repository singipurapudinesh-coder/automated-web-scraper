
FROM python:3.11-slim

# Install Chromium and ChromeDriver for Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Runtime configuration
ENV PYTHONUNBUFFERED=1
ENV SELENIUM_HEADLESS=true

# Initialize sample jobs and start the recurring scheduler
CMD ["sh", "-c", "python cli.py init && exec python cli.py schedule"]
