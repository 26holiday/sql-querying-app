# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Prevent Python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., gcc, libpq-dev)
RUN apt-get update && apt-get install -y gcc libpq-dev

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the project code
COPY . /app/

# Expose port 8000 for the app
EXPOSE 8000

# Run Gunicorn to serve the app
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]
