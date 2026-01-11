# utils/utils_upload_b2.py - AVEC CLÉS INTÉGRÉES
import hashlib
import requests
from pathlib import Path
from datetime import datetime
import os

# ============================================================
# 1. CLÉS BACKBLAZE B2 INTÉGRÉES DANS LE CODE
# ============================================================

keyID = "714db99b1ec3"
applicationKey = "005070550154ade53bdb8c3d8d56512159f4548dbd"

print("\n" + "="*60)
print("🔍 CONFIGURATION B2")
print("="*60)
print(f"keyID: ✅ ({keyID})")
print(f"applicationKey: ✅ ({applicationKey[:8]}...)")
print("="*60)

# ============================================================
# 2. FONCTION POUR TROUVER LE BUCKET
# ============================================================

def get_bucket_info(auth_data):
    """Trouve le premier bucket accessible avec cette clé"""
    try:
        buckets_resp = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_list_buckets",
            headers={"Authorization": auth_data["authorizationToken"]},
            json={"accountId": auth_data["accountId"]},
            timeout=30
        )
        
        if buckets_resp.status_code == 200:
            buckets = buckets_resp.json().get("buckets", [])
            if buckets:
                # Prendre le premier bucket
                bucket = buckets[0]
                return {
                    "success": True,
                    "bucket_id": bucket["bucketId"],
                    "bucket_name": bucket["bucketName"],
                    "all_buckets": [(b["bucketName"], b["bucketId"]) for b in buckets]
                }
            else:
                return {"success": False, "error": "Aucun bucket trouvé"}
        else:
            return {"success": False, "error": f"Erreur liste buckets: {buckets_resp.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================
# 3. FONCTION D'UPLOAD PRINCIPALE
# ============================================================

def upload_zip_to_b2(zip_path: str, custom_name: str = None) -> dict:
    """Upload un ZIP vers B2 - trouve automatiquement le bucket"""
    
    print(f"\n📤 DÉBUT UPLOAD B2")
    print(f"   Fichier: {Path(zip_path).name}")
    
    try:
        zip_file = Path(zip_path)
        
        # Vérifier fichier
        if not zip_file.exists():
            return {"success": False, "error": f"Fichier introuvable: {zip_path}"}
        
        file_size = zip_file.stat().st_size
        if file_size == 0:
            return {"success": False, "error": "Fichier vide"}
        
        print(f"📊 Taille: {file_size:,} octets")
        
        # Nom du fichier
        if custom_name:
            file_name = custom_name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{zip_file.stem}_{timestamp}.zip"
        
        # 1. AUTHENTIFICATION
        print("\n🔐 Authentification...")
        auth_resp = requests.get(
            "https://api.backblazeb2.com/b2api/v2/b2_authorize_account",
            auth=(keyID, applicationKey),
            timeout=30
        )
        
        print(f"   Code réponse: {auth_resp.status_code}")
        
        if auth_resp.status_code != 200:
            return {"success": False, "error": f"Erreur authentification: {auth_resp.status_code}"}
        
        auth = auth_resp.json()
        print("✅ Authentification réussie")
        
        # 2. TROUVER LE BUCKET
        print("\n🔍 Recherche bucket disponible...")
        bucket_info = get_bucket_info(auth)
        
        if not bucket_info["success"]:
            return {"success": False, "error": bucket_info["error"]}
        
        bucket_id = bucket_info["bucket_id"]
        bucket_name = bucket_info["bucket_name"]
        
        print(f"✅ Bucket trouvé: {bucket_name}")
        print(f"📝 Fichier B2: {file_name}")
        
        # 3. URL D'UPLOAD
        print("\n🔗 Obtention URL d'upload...")
        upload_url_resp = requests.post(
            f"{auth['apiUrl']}/b2api/v2/b2_get_upload_url",
            headers={"Authorization": auth["authorizationToken"]},
            json={"bucketId": bucket_id},
            timeout=30
        )
        
        if upload_url_resp.status_code != 200:
            return {"success": False, "error": f"Erreur URL upload: {upload_url_resp.status_code}"}
        
        upload_data = upload_url_resp.json()
        print("✅ URL d'upload obtenue")
        
        # 4. CALCUL HASH
        print("\n🔢 Calcul hash SHA1...")
        sha1 = hashlib.sha1()
        with open(zip_file, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha1.update(chunk)
        
        file_hash = sha1.hexdigest()
        
        # 5. UPLOAD
        print("\n📤 Upload en cours...")
        start_time = datetime.now()
        
        headers = {
            "Authorization": upload_data["authorizationToken"],
            "X-Bz-File-Name": file_name,
            "Content-Type": "application/zip",
            "X-Bz-Content-Sha1": file_hash,
            "X-Bz-Info-Uploaded-By": "GroundWaterFinder",
            "X-Bz-Info-Timestamp": datetime.now().isoformat()
        }
        
        with open(zip_file, "rb") as f:
            upload_resp = requests.post(
                upload_data["uploadUrl"],
                headers=headers,
                data=f,
                timeout=300
            )
        
        print(f"   Code réponse: {upload_resp.status_code}")
        
        if upload_resp.status_code != 200:
            return {"success": False, "error": f"Échec upload: {upload_resp.status_code}"}
        
        result = upload_resp.json()
        duration = (datetime.now() - start_time).total_seconds()
        
        # Générer l'URL
        download_url = f"{auth['downloadUrl']}/file/{bucket_name}/{file_name}"
        
        print(f"\n🎉 UPLOAD RÉUSSI!")
        print(f"📁 Fichier: {file_name}")
        print(f"📦 Bucket: {bucket_name}")
        print(f"📊 Taille: {file_size/1024/1024:.2f} MB")
        print(f"⏱️  Durée: {duration:.1f}s")
        print(f"🔗 URL: {download_url}")
        
        return {
            "success": True,
            "file_name": file_name,
            "file_size": file_size,
            "file_id": result.get('fileId'),
            "download_url": download_url,
            "duration_seconds": round(duration, 1),
            "bucket": bucket_name,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sha1": file_hash
        }
        
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        return {"success": False, "error": str(e)}

# ============================================================
# 4. FONCTION DE TEST
# ============================================================

def test_b2_connection():
    """Teste la connexion B2"""
    
    print("\n" + "="*60)
    print("🔧 TEST CONNEXION B2")
    print("="*60)
    
    try:
        # Test auth
        print("\n🔐 Authentification...")
        auth_resp = requests.get(
            "https://api.backblazeb2.com/b2api/v2/b2_authorize_account",
            auth=(keyID, applicationKey),
            timeout=30
        )
        
        print(f"   Code réponse: {auth_resp.status_code}")
        
        if auth_resp.status_code != 200:
            print(f"❌ Authentification échouée")
            return False
        
        auth = auth_resp.json()
        print("✅ Authentification réussie")
        
        # Test buckets
        print("\n🔍 Liste des buckets...")
        bucket_info = get_bucket_info(auth)
        
        if bucket_info["success"]:
            print(f"✅ {len(bucket_info.get('all_buckets', []))} bucket(s) trouvé(s)")
            for i, (name, bid) in enumerate(bucket_info.get('all_buckets', []), 1):
                print(f"   {i}. {name} (ID: {bid[:10]}...)")
            print("\n🎉 TEST RÉUSSI!")
            return True
        else:
            print(f"❌ {bucket_info.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        return False

# ============================================================
# 5. EXPORT
# ============================================================

__all__ = ['upload_zip_to_b2', 'test_b2_connection']

# ============================================================
# 6. TEST STANDALONE
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 TEST utils_upload_b2.py")
    print("="*60)
    
    if test_b2_connection():
        print("\n✅ Connexion B2 OK")
        
        # Test upload si fichier existe
        import os
        test_file = "test.zip"
        if os.path.exists(test_file):
            print(f"\n📤 Test upload: {test_file}")
            result = upload_zip_to_b2(test_file)
            if result["success"]:
                print(f"✅ Upload réussi!")
                print(f"🔗 {result['download_url']}")
            else:
                print(f"❌ Échec: {result.get('error')}")
        else:
            print(f"\nℹ️  Créez '{test_file}' pour tester l'upload")
    else:
        print("\n❌ Connexion B2 échouée")