# utils/utils_upload_b2.py
from pathlib import Path
import hashlib
import os
import requests
import shutil
import glob
from dotenv import load_dotenv

# =========================
# 1. CHEMINS
# =========================
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"
CLIENTS_DIR = DATA_DIR / "Dossier_clients"

# =========================
# 2. CHARGER LES CLÉS B2
# =========================
B2_KEY_ID = None
B2_APP_KEY = None
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    B2_KEY_ID = os.getenv("keyID")
    B2_APP_KEY = os.getenv("applicationKey")

# =========================
# 3. FONCTION D'UPLOAD AVEC SUPPRESSION
# =========================
def upload_and_delete(zip_path, delete_folder=True):
    """
    Upload un fichier ZIP vers Backblaze B2
    Si delete_folder=True, supprime le dossier client après upload réussi
    """
    if not B2_KEY_ID or not B2_APP_KEY:
        return {'success': False, 'error': 'Clés B2 non configurées'}
    
    try:
        # 1. AUTHENTIFICATION
        auth_resp = requests.get(
            "https://api.backblazeb2.com/b2api/v2/b2_authorize_account",
            auth=(B2_KEY_ID, B2_APP_KEY),
            timeout=30
        )
        if auth_resp.status_code != 200:
            return {'success': False, 'error': f'Auth échouée: {auth_resp.status_code}'}
        auth_data = auth_resp.json()

        # 2. LISTER LES BUCKETS
        buckets_resp = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_list_buckets",
            headers={'Authorization': auth_data['authorizationToken']},
            json={'accountId': auth_data['accountId']},
            timeout=30
        )
        if buckets_resp.status_code != 200:
            return {'success': False, 'error': f'Liste buckets échouée: {buckets_resp.status_code}'}

        buckets = buckets_resp.json()['buckets']
        if not buckets:
            return {'success': False, 'error': 'Aucun bucket trouvé'}

        bucket = buckets[0]
        bucket_id = bucket['bucketId']

        # 3. OBTENIR URL D'UPLOAD
        upload_url_resp = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_get_upload_url",
            headers={'Authorization': auth_data['authorizationToken']},
            json={'bucketId': bucket_id},
            timeout=30
        )
        if upload_url_resp.status_code != 200:
            return {'success': False, 'error': f'URL upload échouée: {upload_url_resp.status_code}'}
        upload_data = upload_url_resp.json()

        # 4. UPLOADER LE ZIP
        file_size = zip_path.stat().st_size
        zip_name = zip_path.name
        sha1 = hashlib.sha1()
        with open(zip_path, 'rb') as f:
            while chunk := f.read(8192):
                sha1.update(chunk)

        with open(zip_path, 'rb') as f:
            upload_resp = requests.post(
                upload_data['uploadUrl'],
                headers={
                    'Authorization': upload_data['authorizationToken'],
                    'X-Bz-File-Name': zip_name,
                    'Content-Type': 'application/zip',
                    'X-Bz-Content-Sha1': sha1.hexdigest()
                },
                data=f,
                timeout=120
            )

        if upload_resp.status_code == 200:
            # Upload réussi, suppression optionnelle
            if delete_folder:
                client_folder = zip_path.parent.parent
                try:
                    shutil.rmtree(client_folder)
                    return {
                        'success': True,
                        'message': f'✅ Upload réussi et dossier supprimé',
                        'file_name': zip_name,
                        'size': file_size
                    }
                except Exception as e:
                    return {
                        'success': True,
                        'message': f'✅ Upload réussi (erreur suppression dossier: {e})',
                        'file_name': zip_name,
                        'size': file_size
                    }
            else:
                return {
                    'success': True,
                    'message': '✅ Upload réussi (dossier conservé)',
                    'file_name': zip_name,
                    'size': file_size
                }
        else:
            return {'success': False, 'error': f'Upload échoué: {upload_resp.status_code}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}

# =========================
# 4. MAIN AUTOMATIQUE
# =========================
def main(delete_folder=True):
    """
    Parcours tous les fichiers ZIP dans CLIENTS_DIR/RENDU et les upload vers B2.
    Retourne une liste de résultats.
    """
    zip_pattern = str(CLIENTS_DIR / "*" / "RENDU" / "*.zip")
    zip_files = [Path(f) for f in glob.glob(zip_pattern, recursive=True)]
    results = []

    if not zip_files:
        print("⚠️ Aucun fichier ZIP trouvé")
        return results

    for zip_file in zip_files:
        print(f"📤 Traitement: {zip_file.parent.parent.name}/{zip_file.name}")
        result = upload_and_delete(zip_file, delete_folder)
        if result.get('success'):
            print(f"✅ {zip_file.name} uploadé et dossier supprimé" if delete_folder else f"✅ {zip_file.name} uploadé")
        else:
            print(f"❌ {zip_file.name} - Erreur: {result.get('error')}")
        results.append(result)

    print("🎉 Tous les traitements sont terminés !")
    return results

# =========================
# 5. POINT D'ENTRÉE
# =========================
if __name__ == "__main__":
    main()
