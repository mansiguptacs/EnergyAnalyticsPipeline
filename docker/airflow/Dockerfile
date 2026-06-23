# ==============================================================================
# Energy Analytics Pipeline — Custom Airflow Image
# ==============================================================================
# Based on the official Airflow image with our project dependencies installed.
# ==============================================================================

FROM apache/airflow:2.7.3-python3.10

USER root

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set the working directory
WORKDIR /opt/airflow
