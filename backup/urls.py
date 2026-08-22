from django.urls import path
from .views import BackupListCreateAPIView, BackupDetailAPIView

urlpatterns = [
    path('backup', BackupListCreateAPIView.as_view(), name='backup-list-create'),
    path('backup/<str:backup_id>', BackupDetailAPIView.as_view(), name='backup-detail'),
]