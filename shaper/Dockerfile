FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         iproute2 \
         iptables \
         iputils-ping \
         procps \
         python3 \
         python3-flask \
         ca-certificates \
         curl \
     && rm -rf /var/lib/apt/lists/*

COPY shaping-controller.py /app/
COPY policies.json /app/
COPY startup.sh /app/

WORKDIR /app
RUN chmod +x startup.sh

EXPOSE 5000

CMD ["/app/startup.sh"]