# orchestrator.py
import uuid
import docker
from docker.errors import NotFound, DockerException
import os
import time

# Noms fixes des conteneurs
WORKER_CONTAINER_NAME = "gwf_worker"
MAIN_CONTAINER_NAME = "ground_water_finder"

def get_docker_client():
    """Retourne un client Docker avec un timeout long."""
    from docker import from_env
    return from_env(timeout=120)

def arreter_et_supprimer_conteneur():
    """Arrête et supprime le conteneur worker s'il existe."""
    try:
        client = get_docker_client()
        container = client.containers.get(WORKER_CONTAINER_NAME)
        if container.status == 'running':
            container.stop()
            print(f"Conteneur {WORKER_CONTAINER_NAME} arrêté.")
        container.remove()
        print(f"Conteneur {WORKER_CONTAINER_NAME} supprimé.")
        return True
    except NotFound:
        print(f"Aucun conteneur nommé {WORKER_CONTAINER_NAME} trouvé.")
        return True
    except DockerException as e:
        print(f"Erreur Docker lors de la suppression : {e}")
        return False

def run_pipeline(image_name="gwf", timeout=600):
    """
    Lance un conteneur worker (exécute une tâche courte).
    Ici, on lance un simple test (sleep) pour éviter le blocage.
    Adaptez la commande à vos besoins réels.
    """
    arreter_et_supprimer_conteneur()
    client = get_docker_client()
    container = client.containers.run(
        image_name,
        name=WORKER_CONTAINER_NAME,
        detach=True,
        remove=False,
        command=["sleep", "2"]   # ⚠️ Remplacez par votre vraie commande
    )
    try:
        result = container.wait(timeout=timeout)
        logs = container.logs().decode("utf-8")
        if result.get("StatusCode", 1) != 0:
            raise Exception(f"Erreur dans le conteneur worker:\n{logs}")
        return logs
    finally:
        try:
            container.remove(force=True)
        except Exception as e:
            print(f"Erreur suppression worker: {e}")

def relancer_conteneur_principal():
    """
    Lance un conteneur helper (docker:cli) qui arrête/supprime le conteneur principal
    puis le recrée avec les mêmes paramètres.
    Plus aucun montage de dossier projet, pour éviter les erreurs de chemin Windows.
    """
    client = get_docker_client()

    # Chemin du projet sur l'HÔTE (à modifier selon votre configuration)
    host_project_path = os.environ.get("HOST_PROJECT_PATH", "C:/Users/User/Documents/ground_water_finder")

    # Commande exécutée dans le helper (le daemon Docker hôte comprendra le chemin Windows)
    cmd = (
        f"docker stop {MAIN_CONTAINER_NAME} || true && "
        f"docker rm {MAIN_CONTAINER_NAME} || true && "
        f"docker run -d -p 10000:10000 "
        f"-v {host_project_path}/data:/app/data "
        f"-v /var/run/docker.sock:/var/run/docker.sock "
        f"--env-file {host_project_path}/.env "
        f"--name {MAIN_CONTAINER_NAME} "
        f"gwf:latest"
    )

    try:
        container = client.containers.run(
            "docker:cli",
            command=["sh", "-c", cmd],
            detach=True,
            remove=True,
            volumes={
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}
                # Plus de montage du projet : le helper n'a pas besoin d'y accéder
            }
        )
        result = container.wait(timeout=30)
        logs = container.logs().decode("utf-8")
        print("Helper logs:", logs)
        return result["StatusCode"] == 0
    except Exception as e:
        print(f"Erreur lors de la relance: {e}")
        return False