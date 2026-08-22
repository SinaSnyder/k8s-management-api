from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from .models import Backup
from clusters.models import App
from .tasks import execute_backup_task

class BackupListCreateAPIView(APIView):

    def get(self, request):
        app_id = request.query_params.get('app_id')
        if not app_id:
            return Response({"error": "app_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        backups = Backup.objects.filter(app_id=app_id)
        data = [{"backup_id": b.backup_id, "status": b.status} for b in backups]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        app_id = request.data.get('app_id')
        source_path = request.data.get('source_path')
        schedule = request.data.get('schedule') 

        if not app_id or not source_path:
            return Response({"error": "app_id and source_path fields is required"}, status=status.HTTP_400_BAD_REQUEST)

        app_obj = get_object_or_404(App, pk=app_id)

        if schedule:
            try:
                cron_parts = schedule.split() 
                crontab, _ = CrontabSchedule.objects.get_or_create(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day_of_month=cron_parts[2],
                    month_of_year=cron_parts[3],
                    day_of_week=cron_parts[4],
                )
                
                PeriodicTask.objects.create(
                    crontab=crontab,
                    name=f"periodic_backup_app_{app_id}_{schedule}",
                    task='backup.tasks.create_scheduled_backup_job',
                    args=json.dumps([app_id, source_path, schedule])
                )
                return Response({"message": "periodic backup successfully set"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": f"invalid corn format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        backup = Backup.objects.create(app=app_obj, source_path=source_path)
        execute_backup_task.delay(backup.id) 

        return Response({
            "backup_id": backup.backup_id,
            "status": backup.status
        }, status=status.HTTP_202_ACCEPTED)


class BackupDetailAPIView(APIView):

    def get(self, request, backup_id):
        backup = get_object_or_404(Backup, backup_id=backup_id)
        return Response({
            "backup_id": backup.backup_id,
            "app_id": backup.app.id,
            "status": backup.status
        }, status=status.HTTP_200_OK)