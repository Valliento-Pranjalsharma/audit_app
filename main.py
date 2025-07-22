"""
Audit App Dashboard (Scrollbar-Fixed Version)
=============================================

This version starts from the full GUI code you last posted and applies **only the
changes needed to make the vertical scrollbar in the video list reliably visible
and functional**. Your prior data, layout, and behavior are preserved.

### What Changed (summary)
- Replaced the original `canvas` + `scrollbar` layout in the *Videos* panel with a
  more robust pattern (`list_container` frame wrapping a fixed-size canvas + scrollbar).
- Ensures canvas has a constrained display region so overflow triggers scrolling.
- Binds `<Configure>` on the inner `scroll_frame` to update the canvas scrollregion.
- After each grid render, forces a geometry update (`canvas.update_idletasks()`) then
  resets scrollregion (safety double-set).
- Fixed a syntax typo in `_enter_factory` (you had `def _enter_factory(lbl, t=title_full):00`).
- Added light mousewheel scrolling support (Windows/Mac/Linux variants).

No changes to:
- DB fetch logic
- Dummy fallback list
- Player controls & filters
- Theme usage (still optional)

Run with:
    python main.py

If you add more videos to the DB while the app is open, restart the app (or ask me to
add a Reload button).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, Image as PILImage
import sqlite3
import os
import cv2
import datetime

# -----------------------------------------------------------------------------
# THEME IMPORT (safe fallback)
# -----------------------------------------------------------------------------
try:
    import theme  # your theme.py should be in the same folder as this script
except ImportError:  # if missing, run without theme
    theme = None

# =============================================================================
# CONFIG
# =============================================================================
DB_PATH = "videos.db"
JUMP_SECONDS = 5
updating_scale = False

IDX_ID = 0
IDX_TITLE = 1
IDX_TIMESTAMP = 2
IDX_DURATION = 3
IDX_FILEPATH = 4
IDX_THUMB = 5
IDX_BOOTH = 6
IDX_CAMERA = 7

# =============================================================================
# DB ACCESS
# =============================================================================

def fetch_videos_from_db():
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

# =============================================================================
# Dummy Data (fallback only if DB returns no rows)
# =============================================================================
DUMMY_VIDEOS = [
    (1, "Booth A1 Entry",   "2025-07-21 09:45:00", "00:25", "videos/booth_a1.mp4",    "thumbnails/booth_a1.jpg",   "A1", "001"),
    (2, "Highway Toll",      "2025-07-20 14:30:00", "00:30", "videos/highway.mp4",     "thumbnails/highway.jpg",    "A2", "002"),
    (3, "Parking Lot Sweep", "2025-07-19 11:00:00", "01:10", "videos/parking.mp4",     "thumbnails/parking.jpg",    "A1", "001"),
    (4, "Night Patrol",      "2025-07-18 22:05:00", "00:40", "videos/night_patrol.mp4","thumbnails/night.jpg",      "A2", "002"),
]


def load_video_data():
    """Load rows from DB; if none, use dummy fallback.
    If DB schema has only 6 columns (no booth/camera), append defaults so GUI works.
    """
    rows = fetch_videos_from_db()
    if rows:
        # DB returning 6 columns? extend with default booth/camera so UI works.
        if len(rows[0]) == 6:
            rows = [tuple(row) + ("A1", "001") for row in rows]
        # If DB already has >6 columns, assume proper extended schema.
    else:
        rows = list(DUMMY_VIDEOS)
    return rows

# =============================================================================
# Utility helpers
# =============================================================================

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

# =============================================================================
# Embedded OpenCV Player
# =============================================================================
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

        for btn in (play_btn, pause_btn, stop_btn, ff_btn, rew_btn, speed05_btn, speed1_btn, speed2_btn):
            btn.config(state="normal")

        self.play()

    def play(self):
        if self.cap is None:
            return
        if self.playing:
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
            self.playing = False

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

# =============================================================================
# UI HELPER FUNCTIONS
# =============================================================================

def ui_seek_to_frame(frame_target, resume=True):
    if not player.cap or not player.total_frames:
        return
    frame_target = max(0, min(player.total_frames - 1, int(frame_target)))
    was_playing = player.playing
    player.pause()
    player.seek(frame_target, show_frame=True)
    if resume and was_playing:
        player.play()


def on_video_click(video_row):
    selected_video.set(video_row[IDX_FILEPATH])
    for w in info_box.winfo_children():
        w.destroy()

    # Get resolution & size
    res_text = "Resolution: Unknown"
    size_text = "Size: Unknown"
    if os.path.exists(video_row[IDX_FILEPATH]):
        cap = cv2.VideoCapture(video_row[IDX_FILEPATH])
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            res_text = f"Resolution: {width}x{height}"
        cap.release()
        size_text = f"Size: {os.path.getsize(video_row[IDX_FILEPATH]) // 1024} KB"

    details = [
        f"ID: {video_row[IDX_ID]}",
        f"Title: {video_row[IDX_TITLE]}",
        f"Timestamp: {video_row[IDX_TIMESTAMP]}",
        f"Duration: {video_row[IDX_DURATION]}",
        f"Booth: {video_row[IDX_BOOTH]}",
        f"Camera: {video_row[IDX_CAMERA]}",
        res_text,
        size_text,
        f"File: {video_row[IDX_FILEPATH]}"
    ]
    for line in details:
        tk.Label(info_box, text=line, bg="white", font=("Arial", 10)).pack(anchor="w", padx=20)

    player.load(video_row[IDX_FILEPATH])


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
    hi = min(frac + 0.01, 1.0)
    timeline_scroll.set(frac, hi)

# =============================================================================
# FILTERING LOGIC
# =============================================================================

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

    # Sorting based on dropdown
    filtered = sort_videos(filtered, latest_first=(sort_combo.get() == "Latest First"))
    render_video_grid(filtered)

# =============================================================================
# GUI SETUP
# =============================================================================
root = tk.Tk()
root.title("Audit App Dashboard")
root.geometry("1200x650")
root.configure(bg="#f6f6f6")
selected_video = tk.StringVar()

# ---- Apply theme (if available) BEFORE building most ttk widgets ----
if theme:
    style = theme.setup_theme(root)
else:
    style = None

# Filter Frame
filter_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
filter_frame.place(x=20, y=20, width=250, height=600)

# Heading (use themed label if theme present)
if theme:
    ttk.Label(filter_frame, text="Filters", style="AuditHeading.TLabel").pack(pady=10)
else:
    tk.Label(filter_frame, text="Filters", bg="white", font=("Arial", 12, "bold")).pack(pady=10)

# Date
tk.Label(filter_frame, text="Date", bg="white").pack(anchor="w", padx=10)
date_combo = ttk.Combobox(filter_frame, values=["Any"], state="readonly")
date_combo.pack(fill="x", padx=10)
date_combo.set("Any")

# Booth
tk.Label(filter_frame, text="Booth", bg="white").pack(anchor="w", padx=10, pady=(10, 2))
booth_combo = ttk.Combobox(filter_frame, values=["All"], state="readonly")
booth_combo.pack(fill="x", padx=10)
booth_combo.set("All")

# Camera
tk.Label(filter_frame, text="Camera ID", bg="white").pack(anchor="w", padx=10, pady=(10, 2))
camera_combo = ttk.Combobox(filter_frame, values=["Any"], state="readonly")
camera_combo.pack(fill="x", padx=10)
camera_combo.set("Any")

# Reset & Apply use themed ttk buttons if available
if theme:
    ttk.Button(filter_frame, text="Reset", style="Audit.TButton", command=reset_filters).pack(pady=6)
    ttk.Button(filter_frame, text="Apply", style="Audit.TButton", command=apply_filters).pack(pady=(0, 12))
else:
    tk.Button(filter_frame, text="Reset", bg="#e0e0e0", command=reset_filters).pack(pady=12)
    tk.Button(filter_frame, text="Apply", bg="#d0ffd0", command=apply_filters).pack(pady=(0, 12))

# Video Preview Section
if theme:
    ttk.Label(filter_frame, text="Video Preview", style="AuditHeading.TLabel").pack()
else:
    tk.Label(filter_frame, text="Video Preview", bg="white", font=("Arial", 10, "bold")).pack()

preview_container = tk.Frame(filter_frame, bg="black", width=200, height=120)
preview_container.pack(pady=6, padx=10)
preview_container.pack_propagate(False)

player = OpenCVEmbeddedPlayer(preview_container, display_size=(180, 100))

controls = tk.Frame(filter_frame, bg="white")
controls.pack(pady=4)
play_btn = tk.Button(controls, text="Play", width=5, command=play_clicked, state="disabled")
pause_btn = tk.Button(controls, text="Pause", width=5, command=pause_clicked, state="disabled")
stop_btn = tk.Button(controls, text="Stop", width=5, command=stop_clicked, state="disabled")
play_btn.grid(row=0, column=0, padx=3)
pause_btn.grid(row=0, column=1, padx=3)
stop_btn.grid(row=0, column=2, padx=3)

rew_btn = tk.Button(controls, text="<<", width=5, command=lambda: seek_relative(-JUMP_SECONDS), state="disabled")
ff_btn = tk.Button(controls, text=">>", width=5, command=lambda: seek_relative(JUMP_SECONDS), state="disabled")
rew_btn.grid(row=1, column=0, padx=3, pady=3)
ff_btn.grid(row=1, column=2, padx=3, pady=3)

speed05_btn = tk.Button(controls, text="0.5x", width=5, command=lambda: player.set_speed(0.5), state="disabled")
speed1_btn = tk.Button(controls, text="1x", width=5, command=lambda: player.set_speed(1.0), state="disabled")
speed2_btn = tk.Button(controls, text="2x", width=5, command=lambda: player.set_speed(2.0), state="disabled")
speed05_btn.grid(row=2, column=0, padx=3, pady=3)
speed1_btn.grid(row=2, column=1, padx=3, pady=3)
speed2_btn.grid(row=2, column=2, padx=3, pady=3)

progress_scale = tk.Scale(filter_frame, from_=0, to=1, orient="horizontal", length=200, bg="white")
progress_scale.pack(pady=4)

time_label = tk.Label(filter_frame, text="00:00 / 00:00", bg="white", font=("Arial", 9))
time_label.pack()

timeline_scroll = tk.Scrollbar(filter_frame, orient="horizontal", command=on_timeline_scroll)
timeline_scroll.pack(fill="x", padx=10, pady=(2, 6))

# Update progress callback attaches after definition below

# =============================================================================
# Video List Frame (SCROLLBAR-FIXED)
# =============================================================================
videos_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
videos_frame.place(x=290, y=20, width=550, height=600)

video_count_label = tk.Label(videos_frame, text="Videos: 0", bg="white", font=("Arial", 10, "bold"))
video_count_label.pack(anchor="w", padx=10, pady=5)

sort_combo = ttk.Combobox(videos_frame, values=["Latest First", "Oldest First"], state="readonly")
sort_combo.set("Latest First")
sort_combo.pack(anchor="e", padx=10)
sort_combo.bind("<<ComboboxSelected>>", apply_filters)

# Scrollable region wrapper
list_container = tk.Frame(videos_frame, bg="white")
list_container.pack(fill="both", expand=True, padx=0, pady=0)

canvas = tk.Canvas(list_container, bg="white", highlightthickness=0)
canvas.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")

canvas.configure(yscrollcommand=scrollbar.set)

# The frame that will actually hold the video rows
scroll_frame = tk.Frame(canvas, bg="white")
canvas_window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

# When the inner frame resizes, update scrollregion

def _on_scroll_frame_config(event):
    # Make the inner window width match the canvas width to avoid horizontal jiggle
    canvas.itemconfig(canvas_window_id, width=canvas.winfo_width())
    canvas.configure(scrollregion=canvas.bbox("all"))

scroll_frame.bind("<Configure>", _on_scroll_frame_config)

# Mousewheel scroll support
# Windows/Mac OS X wheel events

def _on_mousewheel_windows(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

def _on_mousewheel_mac(event):  # on some Mac builds delta is in event.delta
    canvas.yview_scroll(int(-1*event.delta), "units")

def _on_mousewheel_linux(event):
    if event.num == 4:
        canvas.yview_scroll(-1, "units")
    elif event.num == 5:
        canvas.yview_scroll(1, "units")

# Bind platform-appropriate events
canvas.bind_all("<MouseWheel>", _on_mousewheel_windows)  # Windows
canvas.bind_all("<Button-4>", _on_mousewheel_linux)      # Linux scroll up
canvas.bind_all("<Button-5>", _on_mousewheel_linux)      # Linux scroll down
# (Mac often fires <MouseWheel> too; if not, additional OS checks could be added)

# =============================================================================
# Video Info Frame
# =============================================================================
info_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
info_frame.place(x=870, y=20, width=300, height=600)

if theme:
    ttk.Label(info_frame, text="Video Information", style="AuditHeading.TLabel").pack(pady=10)
else:
    tk.Label(info_frame, text="Video Information", bg="white", font=("Arial", 12, "bold")).pack(pady=10)

info_box = tk.Frame(info_frame, bg="white")
info_box.pack(fill="both", expand=True, padx=10, pady=5)

action_frame = tk.Frame(info_frame, bg="white")
action_frame.pack(pady=10)


def accept_video():
    if selected_video.get():
        messagebox.showinfo("Action", f"Video accepted: {selected_video.get()}")


def reject_video():
    if selected_video.get():
        messagebox.showinfo("Action", f"Video rejected: {selected_video.get()}")


def play_full():
    if selected_video.get():
        if os.name == 'nt':
            os.startfile(selected_video.get())
        else:
            os.system(f'open "{selected_video.get()}"')

# Themed buttons for actions
if theme:
    ttk.Button(action_frame, text="Accept", style="Positive.TButton", width=8, command=accept_video).pack(side="left", padx=5)
    ttk.Button(action_frame, text="Reject", style="Negative.TButton", width=8, command=reject_video).pack(side="left", padx=5)
    ttk.Button(action_frame, text="Play Full", style="Primary.TButton", width=10, command=play_full).pack(side="left", padx=5)
else:
    accept_btn = tk.Button(action_frame, text="Accept", bg="#4CAF50", fg="white", width=8, command=accept_video)
    reject_btn = tk.Button(action_frame, text="Reject", bg="#F44336", fg="white", width=8, command=reject_video)
    playfull_btn = tk.Button(action_frame, text="Play Full", bg="#2196F3", fg="white", width=10, command=play_full)
    accept_btn.pack(side="left", padx=5)
    reject_btn.pack(side="left", padx=5)
    playfull_btn.pack(side="left", padx=5)

# =============================================================================
# GLOBAL VIDEO DATA / RENDER
# =============================================================================
ALL_VIDEOS = load_video_data()


def update_progress(frame_index):
    """Update Scale, time label, and timeline scrollbar from current frame."""
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


def render_video_grid(video_list):
    """Render list of videos into scroll_frame."""
    # Clear list
    for widget in scroll_frame.winfo_children():
        widget.destroy()

    video_count_label.config(text=f"Videos: {len(video_list)}")

    for i, vid in enumerate(video_list):
        row_frame = tk.Frame(scroll_frame, bg="white", bd=1, relief="solid")
        row_frame.pack(fill="x", pady=4, padx=4)

        thumb_img = load_thumbnail(vid[IDX_THUMB])
        lbl_img = tk.Label(row_frame, image=thumb_img, bg="white")
        lbl_img.image = thumb_img
        lbl_img.pack(side="left", padx=5, pady=5)

        text_frame = tk.Frame(row_frame, bg="white")
        text_frame.pack(side="left", fill="both", expand=True)

        # Title label w/hover reveal full text
        title_full = vid[IDX_TITLE]
        title_short = title_full if len(title_full) <= 20 else title_full[:20] + "..."
        lbl_title = tk.Label(text_frame, text=title_short, bg="white", anchor="w", font=("Arial", 10, "bold"))
        lbl_title.pack(fill="x", padx=5)

        def _enter_factory(lbl, t=title_full):
            return lambda e: lbl.config(text=t)

        def _leave_factory(lbl, t=title_short):
            return lambda e: lbl.config(text=t)

        lbl_title.bind("<Enter>", _enter_factory(lbl_title))
        lbl_title.bind("<Leave>", _leave_factory(lbl_title))

        tk.Label(text_frame, text=vid[IDX_TIMESTAMP], bg="white", anchor="w", font=("Arial", 9)).pack(fill="x", padx=5)

        # Select button (themed if possible)
        if theme:
            ttk.Button(row_frame, text="Select", style="Audit.TButton", command=lambda v=vid: on_video_click(v)).pack(side="right", padx=5, pady=5)
        else:
            tk.Button(row_frame, text="Select", bg="#e0e0e0", command=lambda v=vid: on_video_click(v)).pack(side="right", padx=5, pady=5)

    # Force layout update so scrollregion can be recomputed
    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

# Populate filter dropdowns
date_combo["values"] = ["Any"] + get_unique_date_strings(ALL_VIDEOS)
booth_combo["values"] = ["All"] + get_unique_booths(ALL_VIDEOS)
camera_combo["values"] = ["Any"] + get_unique_cameras(ALL_VIDEOS)

# Bind filter combos for live filtering
for combo in (date_combo, booth_combo, camera_combo):
    combo.bind("<<ComboboxSelected>>", apply_filters)

# Initial render
apply_filters()

# -----------------------------------------------------------------------------
# Attach hover effects to transport buttons (classic tk.Button)
# -----------------------------------------------------------------------------
if theme:
    # If theme imported, use its color constants
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
