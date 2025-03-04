# Use a lightweight official Python image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first for efficient caching
COPY requirements.txt .

# Install dependencies (if requirements.txt exists)
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files into the container
COPY . .

# Set a default command (optional, for debugging)
CMD ["streamlit", "run", "run_ui.py", "--server.port=80", "--server.address=0.0.0.0"]
