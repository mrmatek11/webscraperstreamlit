import streamlit as st
import subprocess
import sys
import os
import glob
import zipfile
import threading
import queue
import time
import shutil
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="SNAP — Web Snapshot Tool",
    page_icon="📸",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
}
.stApp {
    background: #0d0d0d;
    color: #e0e0e0;
}
.block-container {
    padding-top: 2rem;
    max-width: 1100px;
}

/* Banner */
.snap-banner {
    background: #111;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #00ff88;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #00ff88;
    white-space: pre;
    line-height: 1.3;
}
.snap-subtitle {
    color: #666;
    font-size: 0.7rem;
    margin-top: 0.3rem;
}

/* Mode cards */
.mode-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.6rem;
    margin-bottom: 1.5rem;
}
.mode-card {
    background: #111;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
}
.mode-card:hover { border-color: #444; }
.mode-card.active { border-color: #00ff88; background: #0d1f15; }
.mode-card .icon { font-size: 1.2rem; margin-bottom: 0.3rem; }
.mode-card .label { font-size: 0.75rem; font-weight: 700; color: #ccc; }
.mode-card .desc { font-size: 0.65rem; color: #666; margin-top: 0.2rem; }

/* Input */
.stTextArea textarea, .stTextInput input {
    background: #111 !important;
    border: 1px solid #2a2a2a !important;
    color: #e0e0e0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    border-radius: 4px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #00ff88 !important;
    box-shadow: 0 0 0 1px #00ff88 !important;
}

/* Buttons */
.stButton > button {
    background: #00ff88 !important;
    color: #000 !important;
    border: none !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    border-radius: 4px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #00cc70 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled {
    background: #2a2a2a !important;
    color: #555 !important;
}

/* Terminal log */
.terminal {
    background: #050505;
    border: 1px solid #1a1a1a;
    border-radius: 4px;
    padding: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #aaa;
    height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
}
.terminal .ok { color: #00ff88; }
.terminal .err { color: #ff4444; }
.terminal .info { color: #44aaff; }
.terminal .warn { color: #ffaa00; }

/* Progress */
.stProgress > div > div > div > div {
    background: #00ff88 !important;
}

/* Download button */
.stDownloadButton > button {
    background: #111 !important;
    color: #00ff88 !important;
    border: 1px solid #00ff88 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    border-radius: 4px !important;
}

/* Radio */
.stRadio > div { flex-direction: row; gap: 1rem; }
.stRadio label { color: #aaa !important; font-size: 0.8rem !important; }

/* Slider */
.stSlider > div > div > div { background: #2a2a2a !important; }
.stSlider > div > div > div > div { background: #00ff88 !important; }

/* Checkbox */
.stCheckbox label { color: #aaa !important; font-size: 0.8rem !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #111;
    border-bottom: 1px solid #2a2a2a;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    color: #666 !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #00ff88 !important;
    border-bottom: 2px solid #00ff88 !important;
}

/* Section headers */
.section-header {
    font-size: 0.7rem;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 0.5rem;
    margin-top: 1rem;
    border-bottom: 1px solid #1a1a1a;
    padding-bottom: 0.3rem;
}

/* Status badge */
.badge {
    display: inline-block;
    padding: 0.1rem 0.5rem;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 700;
    margin-left: 0.5rem;
}
.badge-ok { background: #0d1f15; color: #00ff88; border: 1px solid #00ff88; }
.badge-err { background: #1f0d0d; color: #ff4444; border: 1px solid #ff4444; }
.badge-run { background: #0d0d1f; color: #44aaff; border: 1px solid #44aaff; }

/* Screenshot grid */
.screenshot-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
}

/* Expander */
.streamlit-expanderHeader {
    background: #111 !important;
    border: 1px solid #2a2a2a !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    color: #aaa !important;
}

/* Select */
.stSelectbox > div > div {
    background: #111 !important;
    border-color: #2a2a2a !important;
    color: #e0e0e0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""<div class="snap-banner">  ███████╗███╗   ██╗ █████╗ ██████╗
  ██╔════╝████╗  ██║██╔══██╗██╔══██╗
  ███████╗██╔██╗ ██║███████║██████╔╝
  ╚════██║██║╚██╗██║██╔══██║██╔═══╝
  ███████║██║ ╚████║██║  ██║██║
  ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  <span style="color:#666">web snapshot tool  //  v3</span></div>""", unsafe_allow_html=True)

# ── State init ────────────────────────────────────────────────────────────────
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []
if "running" not in st.session_state:
    st.session_state.running = False
if "result_zip" not in st.session_state:
    st.session_state.result_zip = None
if "screenshots" not in st.session_state:
    st.session_state.screenshots = []
if "done" not in st.session_state:
    st.session_state.done = False

RESULTS_DIR = Path("./results")
RESULTS_DIR.mkdir(exist_ok=True)

# ── Layout ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-header">// URL INPUT</div>', unsafe_allow_html=True)
    urls_raw = st.text_area(
        "",
        placeholder="https://example.com\nhttps://another-site.com\nhttps://third-site.com",
        height=140,
        key="urls_input",
        label_visibility="collapsed"
    )
    st.markdown('<div style="font-size:0.65rem;color:#555;margin-top:-0.5rem;margin-bottom:1rem;">jeden URL per linia</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">// TRYB</div>', unsafe_allow_html=True)
    mode = st.selectbox(
        "",
        options=["screenshots", "full", "crawl", "clean-screenshots", "clean-full", "clean-crawl"],
        format_func=lambda x: {
            "screenshots": "📸  Screenshots only  — tylko screenshoty (szybko)",
            "full":        "📦  Full  — HTML + assets + screenshoty",
            "crawl":       "🕷️  Crawl  — auto-discover stron z sitemap + linków",
            "clean-screenshots": "🧹📸  Clean + Screenshots  — nuke popupów, potem screenshoty",
            "clean-full":        "🧹📦  Clean + Full  — nuke popupów, potem full",
            "clean-crawl":       "🧹🕷️  Clean + Crawl  — nuke popupów, potem crawl",
        }[x],
        label_visibility="collapsed"
    )

    # Crawl options
    if "crawl" in mode:
        st.markdown('<div class="section-header">// OPCJE CRAWL</div>', unsafe_allow_html=True)
        max_pages = st.slider("Max stron do odkrycia", 5, 200, 50, 5)
    else:
        max_pages = 50

    keep_folders = st.checkbox("Zachowaj foldery po spakowaniu", value=False)

    st.markdown("")
    run_btn = st.button(
        "▶  START" if not st.session_state.running else "⏳  TRWA...",
        disabled=st.session_state.running,
        use_container_width=True
    )

with col_right:
    st.markdown('<div class="section-header">// LOG</div>', unsafe_allow_html=True)
    log_placeholder = st.empty()
    status_placeholder = st.empty()
    progress_placeholder = st.empty()

    def render_log():
        lines = st.session_state.log_lines[-120:]
        html_lines = []
        for line in lines:
            l = line.replace("<", "&lt;").replace(">", "&gt;")
            if "[OK]" in l or "✓" in l or "ok" in l.lower():
                cls = "ok"
            elif "[FAIL]" in l or "ERROR" in l or "error" in l.lower() or "❌" in l:
                cls = "err"
            elif "[*]" in l or "─" in l or "mode" in l.lower() or "pages" in l.lower():
                cls = "info"
            elif "[!]" in l or "warn" in l.lower():
                cls = "warn"
            else:
                cls = ""
            html_lines.append(f'<span class="{cls}">{l}</span>')
        log_html = '<div class="terminal">' + "\n".join(html_lines) + '</div>'
        log_placeholder.markdown(log_html, unsafe_allow_html=True)

    render_log()

# ── RUN LOGIC ─────────────────────────────────────────────────────────────────
def stream_process(cmd, log_q):
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=Path(__file__).parent
        )
        for line in proc.stdout:
            log_q.put(line.rstrip())
        proc.wait()
        log_q.put(f"__EXIT__{proc.returncode}")
    except Exception as e:
        log_q.put(f"[ERROR] {e}")
        log_q.put("__EXIT__1")


if run_btn:
    urls = [u.strip() for u in urls_raw.strip().splitlines() if u.strip() and not u.strip().startswith("#")]
    if not urls:
        st.error("Wpisz przynajmniej jeden URL!")
    else:
        # clean results
        st.session_state.log_lines = []
        st.session_state.result_zip = None
        st.session_state.screenshots = []
        st.session_state.done = False
        st.session_state.running = True

        cmd = [
            sys.executable, "snap.py",
            "--mode", mode,
            "--output", str(RESULTS_DIR),
            "--max-pages", str(max_pages),
        ]
        if keep_folders:
            cmd.append("--keep-folders")
        cmd.extend(urls)

        log_q = queue.Queue()
        t = threading.Thread(target=stream_process, args=(cmd, log_q), daemon=True)
        t.start()

        prog = progress_placeholder.progress(0)
        total_urls = len(urls)
        done_count = 0
        start_ts = time.time()

        status_placeholder.markdown(
            '<div style="font-size:0.75rem;color:#44aaff;">▶ running...</div>',
            unsafe_allow_html=True
        )

        exit_code = None
        while exit_code is None:
            new_lines = []
            try:
                while True:
                    line = log_q.get_nowait()
                    if line.startswith("__EXIT__"):
                        exit_code = int(line.replace("__EXIT__", ""))
                    else:
                        new_lines.append(line)
                        # progress heuristic
                        if "[OK]" in line or "[FAIL]" in line:
                            done_count = min(done_count + 1, total_urls)
                            prog.progress(done_count / total_urls)
            except queue.Empty:
                pass

            if new_lines:
                st.session_state.log_lines.extend(new_lines)
                render_log()

            time.sleep(0.3)

        # drain remaining
        remaining = []
        while not log_q.empty():
            try:
                line = log_q.get_nowait()
                if not line.startswith("__EXIT__"):
                    remaining.append(line)
            except queue.Empty:
                break
        st.session_state.log_lines.extend(remaining)

        elapsed = time.time() - start_ts
        st.session_state.running = False
        st.session_state.done = True
        prog.progress(1.0)

        # find latest zip
        zips = sorted(glob.glob(str(RESULTS_DIR / "*.zip")), key=os.path.getmtime)
        if zips:
            st.session_state.result_zip = zips[-1]

        # collect screenshots from zip
        shots = []
        if st.session_state.result_zip:
            try:
                with zipfile.ZipFile(st.session_state.result_zip) as zf:
                    for name in sorted(zf.namelist()):
                        if name.lower().endswith(".png"):
                            shots.append((name, zf.read(name)))
            except Exception:
                pass
        st.session_state.screenshots = shots

        if exit_code == 0:
            status_placeholder.markdown(
                f'<div style="font-size:0.75rem;color:#00ff88;">✓ zakończono  [{elapsed:.1f}s]  —  {len(shots)} screenshotów</div>',
                unsafe_allow_html=True
            )
        else:
            status_placeholder.markdown(
                f'<div style="font-size:0.75rem;color:#ff4444;">✗ błąd (exit {exit_code})  [{elapsed:.1f}s]</div>',
                unsafe_allow_html=True
            )

        render_log()
        st.rerun()

# ── RESULTS ───────────────────────────────────────────────────────────────────
if st.session_state.done:
    st.markdown("---")
    st.markdown('<div class="section-header">// WYNIKI</div>', unsafe_allow_html=True)

    res_col1, res_col2 = st.columns([1, 3])

    with res_col1:
        if st.session_state.result_zip:
            zip_path = st.session_state.result_zip
            zip_name = Path(zip_path).name
            zip_size = os.path.getsize(zip_path) / (1024 * 1024)
            st.markdown(f"""
            <div style="background:#111;border:1px solid #2a2a2a;border-radius:4px;padding:1rem;margin-bottom:1rem;">
                <div style="font-size:0.65rem;color:#555;margin-bottom:0.5rem;">PLIK ZIP</div>
                <div style="font-size:0.8rem;color:#e0e0e0;word-break:break-all;">{zip_name}</div>
                <div style="font-size:0.72rem;color:#666;margin-top:0.3rem;">{zip_size:.2f} MB</div>
            </div>
            """, unsafe_allow_html=True)
            with open(zip_path, "rb") as f:
                st.download_button(
                    f"⬇  Pobierz ZIP",
                    data=f,
                    file_name=zip_name,
                    mime="application/zip",
                    use_container_width=True
                )
        else:
            st.markdown('<div style="color:#ff4444;font-size:0.8rem;">Brak pliku ZIP — sprawdź log</div>', unsafe_allow_html=True)

        shots = st.session_state.screenshots
        st.markdown(f"""
        <div style="background:#111;border:1px solid #2a2a2a;border-radius:4px;padding:1rem;margin-top:0.5rem;">
            <div style="font-size:0.65rem;color:#555;margin-bottom:0.3rem;">SCREENSHOTY</div>
            <div style="font-size:1.5rem;color:#00ff88;font-weight:700;">{len(shots)}</div>
        </div>
        """, unsafe_allow_html=True)

    with res_col2:
        shots = st.session_state.screenshots
        if shots:
            st.markdown('<div style="font-size:0.7rem;color:#555;margin-bottom:0.8rem;">PODGLĄD SCREENSHOTÓW</div>', unsafe_allow_html=True)
            tabs = st.tabs([Path(name).stem[:30] for name, _ in shots[:10]])
            for i, (tab, (name, data)) in enumerate(zip(tabs, shots[:10])):
                with tab:
                    st.image(data, caption=name, use_container_width=True)
                    st.download_button(
                        f"⬇ {Path(name).name}",
                        data=data,
                        file_name=Path(name).name,
                        mime="image/png",
                        key=f"shot_{i}"
                    )
            if len(shots) > 10:
                st.markdown(f'<div style="font-size:0.72rem;color:#555;margin-top:0.5rem;">...i {len(shots)-10} więcej w ZIP</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#555;font-size:0.8rem;">Brak screenshotów w wynikach</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid #1a1a1a;font-size:0.65rem;color:#333;text-align:center;">
snap.py v3  //  streamlit frontend  //  playwright + chromium
</div>
""", unsafe_allow_html=True)
