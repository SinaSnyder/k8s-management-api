from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .tasks import run_backup_task

class TriggerBackupAPIView(APIView):

    def post(self, request):
        task_result = run_backup_task.delay()
        
        return Response({
            "message": "backup request sended and in progress",
            "task_id": task_result.id
        }, status=status.HTTP_202_ACCEPTED)