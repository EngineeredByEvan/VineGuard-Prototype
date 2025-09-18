# Mosquitto TLS Setup

Place generated TLS assets in `certs/` prior to running docker compose:

- `ca.crt`: CA certificate used by devices and services to verify the broker
- `server.crt`/`server.key`: Broker certificate/key signed by the CA

Generate a password file with `mosquitto_passwd` and mount it as
`passwordfile` in this directory to configure user credentials matching the
`.env.example` files for gateway and ingestor services.
