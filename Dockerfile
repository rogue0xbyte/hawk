FROM python:3.13-slim

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock* /app/

RUN echo 'alias hawk="poetry run hawk"' >> /root/.bashrc
RUN echo 'alias webui="poetry run webui"' >> /root/.bashrc

# Add project venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the app
COPY . /app

RUN poetry install

# Default command
CMD ["hawk", "--help"]
