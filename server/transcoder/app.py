import asyncio
import os
import shlex
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="Nuvio Transcoder", version="0.1.0")
TOKEN = os.getenv("NUVIO_TRANSCODER_TOKEN", "")
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_BIN", "ffprobe")

PROFILES = {
    "1080p-high": {"height": 1080, "vb": "8M", "maxrate": "10M", "bufsize": "16M", "ab": "192k"},
    "1080p-small": {"height": 1080, "vb": "5M", "maxrate": "6M", "bufsize": "10M", "ab": "160k"},
    "720p": {"height": 720, "vb": "3M", "maxrate": "4M", "bufsize": "6M", "ab": "128k"},
}


def authorize(auth: str | None):
    if not TOKEN:
        raise HTTPException(503, "NUVIO_TRANSCODER_TOKEN is not configured")
    if auth != f"Bearer {TOKEN}":
        raise HTTPException(401, "Invalid transcoder token")


def ffmpeg_args(url: str, profile: str, hw: bool) -> list[str]:
    p = PROFILES[profile]
    scale = f"scale=-2:'min({p['height']},ih)'"
    args = [FFMPEG, "-hide_banner", "-loglevel", "warning", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"]
    if hw:
        # Decode is left on auto; VAAPI is used for encoding when available.
        args += ["-vaapi_device", "/dev/dri/renderD128"]
    args += ["-i", url, "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "-1"]
    if hw:
        args += ["-vf", f"{scale},format=nv12,hwupload", "-c:v", "hevc_vaapi", "-b:v", p["vb"], "-maxrate", p["maxrate"], "-bufsize", p["bufsize"]]
    else:
        args += ["-vf", scale, "-c:v", "libx265", "-preset", "veryfast", "-b:v", p["vb"], "-maxrate", p["maxrate"], "-bufsize", p["bufsize"]]
    args += ["-c:a", "aac", "-b:a", p["ab"], "-ac", "2", "-movflags", "frag_keyframe+empty_moov+default_base_moof", "-f", "mp4", "pipe:1"]
    return args


@app.get("/health")
async def health():
    return {"ok": True, "profiles": list(PROFILES), "vaapi": os.path.exists("/dev/dri/renderD128")}


@app.get("/profiles")
async def profiles(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return PROFILES


@app.get("/probe")
async def probe(url: str = Query(...), authorization: str | None = Header(default=None)):
    authorize(authorization)
    cmd = [FFPROBE, "-v", "error", "-show_entries", "format=bit_rate,duration,size", "-show_entries", "stream=index,codec_type,codec_name,width,height,bit_rate", "-of", "json", url]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    if proc.returncode:
        raise HTTPException(502, err.decode(errors="replace")[-1000:])
    return __import__("json").loads(out)


@app.get("/transcode")
async def transcode(request: Request, url: str = Query(...), profile: str = Query("1080p-small"), hw: bool = Query(True), authorization: str | None = Header(default=None)):
    authorize(authorization)
    if profile not in PROFILES:
        raise HTTPException(400, f"Unknown profile: {profile}")
    if hw and not os.path.exists("/dev/dri/renderD128"):
        hw = False
    cmd = ffmpeg_args(url, profile, hw)
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    async def body() -> AsyncIterator[bytes]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                chunk = await proc.stdout.read(1024 * 256)
                if not chunk:
                    break
                yield chunk
        finally:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), 5)
                except asyncio.TimeoutError:
                    proc.kill()

    return StreamingResponse(body(), media_type="video/mp4", headers={"Cache-Control": "no-store", "X-Nuvio-Profile": profile})
