import os
import time
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from kubernetes.stream import stream

from .models import Backup
from clusters.models import App
from clusters.k8s_client import get_k8s_client

from metrics import (
    K8S_OPERATIONS_TOTAL,
    K8S_OPERATION_DURATION_SECONDS,
)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_backup_task(self, backup_db_id):
    BACKUPS_IN_PROGRESS.inc()
    start_time = time.time()

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
                    chunk = resp.read_stdout()
                    if isinstance(chunk, str):
                        f.write(chunk.encode('utf-8'))
                    else:
                        f.write(chunk)

        backup.status = 'completed'
        backup.save()

        BACKUP_JOBS_TOTAL.labels(status='completed').inc()
        
        return f"Backup {backup.backup_id} completed successfully."

    except Exception as exc:
        try:
            backup = Backup.objects.get(id=backup_db_id)
            backup.status = 'failed'
            backup.save()
        except Exception:
            pass

        BACKUP_JOBS_TOTAL.labels(status='failed').inc()
        raise self.retry(exc=exc)

    finally:
        BACKUPS_IN_PROGRESS.dec()
        duration = time.time() - start_time
        BACKUP_DURATION_SECONDS.observe(duration)


@shared_task
def cleanup_stale_backups():
    threshold = timezone.now() - timezone.timedelta(hours=24)
    stale_backups = Backup.objects.filter(status='pending', created_at__lt=threshold)
    updated_count = stale_backups.update(status='failed')
    
    if updated_count > 0:
        BACKUP_JOBS_TOTAL.labels(status='failed').inc()
        
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