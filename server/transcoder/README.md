# Nuvio optional transcoder

This service is deliberately optional. Nuvio should Direct Play/Direct Download by default and use this service only when the selected source is too large/heavy or the user explicitly selects a smaller offline quality.

## NUC install

```bash
cd server/transcoder
cp .env.example .env
# replace change-me with: openssl rand -hex 32
docker compose up -d --build
curl http://127.0.0.1:8099/health
```

Intel VAAPI is used when `/dev/dri/renderD128` is available. Otherwise the service falls back to CPU x265.

## Profiles

- `1080p-high`: ~8 Mbit/s video
- `1080p-small`: ~5 Mbit/s video
- `720p`: ~3 Mbit/s video

## API

All endpoints except `/health` require `Authorization: Bearer <NUVIO_TRANSCODER_TOKEN>`.

`GET /probe?url=<encoded source URL>` inspects bitrate, codec and resolution.

`GET /transcode?profile=1080p-small&url=<encoded source URL>` returns a fragmented MP4 suitable for progressive playback/download.

Recommended client logic: probe when source metadata is insufficient. Direct play/download when the source fits the device/network preference. Route through `/transcode` only when bitrate/resolution exceeds the configured limit or when the user selects a smaller offline profile.

Do not expose port 8099 directly to the public internet. Put it behind your existing reverse proxy/tunnel with HTTPS and keep the bearer token secret.
