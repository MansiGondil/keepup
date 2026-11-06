# Image for running Keepup's Python code (pipeline, evaluation scripts).
# Running inside Linux avoids Windows blocking PyTorch's DLLs.
FROM python:3.12-slim

WORKDIR /app

# CPU-only PyTorch first: much smaller than the default GPU build. Doing it
# before requirements.txt means sentence-transformers finds torch already
# installed and doesn't pull the large GPU version.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install the other packages. Copying only requirements.txt first lets
# Docker reuse this slow step when just the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the code last (.env is excluded by .dockerignore).
COPY . .
