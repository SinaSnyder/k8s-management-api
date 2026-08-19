from django.db import models

class Cluster(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="cluster name")
    address = models.CharField(max_length=255, verbose_name="kubernetes API address")
    token = models.TextField(verbose_name="kubernetes access token")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Namespace(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='namespaces')
    name = models.CharField(max_length=63) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:  
        unique_together = ('cluster', 'name')

    def __str__(self):
        return f"{self.name} ({self.cluster.name})"



class App(models.Model):
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='apps')
    name = models.CharField(max_length=63)
    image = models.CharField(max_length=255)
    replicas = models.IntegerField(default=1)
    cpu_limit = models.CharField(max_length=50, default="500m")     
    memory_limit = models.CharField(max_length=50, default="512Mi")  
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('namespace', 'name')

    def __str__(self):
        return f"{self.name} in {self.namespace.name}"