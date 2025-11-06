from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
from pathlib import Path
from datetime import datetime
import logging
from urllib.parse import quote

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DOWNLOAD_FOLDER = Path("downloads")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

LOG_FILE = Path("download_logs.txt")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_message(message):
    """Log message to file and console"""
    logger.info(message)

def progress_hook(d):
    """Hook to track download progress"""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        log_message(f"Downloading: {percent} | Speed: {speed} | ETA: {eta}")
    elif d['status'] == 'finished':
        log_message(f"Download finished: {d.get('filename', 'Unknown')}")
        log_message("Processing file...")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("video_form.html", {"request": request})

@app.get("/logs", response_class=PlainTextResponse)
async def view_logs():
    """Endpoint to view download logs"""
    if LOG_FILE.exists():
        return LOG_FILE.read_text()
    return "No logs available yet."

@app.get("/videos", response_class=HTMLResponse)
async def list_videos(request: Request):
    """Endpoint to list all downloaded videos"""
    videos = []
    if DOWNLOAD_FOLDER.exists():
        for file in DOWNLOAD_FOLDER.glob("*.mp4"):
            file_size = file.stat().st_size
            size_mb = file_size / (1024 * 1024)
            videos.append({
                "name": file.name,
                "size": f"{size_mb:.2f} MB",
                "path": quote(file.name)
            })

    return templates.TemplateResponse("video_list.html", {
        "request": request,
        "videos": videos
    })

@app.get("/watch/{filename:path}")
async def watch_video(request: Request, filename: str):
    """Endpoint to watch a video"""
    return templates.TemplateResponse("video_player.html", {
        "request": request,
        "filename": filename
    })

@app.get("/stream/{filename:path}")
async def stream_video(filename: str):
    """Endpoint to stream video file"""
    file_path = DOWNLOAD_FOLDER / filename
    if not file_path.exists():
        return HTMLResponse("Video not found", status_code=404)

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=filename
    )

@app.post("/download", response_class=HTMLResponse)
async def download_video(request: Request, video_url: str = Form(...)):
    try:
        log_message(f"========== NEW DOWNLOAD REQUEST ==========")
        log_message(f"URL: {video_url}")

        output_path = DOWNLOAD_FOLDER / "%(title)s.%(ext)s"

        ydl_opts = {
            'format': 'best',
            'outtmpl': str(output_path),
            'quiet': False,
            'no_warnings': False,
            'progress_hooks': [progress_hook],
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'prefer_ffmpeg': True,
        }

        log_message("Starting video extraction...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_title = info.get('title', 'Unknown')
            ext = info.get('ext', 'mp4')
            filename = f"{video_title}.{ext}"
            filesize = info.get('filesize', 'Unknown')
            duration = info.get('duration', 'Unknown')

        log_message(f"SUCCESS: Video saved as '{filename}'")
        log_message(f"File size: {filesize} bytes")
        log_message(f"Duration: {duration} seconds")
        log_message("==========================================\n")

        return templates.TemplateResponse("video_result.html", {
            "request": request,
            "success": True,
            "message": f"Video downloaded successfully: {filename}",
            "filename": filename,
            "error": None
        })

    except Exception as e:
        error_msg = f"Error downloading video: {str(e)}"
        log_message(f"ERROR: {error_msg}")
        log_message("==========================================\n")

        return templates.TemplateResponse("video_result.html", {
            "request": request,
            "success": False,
            "message": None,
            "filename": None,
            "error": error_msg
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
