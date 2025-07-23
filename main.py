#!/usr/bin/env python3
"""
Audit App Dashboard
-------------------
Final merged version:
- Playback preview + scrub slider + time label.
- Scrollable video list (middle panel).
- Working Video Information panel.
- Clean function ordering (no NameError).
- Backward-compatible DB row handling (6 or 8 columns).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, Image as PILImage
import sqlite3
import os
import cv2
import datetime

# -----------------------------------------------------------------------------
# THEME (optional)
# -----------------------------------------------------------------------------
try:
    import theme  # local file (optional)
except ImportError:
    theme = None

# -----------------------------------------------------------------------------
# CONFIG / CONSTANTS
# -----------------------------------------------------------------------------
DB_PATH = "videos.db"
VIDEOS_DIR = "videos"
THUMBS_DIR = "thumbnails"
JUMP_SECONDS = 5

# column index helpers (GUI always uses 8-column tuples)
IDX_ID = 0
IDX_TITLE = 1
IDX_TIMESTAMP = 2
IDX_DURATION = 3
IDX_FILEPATH = 4
IDX_THUMB = 5
IDX_BOOTH = 6
IDX_CAMERA = 7

# ensure dirs exist (avoid crashes)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# DB ACCESS
# -----------------------------------------------------------------------------
def fetch_videos_from_db():
    """Return raw DB rows (whatever schema is in file)."""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM videos ORDER BY id")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"DB error: {e}")
        rows = []
    finally:
        conn.close()
    return rows

# -----------------------------------------------------------------------------
# Fallback dummy data (used only if DB empty)
# -----------------------------------------------------------------------------
DUMMY_VIDEOS = [
    (1, "Booth A1 Entry",   "2025-07-21 09:45:00", "00:25", "videos/booth_a1.mp4",    "thumbnails/booth_a1.jpg",   "A1", "001"),
    (2, "Highway Toll",     "2025-07-20 14:30:00", "00:30", "videos/highway.mp4",     "thumbnails/highway.jpg",    "A2", "002"),
    (3, "Parking Lot Sweep","2025-07-19 11:00:00", "01:10", "videos/parking.mp4",     "thumbnails/parking.jpg",    "A1", "001"),
    (4, "Night Patrol",     "2025-07-18 22:05:00", "00:40", "videos/night_patrol.mp4","thumbnails/night.jpg",      "A2", "002"),
]

def _coerce_rows_to_8cols(rows):
    """Take DB rows (len 6 or 8) and return list of 8-col tuples."""
    out = []
    for r in rows:
        if len(r) >= 8:
            out.append(tuple(r[:8]))
        elif len(r) == 6:
            # (id, title, timestamp, duration, filepath, thumb)
            out.append(tuple(r) + ("A1", "001"))
        else:
            # unexpected schema; pad
            padded = list(r) + ["?"] * (8 - len(r))
            out.append(tuple(padded[:8]))
    return out

def load_video_data():
    rows = fetch_videos_from_db()
    if rows:
        return _coerce_rows_to_8cols(rows)
    # DB empty? fallback
    return list(DUMMY_VIDEOS)

# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------
def parse_timestamp(ts_str):
    try:
        return datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def sort_videos(rows, latest_first=True):
    return sorted(
        rows,
        key=lambda r: parse_timestamp(r[IDX_TIMESTAMP]) or datetime.datetime.min,
        reverse=latest_first
    )

def load_thumbnail(path, size=(160, 90)):
    """Return an ImageTk object (always succeeds)."""
    try:
        if not os.path.exists(path):
            return ImageTk.PhotoImage(PILImage.new('RGB', size, color='gray'))
        img = PILImage.open(path).resize(size)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Thumbnail error {path}: {e}")
        return ImageTk.PhotoImage(PILImage.new('RGB', size, color='gray'))

def format_time(frames, fps=30):
    if not fps or fps <= 0:
        fps = 30
    seconds = int(frames / fps)
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"

# -----------------------------------------------------------------------------
# Embedded OpenCV Player
# -----------------------------------------------------------------------------
class OpenCVEmbeddedPlayer:
    def __init__(self, parent, display_size=(180, 100)):
        self.parent = parent
        self.display_w, self.display_h = display_size
        self.label = tk.Label(parent, bg="black")
        self.label.pack(fill="both", expand=True)
        self.cap = None
        self.playing = False
        self.video_path = None
        self.fps_delay = 33
        self.total_frames = 0
        self.current_frame_index = 0
        self.speed_factor = 1.0
        self.on_frame_callback = None
        self._after_id = None

    def load(self, path):
        self.stop()
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Video not found: {path}")
            return

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            messagebox.showerror("Error", f"Cannot open video: {path}")
            return

        self.cap = cap
        self.video_path = path

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps and fps > 1:
            self.fps_delay = int(1000 / fps)
        else:
            self.fps_delay = 33

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.current_frame_index = 0

        progress_scale.config(to=self.total_frames if self.total_frames else 1)
        progress_scale.set(0)

        if self.cap:
            total_time = format_time(self.total_frames, fps)
            time_label.config(text=f"00:00 / {total_time}")
        timeline_scroll_set(0.0)

        # enable transport buttons
        for btn in (play_btn, pause_btn, stop_btn, ff_btn, rew_btn, speed05_btn, speed1_btn, speed2_btn):
            btn.config(state="normal")

        self.play()

    def play(self):
        if self.cap is None or self.playing:
            return
        self.playing = True
        self._schedule_next_frame()

    def pause(self):
        self.playing = False
        if self._after_id is not None:
            self.label.after_cancel(self._after_id)
            self._after_id = None

    def stop(self):
        self.pause()
        if self.cap:
            self.cap.release()
            self.cap = None
        self._show_blank()
        try:
            progress_scale.set(0)
        except tk.TclError:
            pass
        self.current_frame_index = 0
        self.total_frames = 0
        time_label.config(text="00:00 / 00:00")
        timeline_scroll_set(0.0)
        for btn in (play_btn, pause_btn, stop_btn, ff_btn, rew_btn, speed05_btn, speed1_btn, speed2_btn):
            btn.config(state="disabled")

    def seek(self, frame_index, show_frame=False):
        if self.cap and 0 <= frame_index < self.total_frames:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            self.current_frame_index = frame_index
            if show_frame:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame_index = frame_index + 1
                    self._display_frame(frame)
                    if self.on_frame_callback:
                        self.on_frame_callback(self.current_frame_index)

    def set_speed(self, factor: float):
        self.speed_factor = max(0.1, float(factor))

    def _schedule_next_frame(self):
        if not self.playing or self.cap is None:
            return
        delay = max(1, int(self.fps_delay / self.speed_factor))
        self._after_id = self.label.after(delay, self._next_frame)

    def _next_frame(self):
        if not self.playing or self.cap is None:
            return
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_index += 1
            self._display_frame(frame)
            if self.on_frame_callback:
                self.on_frame_callback(self.current_frame_index)
            self._schedule_next_frame()
        else:
            self.playing = False  # end of video

    def _display_frame(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.resize(rgb, (self.display_w, self.display_h), interpolation=cv2.INTER_AREA)
        img = PILImage.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(img)
        self.label.imgtk = imgtk
        self.label.config(image=imgtk)

    def _show_blank(self):
        blank = PILImage.new('RGB', (self.display_w, self.display_h), color='black')
        imgtk = ImageTk.PhotoImage(blank)
        self.label.imgtk = imgtk
        self.label.config(image=imgtk)

# -----------------------------------------------------------------------------
# GLOBAL STATE PLACEHOLDERS (widgets assigned later)
# -----------------------------------------------------------------------------
player = None
selected_video = None
info_box = None
progress_scale = None
time_label = None
timeline_scroll = None
play_btn = pause_btn = stop_btn = ff_btn = rew_btn = speed05_btn = speed1_btn = speed2_btn = None
date_combo = booth_combo = camera_combo = sort_combo = None
video_count_label = None
scroll_frame = None
canvas = None

updating_scale = False  # used to avoid recursive seek updates

# -----------------------------------------------------------------------------
# UI helper functions (use globals; defined before widgets are created)
# -----------------------------------------------------------------------------
def ui_seek_to_frame(frame_target, resume=True):
    if not player or not player.cap or not player.total_frames:
        return
    frame_target = max(0, min(player.total_frames - 1, int(frame_target)))
    was_playing = player.playing
    player.pause()
    player.seek(frame_target, show_frame=True)
    if resume and was_playing:
        player.play()

def on_video_click(video_row):
    """Populate info panel and load preview player."""
    selected_video.set(video_row[IDX_FILEPATH])

    # clear previous info
    for w in info_box.winfo_children():
        w.destroy()

    # header
    tk.Label(info_box, text="Selected Video", bg="white", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(0,4))

    # resolution & size (if file exists)
    res_text = "Resolution: Unknown"
    size_text = "Size: Unknown"
    fp = video_row[IDX_FILEPATH]
    if os.path.exists(fp):
        cap = cv2.VideoCapture(fp)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            res_text = f"Resolution: {width}x{height}"
        cap.release()
        size_text = f"Size: {os.path.getsize(fp)//1024} KB"

    details = [
        f"ID: {video_row[IDX_ID]}",
        f"Title: {video_row[IDX_TITLE]}",
        f"Timestamp: {video_row[IDX_TIMESTAMP]}",
        f"Duration: {video_row[IDX_DURATION]}",
        f"Booth: {video_row[IDX_BOOTH]}",
        f"Camera: {video_row[IDX_CAMERA]}",
        res_text,
        size_text,
        f"File: {fp}"
    ]
    for line in details:
        tk.Label(info_box, text=line, bg="white", anchor="w", font=("Arial", 10)).pack(anchor="w", padx=20)

    player.load(fp)

def reset_filters():
    date_combo.set("Any")
    booth_combo.set("All")
    camera_combo.set("Any")
    apply_filters()

def play_clicked():
    player.play()

def pause_clicked():
    player.pause()

def stop_clicked():
    player.stop()

def on_seek(val):
    global updating_scale
    if updating_scale:
        return
    if player.cap and player.total_frames:
        frame_target = int(float(val))
        ui_seek_to_frame(frame_target, resume=True)

def seek_relative(seconds):
    if not player.cap:
        return
    fps = player.cap.get(cv2.CAP_PROP_FPS) or 30
    frame_jump = int(seconds * fps)
    target_frame = player.current_frame_index + frame_jump
    ui_seek_to_frame(target_frame, resume=True)

def on_timeline_scroll(action, *args):
    if not player.cap or not player.total_frames:
        return
    if action == 'moveto':
        frac = float(args[0])
        frame_target = int(frac * (player.total_frames - 1))
    elif action == 'scroll':
        count = int(args[0])
        what = args[1]
        step = 100 if what == 'pages' else 10
        frame_target = player.current_frame_index + count * step
    else:
        return
    ui_seek_to_frame(frame_target, resume=False)

def timeline_scroll_set(frac):
    # slider-length ~1%. We set lo=frac hi=frac+small
    hi = min(frac + 0.01, 1.0)
    timeline_scroll.set(frac, hi)

# -----------------------------------------------------------------------------
# Filtering helpers
# -----------------------------------------------------------------------------
def get_unique_date_strings(rows):
    seen, out = set(), []
    for r in rows:
        date_part = r[IDX_TIMESTAMP].split(" ")[0] if r[IDX_TIMESTAMP] else ""
        if date_part and date_part not in seen:
            seen.add(date_part)
            out.append(date_part)
    return sorted(out, reverse=True)

def get_unique_booths(rows):
    return sorted({r[IDX_BOOTH] for r in rows})

def get_unique_cameras(rows):
    return sorted({r[IDX_CAMERA] for r in rows})

def apply_filters(*_):
    """Apply current filter combobox selections and re-render list."""
    date_sel = date_combo.get()
    booth_sel = booth_combo.get()
    cam_sel = camera_combo.get()

    filtered = []
    for r in ALL_VIDEOS:
        ok = True
        if date_sel != "Any":
            date_part = r[IDX_TIMESTAMP].split(" ")[0]
            ok = ok and (date_part == date_sel)
        if booth_sel != "All":
            ok = ok and (r[IDX_BOOTH] == booth_sel)
        if cam_sel != "Any":
            ok = ok and (r[IDX_CAMERA] == cam_sel)
        if ok:
            filtered.append(r)

    latest = (sort_combo.get() == "Latest First")
    filtered = sort_videos(filtered, latest_first=latest)
    render_video_grid(filtered)

# -----------------------------------------------------------------------------
# Accept / Reject / Play full handlers
# -----------------------------------------------------------------------------
def accept_video():
    if selected_video.get():
        messagebox.showinfo("Action", f"Video accepted: {selected_video.get()}")

def reject_video():
    if selected_video.get():
        messagebox.showinfo("Action", f"Video rejected: {selected_video.get()}")

def play_full():
    if not selected_video.get():
        return
    fp = selected_video.get()
    if os.name == 'nt':
        os.startfile(fp)
    elif os.name == 'posix':
        os.system(f'open "{fp}"')  # macOS; adjust for Linux if needed
    else:
        messagebox.showinfo("Open", fp)

# -----------------------------------------------------------------------------
# Tk root
# -----------------------------------------------------------------------------
root = tk.Tk()
root.title("Audit App Dashboard")
root.geometry("1350x750")
root.configure(bg="#f6f6f6")

# theme
if theme:
    style = theme.setup_theme(root)
else:
    style = None

# selected video path
selected_video = tk.StringVar()

# -----------------------------------------------------------------------------
# FILTER / PLAYBACK PANEL (LEFT)
# -----------------------------------------------------------------------------
filter_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
filter_frame.place(x=20, y=20, width=270, height=720)

# Heading
if theme:
    ttk.Label(filter_frame, text="Filters", style="AuditHeading.TLabel").pack(pady=10)
else:
    tk.Label(filter_frame, text="Filters", bg="white", font=("Arial", 12, "bold")).pack(pady=10)

# Date filter
tk.Label(filter_frame, text="Date", bg="white").pack(anchor="w", padx=10)
date_combo = ttk.Combobox(filter_frame, values=["Any"], state="readonly")
date_combo.pack(fill="x", padx=10)
date_combo.set("Any")

# Booth filter
tk.Label(filter_frame, text="Booth", bg="white").pack(anchor="w", padx=10, pady=(10, 2))
booth_combo = ttk.Combobox(filter_frame, values=["All"], state="readonly")
booth_combo.pack(fill="x", padx=10)
booth_combo.set("All")

# Camera filter
tk.Label(filter_frame, text="Camera ID", bg="white").pack(anchor="w", padx=10, pady=(10, 2))
camera_combo = ttk.Combobox(filter_frame, values=["Any"], state="readonly")
camera_combo.pack(fill="x", padx=10)
camera_combo.set("Any")

# Reset / Apply
if theme:
    ttk.Button(filter_frame, text="Reset", style="Audit.TButton", command=reset_filters).pack(pady=6)
    ttk.Button(filter_frame, text="Apply", style="Audit.TButton", command=apply_filters).pack(pady=(0, 12))
else:
    tk.Button(filter_frame, text="Reset", bg="#e0e0e0", command=reset_filters).pack(pady=12)
    tk.Button(filter_frame, text="Apply", bg="#d0ffd0", command=apply_filters).pack(pady=(0, 12))

# Playback subheading
if theme:
    ttk.Label(filter_frame, text="Playback", style="AuditHeading.TLabel").pack()
else:
    tk.Label(filter_frame, text="Playback", bg="white", font=("Arial", 10, "bold")).pack()

# Preview container
preview_container = tk.Frame(filter_frame, bg="black", width=220, height=160)
preview_container.pack(pady=8, padx=10)
preview_container.pack_propagate(False)

# instantiate player
player = OpenCVEmbeddedPlayer(preview_container, display_size=(200, 120))

# transport controls
controls = tk.Frame(filter_frame, bg="white")
controls.pack(pady=8)
play_btn = tk.Button(controls, text="Play", width=6, command=play_clicked, state="disabled")
pause_btn = tk.Button(controls, text="Pause", width=6, command=pause_clicked, state="disabled")
stop_btn = tk.Button(controls, text="Stop", width=6, command=stop_clicked, state="disabled")
play_btn.grid(row=0, column=0, padx=4, pady=3)
pause_btn.grid(row=0, column=1, padx=4, pady=3)
stop_btn.grid(row=0, column=2, padx=4, pady=3)

rew_btn = tk.Button(controls, text="<<", width=6, command=lambda: seek_relative(-JUMP_SECONDS), state="disabled")
ff_btn  = tk.Button(controls, text=">>", width=6, command=lambda: seek_relative(JUMP_SECONDS), state="disabled")
rew_btn.grid(row=1, column=0, padx=4, pady=3)
ff_btn.grid(row=1, column=2, padx=4, pady=3)

speed05_btn = tk.Button(controls, text="0.5x", width=6, command=lambda: player.set_speed(0.5), state="disabled")
speed1_btn  = tk.Button(controls, text="1x", width=6, command=lambda: player.set_speed(1.0), state="disabled")
speed2_btn  = tk.Button(controls, text="2x", width=6, command=lambda: player.set_speed(2.0), state="disabled")
speed05_btn.grid(row=2, column=0, padx=4, pady=3)
speed1_btn.grid(row=2, column=1, padx=4, pady=3)
speed2_btn.grid(row=2, column=2, padx=4, pady=3)

# progress scale (seek slider)
progress_scale = tk.Scale(
    filter_frame,
    from_=0, to=1,
    orient="horizontal",
    length=230,
    bg="white",
    highlightthickness=0,
    sliderlength=15
)
progress_scale.pack(pady=5)

def on_scale_release(event):
    on_seek(progress_scale.get())
progress_scale.bind("<ButtonRelease-1>", on_scale_release)

# playback time label (00:00 / 00:00)
time_label = tk.Label(filter_frame, text="00:00 / 00:00", bg="white", font=("Arial", 9))
time_label.pack()

# playback timeline scrollbar (alternative fine scrub)
timeline_scroll = tk.Scrollbar(filter_frame, orient="horizontal", command=on_timeline_scroll)
timeline_scroll.pack(fill="x", padx=10, pady=(4, 6))

# -----------------------------------------------------------------------------
# VIDEOS LIST PANEL (MIDDLE)
# -----------------------------------------------------------------------------
videos_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
videos_frame.place(x=310, y=20, width=600, height=700)

video_count_label = tk.Label(videos_frame, text="Videos: 0", bg="white", font=("Arial", 10, "bold"))
video_count_label.pack(anchor="w", padx=10, pady=5)

sort_combo = ttk.Combobox(videos_frame, values=["Latest First", "Oldest First"], state="readonly")
sort_combo.set("Latest First")
sort_combo.pack(anchor="e", padx=10)

# scrollable list container
list_container = tk.Frame(videos_frame, bg="white")
list_container.pack(fill="both", expand=True, padx=0, pady=0)

canvas = tk.Canvas(list_container, bg="white", highlightthickness=0)
canvas.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.configure(yscrollcommand=scrollbar.set)

# frame that holds each video row
scroll_frame = tk.Frame(canvas, bg="white")
canvas_window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

def _on_scroll_frame_config(event):
    # match inner width to canvas width; update scrollregion
    canvas.itemconfig(canvas_window_id, width=canvas.winfo_width())
    canvas.configure(scrollregion=canvas.bbox("all"))
scroll_frame.bind("<Configure>", _on_scroll_frame_config)

# mousewheel support
def _on_mousewheel_windows(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
def _on_mousewheel_linux(event):
    if event.num == 4:
        canvas.yview_scroll(-1, "units")
    elif event.num == 5:
        canvas.yview_scroll(1, "units")
canvas.bind_all("<MouseWheel>", _on_mousewheel_windows)  # Windows & often Mac
canvas.bind_all("<Button-4>", _on_mousewheel_linux)      # Linux up
canvas.bind_all("<Button-5>", _on_mousewheel_linux)      # Linux down

# -----------------------------------------------------------------------------
# VIDEO INFORMATION PANEL (RIGHT)
# -----------------------------------------------------------------------------
info_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
info_frame.place(x=930, y=20, width=380, height=700)

if theme:
    ttk.Label(info_frame, text="Video Information", style="AuditHeading.TLabel").pack(pady=10)
else:
    tk.Label(info_frame, text="Video Information", bg="white", font=("Arial", 12, "bold")).pack(pady=10)

info_box = tk.Frame(info_frame, bg="white")
info_box.pack(fill="both", expand=True, padx=10, pady=5)

action_frame = tk.Frame(info_frame, bg="white")
action_frame.pack(pady=10)

if theme:
    ttk.Button(action_frame, text="Accept", style="Positive.TButton", width=8, command=accept_video).pack(side="left", padx=5)
    ttk.Button(action_frame, text="Reject", style="Negative.TButton", width=8, command=reject_video).pack(side="left", padx=5)
    ttk.Button(action_frame, text="Play Full", style="Primary.TButton", width=10, command=play_full).pack(side="left", padx=5)
else:
    tk.Button(action_frame, text="Accept", bg="#4CAF50", fg="white", width=8, command=accept_video).pack(side="left", padx=5)
    tk.Button(action_frame, text="Reject", bg="#F44336", fg="white", width=8, command=reject_video).pack(side="left", padx=5)
    tk.Button(action_frame, text="Play Full", bg="#2196F3", fg="white", width=10, command=play_full).pack(side="left", padx=5)

# -----------------------------------------------------------------------------
# LOAD DATA, POPULATE FILTERS, RENDER
# -----------------------------------------------------------------------------
ALL_VIDEOS = load_video_data()

# fill combobox choices from data
date_combo["values"]   = ["Any"] + get_unique_date_strings(ALL_VIDEOS)
booth_combo["values"]  = ["All"] + get_unique_booths(ALL_VIDEOS)
camera_combo["values"] = ["Any"] + get_unique_cameras(ALL_VIDEOS)

# bind filters *after* apply_filters defined
date_combo.bind("<<ComboboxSelected>>", apply_filters)
booth_combo.bind("<<ComboboxSelected>>", apply_filters)
camera_combo.bind("<<ComboboxSelected>>", apply_filters)
sort_combo.bind("<<ComboboxSelected>>", apply_filters)

# -----------------------------------------------------------------------------
# Render list
# -----------------------------------------------------------------------------
def render_video_grid(video_list):
    """Render list of videos into scroll_frame."""
    # Clear
    for widget in scroll_frame.winfo_children():
        widget.destroy()

    video_count_label.config(text=f"Videos: {len(video_list)}")

    for vid in video_list:
        row_frame = tk.Frame(scroll_frame, bg="white", bd=1, relief="solid")
        row_frame.pack(fill="x", pady=4, padx=4)

        # thumbnail
        thumb_img = load_thumbnail(vid[IDX_THUMB])
        lbl_img = tk.Label(row_frame, image=thumb_img, bg="white")
        lbl_img.image = thumb_img  # keep ref
        lbl_img.pack(side="left", padx=5, pady=5)

        # text info
        text_frame = tk.Frame(row_frame, bg="white")
        text_frame.pack(side="left", fill="both", expand=True)

        title_full = vid[IDX_TITLE]
        title_short = title_full if len(title_full) <= 20 else title_full[:20] + "..."
        lbl_title = tk.Label(text_frame, text=title_short, bg="white", anchor="w", font=("Arial", 10, "bold"))
        lbl_title.pack(fill="x", padx=5)

        # hover show full title
        def _enter_factory(lbl, t=title_full):
            return lambda e: lbl.config(text=t)
        def _leave_factory(lbl, t=title_short):
            return lambda e: lbl.config(text=t)
        lbl_title.bind("<Enter>", _enter_factory(lbl_title))
        lbl_title.bind("<Leave>", _leave_factory(lbl_title))

        tk.Label(text_frame, text=vid[IDX_TIMESTAMP], bg="white", anchor="w", font=("Arial", 9)).pack(fill="x", padx=5)

        # select button
        if theme:
            ttk.Button(row_frame, text="Select", style="Audit.TButton",
                       command=lambda v=vid: on_video_click(v)).pack(side="right", padx=5, pady=5)
        else:
            tk.Button(row_frame, text="Select", bg="#e0e0e0",
                      command=lambda v=vid: on_video_click(v)).pack(side="right", padx=5, pady=5)

    # update scroll region
    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

# initial render
apply_filters()

# -----------------------------------------------------------------------------
# Player progress update callback
# -----------------------------------------------------------------------------
def update_progress(frame_index):
    """Called by player each frame to sync slider / label / mini-scrollbar."""
    global updating_scale
    if player.cap is None:
        return
    try:
        updating_scale = True
        progress_scale.set(frame_index)
        fps = player.cap.get(cv2.CAP_PROP_FPS) or 30
        current_time = format_time(frame_index, fps)
        total_time = format_time(player.total_frames, fps)
        time_label.config(text=f"{current_time} / {total_time}")
        frac = frame_index / float(player.total_frames) if player.total_frames else 0.0
        timeline_scroll_set(frac)
    finally:
        updating_scale = False

player.on_frame_callback = update_progress

# -----------------------------------------------------------------------------
# Optional button hover visual (if theme)
# -----------------------------------------------------------------------------
if theme:
    theme.attach_hover(play_btn,    theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(pause_btn,   theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(stop_btn,    theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(ff_btn,      theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(rew_btn,     theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(speed05_btn, theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(speed1_btn,  theme.BTN_GRAY, theme.BTN_GRAY_HOVER)
    theme.attach_hover(speed2_btn,  theme.BTN_GRAY, theme.BTN_GRAY_HOVER)

# -----------------------------------------------------------------------------
# Mainloop
# -----------------------------------------------------------------------------
root.mainloop()
