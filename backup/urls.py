from django.urls import path
from .views import TriggerBackupAPIView

urlpatterns = [
    path('backup', TriggerBackupAPIView.as_view(), name='trigger-backup'),
]