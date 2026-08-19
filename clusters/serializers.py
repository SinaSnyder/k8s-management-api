from rest_framework import serializers
from .models import Cluster, Namespace, App

class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = ['id', 'name', 'address', 'token', 'created_at']
        extra_kwargs = {
            'token': {'write_only': True}
        }


class NamespaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Namespace
        fields = ['id', 'cluster', 'name', 'created_at']


class AppSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ['id', 'namespace', 'name', 'image', 'replicas', 'cpu_limit', 'memory_limit', 'created_at']