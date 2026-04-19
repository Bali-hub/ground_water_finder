from pathlib import Path
import os
import hashlib
import requests
import shutil
from dotenv import load_dotenv

# =========================
# ROOT PROJET (ULTRA IMPORTANT)
# =========================
ROOT_DIR = Path(__file__).resolve().parent.parent
SEARCH_ROOT = ROOT_DIR / "data"
ENV_FILE = ROOT_DIR / ".env"
load_dotenv(ENV_FILE)

KEY_ID = os.getenv("B2_KEY_ID")
APP_KEY = os.getenv("B2_APPLICATION_KEY")

if not KEY_ID or not APP_KEY:
    raise SystemExit("❌ .env manquant")

BUCKET_NAME = "ground-water-finder"

# Dossier temporaire pour sauvegarder les cartes avant suppression
TEMP_CARTES = Path("/tmp/cartes_sauvegardees")
TEMP_CARTES.mkdir(parents=True, exist_ok=True)


def auth():
    r = requests.get(
        "https://api.backblazeb2.com/b2api/v2/b2_authorize_account",
        auth=(KEY_ID, APP_KEY),
        timeout=30
    )
    if not r.ok:
        raise SystemExit("❌ Auth échouée")
    return r.json()


def get_bucket(auth_data):
    r = requests.post(
        auth_data["apiUrl"] + "/b2api/v2/b2_list_buckets",
        headers={"Authorization": auth_data["authorizationToken"]},
        json={"accountId": auth_data["accountId"]},
        timeout=30
    )
    for b in r.json().get("buckets", []):
        if b["bucketName"] == BUCKET_NAME:
            return b
    raise SystemExit("❌ Bucket introuvable")


def find_zip_files():
    print("🔍 ROOT réel:", ROOT_DIR.resolve())
    print("🔍 SEARCH_ROOT:", SEARCH_ROOT.resolve())
    zip_files = list(SEARCH_ROOT.rglob("*.zip"))
    # Filtrer les ZIP vides ou temporaires
    zip_files = [
        z for z in zip_files
        if z.stat().st_size > 0
        and "tmp" not in z.name.lower()
        and not z.name.startswith(".")
    ]
    print(f"📦 ZIP trouvés (data seulement): {len(zip_files)}")
    for z in zip_files:
        print("➡️", z)
    return zip_files


def upload_file(file_path, auth_data, bucket):
    """Upload un fichier ZIP. Retourne True si réussi, False sinon."""
    print(f"📤 Upload: {file_path.name}")

    r = requests.post(
        auth_data["apiUrl"] + "/b2api/v2/b2_get_upload_url",
        headers={"Authorization": auth_data["authorizationToken"]},
        json={"bucketId": bucket["bucketId"]},
        timeout=30
    )
    if not r.ok:
        print("❌ get_upload_url échoué")
        return False

    up = r.json()
    upload_url = up["uploadUrl"]
    upload_auth = up["authorizationToken"]

    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha1.update(chunk)

    with open(file_path, "rb") as f:
        r = requests.post(
            upload_url,
            headers={
                "Authorization": upload_auth,
                "X-Bz-File-Name": file_path.name,
                "Content-Type": "application/zip",
                "X-Bz-Content-Sha1": sha1.hexdigest()
            },
            data=f,
            timeout=(30, 600)
        )

    if r.status_code == 200:
        print("✅ OK:", file_path.name)
        return True
    else:
        print(r.text)
        print("❌ Upload échoué")
        return False


def sauvegarder_carte(client_folder):
    """Copie la carte_prospection.png dans /tmp/cartes_sauvegardees"""
    rapport_dir = client_folder / "RENDU" / f"Rapport_{client_folder.name}"
    carte_path = rapport_dir / "carte_prospection.png"
    if carte_path.exists():
        backup_name = f"{client_folder.name}_carte_prospection.png"
        backup_path = TEMP_CARTES / backup_name
        shutil.copy2(carte_path, backup_path)
        print(f"🗺️ Carte sauvegardée : {backup_path}")
    else:
        print(f"⚠️ Aucune carte trouvée pour {client_folder.name}")


def supprimer_dossier_client(client_folder):
    """Supprime le dossier client complet après upload réussi"""
    try:
        shutil.rmtree(client_folder)
        print(f"🗑️ Dossier client supprimé : {client_folder}")
    except Exception as e:
        print(f"❌ Erreur suppression {client_folder} : {e}")

def main():
    auth_data = auth()
    bucket = get_bucket(auth_data)

    zip_files = find_zip_files()
    if not zip_files:
        print("📭 Aucun ZIP trouvé dans tout le projet")
        return

    # Regrouper les ZIP par client
    clients_zips = {}
    for z in zip_files:
        client_folder = z.parent.parent
        clients_zips.setdefault(client_folder, []).append(z)

    for client_folder, zips in clients_zips.items():
        print(f"\n📁 Traitement du client : {client_folder.name}")
        all_success = True
        for z in zips:
            if not upload_file(z, auth_data, bucket):
                all_success = False
                break
        if all_success:
            sauvegarder_carte(client_folder)
            supprimer_dossier_client(client_folder)
        else:
            print(f"⚠️ Client {client_folder.name} : upload échoué, dossier conservé.")

    # ========== MESSAGE DE FIN ==========
    print("\n" + "="*50)
    print("Français : Travaux terminés. Pour plus d'amples détails sur le rapport, écrivez à m2techsecretariat@gmail.com")
    print("English : Work completed. For further details about the report, contact m2techsecretariat@gmail.com")
    print("="*50)

    print("🎉 TERMINÉ")

if __name__ == "__main__":
    main()
