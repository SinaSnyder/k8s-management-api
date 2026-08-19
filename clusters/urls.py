from django.urls import path
from .views import (
    ClusterListCreateAPIView, 
    NamespaceListCreateAPIView, 
    NamespaceDetailAPIView,
    AppListCreateAPIView,
    AppDetailAPIView
)

urlpatterns = [
    path('cluster', ClusterListCreateAPIView.as_view(), name='cluster-list-create'),
    path('namespace', NamespaceListCreateAPIView.as_view(), name='namespace-list-create'),
    path('namespace/<int:pk>', NamespaceDetailAPIView.as_view(), name='namespace-detail'),
    path('app', AppListCreateAPIView.as_view(), name='app-list-create'),
    path('app/<int:pk>', AppDetailAPIView.as_view(), name='app-detail'),
]