FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends iperf3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 5201

CMD ["iperf3", "-s"]
