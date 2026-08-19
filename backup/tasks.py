from celery import shared_task
import time

@shared_task
def run_backup_task():
    print("---backup in progress---")
    time.sleep(5)  
    print("---backup completed successfully---")
    return "Backup completed successfully"