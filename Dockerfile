# Use a slim, official Python image
FROM python:3.11-slim

# Set an environment variable for where Airflow will live
ENV AIRFLOW_HOME=/opt/airflow
# Add the path for pip-installed executables to the system's PATH. Standard location for system-wide pip installs.
ENV PATH="/usr/local/bin:${PATH}"

# Define Airflow and Python versions as arguments to keep the build clean
ARG AIRFLOW_VERSION=2.9.2
ARG PYTHON_VERSION=3.11
ENV AIRFLOW_VERSION=${AIRFLOW_VERSION}

# Create a non-root user and its home directory FIRST
RUN useradd -ms /bin/bash -d ${AIRFLOW_HOME} airflow

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    curl \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR ${AIRFLOW_HOME}

# --- THE FIX (v2): Install Airflow using the CORRECT constraint file URL ---
# The URL format is simpler for recent Airflow versions.
# This single command installs Airflow, its providers (postgres, docker),
# and all core dependencies like SQLAlchemy, pinned to versions tested by the Airflow team.
RUN pip install --no-cache-dir \
    "apache-airflow[postgres,docker]==${AIRFLOW_VERSION}" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# Copy and install the rest of the project requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy our project files into the home directory
COPY . .

# Create the mlruns directory and set proper permissions
RUN mkdir -p ${AIRFLOW_HOME}/mlruns && \
    mkdir -p ${AIRFLOW_HOME}/mlruns/.trash && \
    chown -R airflow:airflow ${AIRFLOW_HOME}

# Set the user for running the container
USER airflow