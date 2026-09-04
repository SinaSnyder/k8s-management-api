from prometheus_client import Counter, Histogram, Gauge

K8S_OPERATIONS_TOTAL = Counter(
    'hamamooz_kubernetes_operations_total',
    'How many Kubernetes operations ended in each outcome?',
    ['resource', 'operation', 'outcome']
)

K8S_OPERATION_DURATION_SECONDS = Histogram(
    'hamamooz_kubernetes_operation_duration_seconds',
    'How long did each Kubernetes operation take?',
    ['resource', 'operation']
)

BACKUP_JOBS_TOTAL = Counter(
    'hamamooz_backup_jobs_total',
    'How many backup jobs reached each terminal outcome?',
    ['outcome']
)

BACKUP_DURATION_SECONDS = Histogram(
    'hamamooz_backup_duration_seconds',
    'How long did backup work take?'
)

BACKUPS_IN_PROGRESS = Gauge(
    'hamamooz_backups_in_progress',
    'How many backups are running now?'
)
