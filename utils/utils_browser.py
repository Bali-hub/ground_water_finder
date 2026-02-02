import streamlit as st
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pyppeteer import launch

# =====================================================
# CONFIG
# =====================================================
APP_DIR = Path(__file__).resolve().parent
CLIENTS_DIR = APP_DIR.parent / "data" / "Dossier_clients"

# détecter automatiquement le dernier dossier créé
subdirs = [d for d in CLIENTS_DIR.iterdir() if d.is_dir()]
if not subdirs:
    st.error(f"Aucun dossier clients trouvé dans {CLIENTS_DIR}")
    st.stop()

LAST_CLIENT_DIR = sorted(subdirs, key=lambda d: d.stat().st_ctime, reverse=True)[0]

BASE_DIR = LAST_CLIENT_DIR / "OUTPUT" / "A_convertir"
CONVERT_DIR = LAST_CLIENT_DIR / "OUTPUT" / "Convertir"

# Chemin FIXE pour Chrome dans Docker (supprime la logique conditionnelle)
CHROME_PATH = "/usr/bin/google-chrome"

BASE_URL = "https://www.gpsvisualizer.com"
DOWNLOAD_SUFFIX = "_e"
MIN_FILE_SIZE = 1000
TIMEOUT = 30
NAV_TIMEOUT = 180_000
BATCH_SIZE = 4        # nombre de fichiers par batch
MAX_RETRIES = 3

# =====================================================
# LOGGER
# =====================================================
def init_logger():
    box = st.empty()
    logs = []

    def log(msg, level="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
        logs.append(f"[{ts}] {icon} {msg}")
        box.text("\n".join(logs))
    return log

log = init_logger()

# =====================================================
# HELPERS
# =====================================================
def verify_directory():
    global BASE_DIR
    BASE_DIR = BASE_DIR.resolve()
    log(f"Vérification dossier : {BASE_DIR}")
    if not BASE_DIR.exists():
        log("Dossier introuvable", "error")
        return False

    gpx_files = [f for f in BASE_DIR.rglob("*.gpx")
                 if f.is_file()
                 and not f.name.lower().endswith(f"{DOWNLOAD_SUFFIX}.gpx")
                 and f.stat().st_size >= MIN_FILE_SIZE]

    if not gpx_files:
        log("Aucun fichier GPX valide trouvé", "warning")
        return False

    log(f"{len(gpx_files)} fichier(s) GPX valide(s) détecté(s)", "success")
    return True

def find_gpx_files():
    files = []
    for f in BASE_DIR.rglob("*.gpx"):
        if f.is_file() and not f.name.lower().endswith(f"{DOWNLOAD_SUFFIX}.gpx") and f.stat().st_size >= MIN_FILE_SIZE:
            files.append(f)
    files = sorted(files, key=lambda f: f.name.lower())
    log(f"{len(files)} fichier(s) à traiter", "info")
    return files

def normalize_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return f"{BASE_URL}/{href}"

def extract_gpx_download_link(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text().lower()
    error_keywords = ["error", "failed", "invalid", "problem", "no data"]
    if any(k in text for k in error_keywords):
        return None
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".gpx") or "download" in a["href"].lower():
            return a["href"]
    return None

# =====================================================
# PYPPETEER DOWNLOAD
# =====================================================
async def download_gpx(gpx_file: Path, output_file: Path):
    browser = None
    try:
        log(f"🌍 Traitement {gpx_file.name}")

        # BLOC MODIFIÉ : arguments critiques pour Docker
        browser = await launch(
            headless=True,
            executablePath=CHROME_PATH,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",  # Argument CRITIQUE ajouté pour Docker
                "--disable-gpu",
                "--disable-extensions"
            ],
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False,
            timeout=NAV_TIMEOUT
        )

        page = await browser.newPage()
        await page.goto(f"{BASE_URL}/elevation", waitUntil="networkidle2", timeout=NAV_TIMEOUT)
        await asyncio.sleep(3)  # laisser la page se stabiliser
        await page.waitForSelector('input[name="uploaded_file_1"]', timeout=60_000)
        await (await page.querySelector('input[name="uploaded_file_1"]')).uploadFile(str(gpx_file))
        await asyncio.sleep(2)
        await (await page.querySelector('input[name="submitted"]')).click()

        try:
            await page.waitForNavigation(timeout=30_000)
        except:
            pass
        await asyncio.sleep(5)

        html = await page.content()
        link = extract_gpx_download_link(html)
        if not link:
            debug = output_file.with_suffix(".html")
            debug.write_text(html, encoding="utf-8")
            log(f"HTML sauvegardé pour debug : {debug}", "warning")
            raise Exception("Lien GPX introuvable")

        download_url = normalize_url(link)
        r = requests.get(download_url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(r.content)

        if output_file.stat().st_size < MIN_FILE_SIZE:
            raise Exception("Fichier trop petit")

        log(f"✅ {output_file.name} téléchargé", "success")
        return True

    finally:
        if browser:
            await browser.close()

# =====================================================
# PROCESS ONE FILE
# =====================================================
async def process_file(gpx_file: Path):
    output_file = CONVERT_DIR / f"{gpx_file.stem}{DOWNLOAD_SUFFIX}.gpx"
    if output_file.exists() and output_file.stat().st_size >= MIN_FILE_SIZE:
        log(f"Déjà traité : {gpx_file.name}", "warning")
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"Tentative {attempt} : {gpx_file.name}")
            return await download_gpx(gpx_file, output_file)
        except Exception as e:
            log(str(e), "error")
            await asyncio.sleep(2 ** attempt)

    log(f"Échec définitif : {gpx_file.name}", "error")
    return False

# =====================================================
# BATCH PROCESSING
# =====================================================
async def process_all_gpx():
    if not verify_directory():
        return

    CONVERT_DIR.mkdir(parents=True, exist_ok=True)
    files = find_gpx_files()
    success = 0
    fail = 0

    # Process files in batches
    for i in range(0, len(files), BATCH_SIZE):
        batch = files[i:i+BATCH_SIZE]
        log(f"📦 Batch {i//BATCH_SIZE + 1} → {len(batch)} fichiers")
        tasks = [process_file(f) for f in batch]
        results = await asyncio.gather(*tasks)
        success += results.count(True)
        fail += results.count(False)

    log("════════════════════════════════")
    log(f"Succès : {success}", "success")
    log(f"Échecs : {fail}", "error" if fail else "info")


def run_streamlit_app():
    st.title("🛰️ Scan landsat – scan")
    st.write("Pyppeteer + Requests + BeautifulSoup (batch + retry stable)")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(process_all_gpx())
    st.success("Traitement terminé ✅")


if __name__ == "__main__":
    run_streamlit_app()