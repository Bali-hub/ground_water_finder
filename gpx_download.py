import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# ===============================================================
# 🔧 CONFIG
# ===============================================================
BASE_DIR = Path(__file__).parent / "Notebooks" / "dossier_input"
MAX_CONCURRENT_TASKS = 4
UPLOAD_TIMEOUT = 180_000
DOWNLOAD_TIMEOUT = 120_000

# 🔹 Fichier de progression
PROGRESS_FILE = BASE_DIR / "progress.txt"

# ===============================================================
# 🔹 Gestion progression
# ===============================================================
def load_progress():
    if not PROGRESS_FILE.exists():
        return set()

    with open(PROGRESS_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_progress(file_path):
    with open(PROGRESS_FILE, "a") as f:
        f.write(str(file_path) + "\n")


# ===============================================================
# 🔹 Vérifie si le GPX contient des altitudes
# ===============================================================
def has_elevation(gpx_path):
    try:
        with open(gpx_path, "r", encoding="utf-8") as f:
            return "<ele>" in f.read()

    except Exception as e:
        print(f"⚠️ Lecture impossible {gpx_path}: {e}")
        return False


# ===============================================================
# 🔹 Normalisation Convertir/
#
# Cas gérés :
#
# 1. chunk_1.gpx contient <ele>
#    -> renommé en chunk_1e.gpx
#
# 2. chunk_1e.gpx existe déjà
#    -> suppression de chunk_1.gpx
# ===============================================================
def normalize_convertir(destination_folder, file_path):

    stem = file_path.stem

    normal_file = destination_folder / f"{stem}.gpx"
    elevated_file = destination_folder / f"{stem}e.gpx"

    # Si chunk_1.gpx existe
    if normal_file.exists():

        # Vérifie si altitude déjà présente
        if has_elevation(normal_file):

            # chunk_1e.gpx existe déjà
            if elevated_file.exists():

                print(f"🗑️ Doublon supprimé : {normal_file.name}")
                normal_file.unlink()

            else:
                # Renommage
                normal_file.rename(elevated_file)

                print(
                    f"✏️ Renommé : "
                    f"{normal_file.name} -> {elevated_file.name}"
                )


# ===============================================================
# 🔹 GPSVisualizer - traitement d'un fichier
# ===============================================================
async def process_file(file_path, semaphore):

    destination_folder = file_path.parent.parent / "Convertir"

    os.makedirs(destination_folder, exist_ok=True)

    # 🔹 Normalisation avant traitement
    normalize_convertir(destination_folder, file_path)

    file_name = file_path.name

    # 🔹 Nom final avec "e"
    save_path = destination_folder / f"{file_path.stem}e.gpx"

    # ✅ Skip si déjà traité
    if save_path.exists():
        print(f"⏭️ Déjà traité, skip: {save_path.name}")
        return

    max_retries = 3

    for attempt in range(1, max_retries + 1):

        async with semaphore:

            print(
                f"\n📤 [UPLOAD START] "
                f"{file_name} "
                f"(tentative {attempt})"
            )

            try:

                async with async_playwright() as p:

                    browser = await p.chromium.launch(
                        headless=True
                    )

                    page = await browser.new_page()

                    await page.goto(
                        "https://www.gpsvisualizer.com/elevation",
                        timeout=UPLOAD_TIMEOUT
                    )

                    await page.wait_for_load_state("load")

                    # Cookies
                    try:
                        await page.click(
                            "#ez-accept-all",
                            timeout=5000
                        )

                        print("🍪 Cookies acceptés")

                    except:
                        pass

                    # Upload fichier
                    await page.set_input_files(
                        'input[name="uploaded_file_1"]',
                        str(file_path)
                    )

                    await page.click(
                        'input[name="submitted"]'
                    )

                    print(f"📡 Upload OK {file_name}")

                    # Attente génération
                    print(
                        f"⏳ Attente génération GPX "
                        f"pour {file_name}..."
                    )

                    await page.wait_for_selector(
                        'a[href$=".gpx"]',
                        timeout=DOWNLOAD_TIMEOUT
                    )

                    # Téléchargement
                    async with page.expect_download() as download_info:

                        await page.click(
                            'a[href$=".gpx"]'
                        )

                    download = await download_info.value

                    await download.save_as(str(save_path))

                    print(f"✅ Téléchargé : {save_path}")

                    # Sauvegarde progression
                    save_progress(file_path)

                    await browser.close()

                    return

            except Exception as e:

                print(
                    f"❌ Erreur {file_name} "
                    f"(tentative {attempt}) : {e}"
                )

                if attempt < max_retries:

                    print("🔁 Nouvelle tentative...")

                else:

                    print(
                        f"🚨 Échec définitif : "
                        f"{file_name}"
                    )


# ===============================================================
# 🔹 Parcours des dossiers
# ===============================================================
async def process_all_subdirs():

    semaphore = asyncio.Semaphore(
        MAX_CONCURRENT_TASKS
    )

    # Charger fichiers déjà traités
    processed_files = load_progress()

    subdirs = [
        d for d in BASE_DIR.iterdir()
        if d.is_dir()
    ]

    if not subdirs:

        print(
            f"⚠️ Aucun sous-dossier trouvé "
            f"dans {BASE_DIR}"
        )

        return

    for subdir in subdirs:

        input_gpx_folder = (
            subdir / "OUTPUT" / "A_convertir"
        )

        if not input_gpx_folder.is_dir():

            print(
                f"⚠️ Dossier introuvable : "
                f"{input_gpx_folder}"
            )

            continue

        # Filtrer fichiers déjà traités
        gpx_files = [

            f for f in input_gpx_folder.glob("*.gpx")

            if (
                f.is_file()
                and str(f) not in processed_files
            )
        ]

        if not gpx_files:

            print(
                f"⚠️ Aucun fichier à traiter dans "
                f"{input_gpx_folder}"
            )

            continue

        print(
            f"\n📁 DOSSIER: "
            f"{subdir.name} "
            f"({len(gpx_files)} fichiers)"
        )

        tasks = [
            process_file(f, semaphore)
            for f in gpx_files
        ]

        await asyncio.gather(*tasks)

    print("\n🎯 Tous les sous-dossiers ont été traités.")


# ===============================================================
# 🔹 MAIN
# ===============================================================
if __name__ == "__main__":
    asyncio.run(process_all_subdirs())