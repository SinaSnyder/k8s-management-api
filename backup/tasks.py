import os
import tarfile
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from .models import Backup
from clusters.models import App
from clusters.k8s_client import get_k8s_client
from kubernetes.stream import stream
from django.conf import settings

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_backup_task(self, backup_db_id):
    try:
        backup = Backup.objects.get(id=backup_db_id)
        backup.status = 'running'
        backup.save()

        app = backup.app
        namespace = app.namespace.name
        cluster = app.namespace.cluster

        k8s_api = get_k8s_client(cluster)
        pods = k8s_api.list_namespaced_pod(namespace=namespace, label_selector=f"app={app.name}")
        
        if not pods.items:
            raise Exception("No active pod found for this app.")

        pod_name = pods.items[0].metadata.name

        today_str = datetime.now().strftime('%Y-%m-%d')
        backup_dir = os.path.join(settings.BASE_DIR, 'backups', str(app.id), today_str)
        os.makedirs(backup_dir, exist_ok=True)
        file_path = os.path.join(backup_dir, f"{backup.backup_id}.tar.gz")

        exec_command = ['tar', 'cfz', '-', backup.source_path]
        resp = stream(
            k8s_api.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=exec_command,
            stderr=True, stdin=False,
            stdout=True, tty=False,
            _preload_content=False
        )

        with open(file_path, 'wb') as f:
            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    f.write(resp.read_stdout().encode('utf-8'))

        backup.status = 'completed'
        backup.save()
        return f"Backup {backup.backup_id} completed successfully."

    except Exception as exc:
        backup = Backup.objects.get(id=backup_db_id)
        backup.status = 'failed'
        backup.save()
        raise self.retry(exc=exc)


@shared_task
def cleanup_stale_backups():
    threshold = timezone.now() - timezone.timedelta(hours=24)
    stale_backups = Backup.objects.filter(status='pending', created_at__lt=threshold)
    updated_count = stale_backups.update(status='failed')
    return f"Cleaned up {updated_count} stale backup(s)."


@shared_task
def create_scheduled_backup_job(app_id, source_path, schedule):
    try:
        app_obj = App.objects.get(pk=app_id)
        backup = Backup.objects.create(
            app=app_obj, 
            source_path=source_path, 
            schedule=schedule
        )
        execute_backup_task.delay(backup.id)
        return f"Scheduled backup triggered: {backup.backup_id}"
    except Exception as e:
        raise Exception(f"Failed to trigger scheduled backup for app {app_id}: {str(e)}")