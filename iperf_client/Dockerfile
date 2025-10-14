FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends iperf3 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["iperf3"]

CMD ["-c", "172.21.0.3", "-t", "10"]
