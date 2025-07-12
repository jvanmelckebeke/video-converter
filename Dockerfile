FROM python:3.9-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Copy requirements and install them.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY video_optimizer/ main.py .

# Run the script when the container starts.
CMD ["python", "main.py"]
