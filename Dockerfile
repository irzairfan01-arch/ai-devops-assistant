# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by Git and scanners
RUN apt-get update -qq && \
    apt-get install -y -qq git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy packaging files first to leverage Docker cache
COPY pyproject.toml README.md CHANGELOG.md ./
COPY src/ ./src/

# Install the package globally with all optional dependencies
RUN pip install --no-cache-dir .[all]

# Set the default command to the CLI tool
ENTRYPOINT ["devops-assistant"]
CMD ["--help"]
