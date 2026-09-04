from django.urls import path
from .views import BackupListCreateAPIView, BackupDetailAPIView, TestBackupMetricAPIView

urlpatterns = [
    path('backup', BackupListCreateAPIView.as_view(), name='backup-list-create'),
    path('test-metric/', TestBackupMetricAPIView.as_view(), name='test-metric'),
    path('backup/<str:backup_id>', BackupDetailAPIView.as_view(), name='backup-detail'),
]
