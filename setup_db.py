import sqlite3
import os
import glob
from datetime import datetime
import cv2
from PIL import Image

DB_PATH = "videos.db"
VIDEOS_DIR = "videos"
THUMBS_DIR = "thumbnails"

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Metadata helper
# ------------------------------------------------------------------
def get_video_metadata(fp):
    if not os.path.exists(fp):
        return "Unknown", None
    cap = cv2.VideoCapture(fp)
    if not cap.isOpened():
        return "Unknown", None
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    if fps > 0 and total_frames > 0:
        secs = int(total_frames / fps)
        mm = secs // 60
        ss = secs % 60
        duration = f"{mm:02d}:{ss:02d}"
    else:
        duration = "Unknown"
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return duration, None
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    return duration, pil_img

# ------------------------------------------------------------------
# Resolve video path: prefer videos/video{num}.mp4, fallback to root
# ------------------------------------------------------------------
def resolve_video_path(num: int) -> str:
    fname = f"video{num}.mp4"
    in_videos = os.path.join(VIDEOS_DIR, fname)
    if os.path.exists(in_videos):
        return in_videos
    # fallback root-level
    return fname

# ------------------------------------------------------------------
# Resolve thumbnail path (always under THUMBS_DIR)
# ------------------------------------------------------------------
def resolve_thumb_path(num: int) -> str:
    return os.path.join(THUMBS_DIR, f"thumb{num}.png")

# ------------------------------------------------------------------
# DB setup
# ------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    duration TEXT NOT NULL,
    filepath TEXT NOT NULL,
    thumbnail_path TEXT NOT NULL
)
''')

# ------------------------------------------------------------------
# Seed known rows (1–4, 12, and now 13–15)
# ------------------------------------------------------------------
seed_rows = [
    ("Audit Footage 1",  "2024-07-19 10:00:00", "00:15", resolve_video_path(1),  resolve_thumb_path(1)),
    ("Audit Footage 2",  "2024-07-19 10:10:00", "00:30", resolve_video_path(2),  resolve_thumb_path(2)),
    ("Audit Footage 3",  "2024-07-19 10:20:00", "00:45", resolve_video_path(3),  resolve_thumb_path(3)),
    ("Audit Footage 4",  "2024-07-19 10:30:00", "01:00", resolve_video_path(4),  resolve_thumb_path(4)),
    ("Audit Footage 12", "2024-07-19 10:50:00", "00:12", resolve_video_path(12), resolve_thumb_path(12)),
    # newly added
    ("Audit Footage 13", "2024-07-19 11:00:00", "00:50", resolve_video_path(13), resolve_thumb_path(13)),
    ("Audit Footage 14", "2024-07-19 11:10:00", "00:35", resolve_video_path(14), resolve_thumb_path(14)),
    ("Audit Footage 15", "2024-07-19 11:20:00", "01:00", resolve_video_path(15), resolve_thumb_path(15)),
]

for title, ts, dur, fp, thumb in seed_rows:
    cursor.execute("SELECT COUNT(*) FROM videos WHERE filepath = ?", (fp,))
    if cursor.fetchone()[0] == 0:
        # Generate thumbnail if video exists
        if os.path.exists(fp):
            dur, pil_img = get_video_metadata(fp)
            if pil_img:
                pil_img.thumbnail((160, 90))
                pil_img.save(thumb)
        cursor.execute("""
            INSERT INTO videos (title, timestamp, duration, filepath, thumbnail_path)
            VALUES (?, ?, ?, ?, ?)
        """, (title, ts, dur, fp, thumb))
        print(f"✅ Added seed {fp}")
    else:
        print(f"ℹ️ Seed exists: {fp}")

# ------------------------------------------------------------------
# Collect MP4s from /videos and root (auto-add any you missed)
# ------------------------------------------------------------------
mp4_paths = set()
# videos dir
mp4_paths.update(
    os.path.join(VIDEOS_DIR, f)
    for f in os.listdir(VIDEOS_DIR)
    if f.lower().endswith(".mp4")
)
# root-level
mp4_paths.update(glob.glob("*.mp4"))

for fp in sorted(mp4_paths):
    cursor.execute("SELECT COUNT(*) FROM videos WHERE filepath = ?", (fp,))
    if cursor.fetchone()[0] != 0:
        continue

    base = os.path.basename(fp)
    stem, _ = os.path.splitext(base)
    num = "".join(ch for ch in stem if ch.isdigit())

    if num:
        title = f"Audit Footage {num}"
    else:
        title = stem.replace("_", " ").title()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dur, pil_img = get_video_metadata(fp)

    thumb = os.path.join(THUMBS_DIR, f"thumb{num or stem}.png")
    if pil_img is not None:
        pil_img.thumbnail((160, 90))
        pil_img.save(thumb)
    else:
        thumb = os.path.join(THUMBS_DIR, "default.png")

    cursor.execute("""
        INSERT INTO videos (title, timestamp, duration, filepath, thumbnail_path)
        VALUES (?, ?, ?, ?, ?)
    """, (title, ts, dur, fp, thumb))
    print(f"✅ Auto-added {fp}")

conn.commit()
conn.close()
print("🎉 Database updated.")