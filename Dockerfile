FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to avoid virtual environments
RUN poetry config virtualenvs.create false

# Copy pyproject.toml and install dependencies without a lock file
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . .

# Expose the port for FastAPI
EXPOSE 8000

# Run the FastAPI app with Uvicorn
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}", "--reload"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --reload"]