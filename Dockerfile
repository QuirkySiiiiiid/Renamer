# Use a specific, stable Python version instead of 'latest'
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first for caching
COPY requirements.txt /app/

# Update and install system dependencies
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
       git \
       ffmpeg \
    && rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Specify the command to run the application
CMD ["python", "bot.py"]

