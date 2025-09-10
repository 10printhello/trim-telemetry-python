FROM python:3.11-slim

WORKDIR /app

# Copy the local package to a separate location and install it
COPY trim_telemetry /tmp/trim_telemetry
COPY setup.py /tmp/
COPY README.md /tmp/
WORKDIR /tmp
RUN pip install -e .

# Switch back to app directory and copy example project
WORKDIR /app
COPY example/ .

# Install the example project requirements
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
