# Use Python base image
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install project dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose FastAPI (uvicorn) default port
EXPOSE 8000

# Start FastAPI app using Uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
