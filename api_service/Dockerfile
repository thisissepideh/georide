# api_service/Dockerfile

# ---- Stage 1: Builder ----
# This stage builds a virtual environment with our dependencies.
FROM python:3.11-slim as builder

# Prevent python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: Final Image ----
# This is our lean production image.
FROM python:3.11-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY app.py .

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]