FROM python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev && rm -rf /var/lib/apt/lists/*
COPY aioquic-fork /opt/aioquic-fork
RUN pip install --no-cache-dir /opt/aioquic-fork
COPY client/client.py /app/client.py
CMD ["sleep", "infinity"]
