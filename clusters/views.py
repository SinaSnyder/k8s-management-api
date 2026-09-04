import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from kubernetes.client.rest import ApiException
from kubernetes import client
from kubernetes.client import V1Deployment, V1ObjectMeta, V1DeploymentSpec, V1PodTemplateSpec, V1PodSpec, V1Container, V1ResourceRequirements

from .models import App, Cluster, Namespace
from .serializers import AppSerializer, ClusterSerializer, NamespaceSerializer
from .k8s_client import get_k8s_client, get_k8s_apps_api
from metrics import K8S_OPERATIONS_TOTAL, K8S_OPERATION_DURATION_SECONDS


class ClusterListCreateAPIView(APIView):
    def get(self, request):
        start_time = time.time()
        try:
            clusters = Cluster.objects.all().order_by('-created_at')
            serializer = ClusterSerializer(clusters, many=True)
            K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='list', outcome='success').inc()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='list', outcome='error').inc()
            raise
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='cluster', operation='list').observe(time.time() - start_time)

    def post(self, request):
        start_time = time.time()
        serializer = ClusterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='create', outcome='success').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='cluster', operation='create').observe(time.time() - start_time)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='create', outcome='error').inc()
        K8S_OPERATION_DURATION_SECONDS.labels(resource='cluster', operation='create').observe(time.time() - start_time)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NamespaceListCreateAPIView(APIView):

    def get(self, request):
        start_time = time.time()
        cluster_id = request.query_params.get('cluster_id')
        if not cluster_id:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='list', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='list').observe(time.time() - start_time)
            return Response({"error": "cluster_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cluster = get_object_or_404(Cluster, pk=cluster_id)
            namespaces = Namespace.objects.filter(cluster=cluster)
            serializer = NamespaceSerializer(namespaces, many=True)
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='list', outcome='success').inc()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='list', outcome='error').inc()
            raise
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='list').observe(time.time() - start_time)

    def post(self, request):
        start_time = time.time()
        cluster_id = request.data.get('cluster_id')
        ns_name = request.data.get('name')

        if not cluster_id or not ns_name:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)
            return Response({"error": "sending cluster_id and name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cluster = Cluster.objects.get(pk=cluster_id)
        except Cluster.DoesNotExist:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)
            return Response({"error": "Cluster not found"}, status=status.HTTP_404_NOT_FOUND)

        if Namespace.objects.filter(cluster=cluster, name=ns_name).exists():
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)
            return Response({"error": "this namespace is already in database"}, status=status.HTTP_409_CONFLICT)

        try:
            k8s_api = get_k8s_client(cluster)
            body = client.V1Namespace(metadata=client.V1ObjectMeta(name=ns_name))
            k8s_api.create_namespace(body=body)
            
            ns_obj = Namespace.objects.create(cluster=cluster, name=ns_name)
            serializer = NamespaceSerializer(ns_obj)
            
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='success').inc()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ApiException as e:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            if e.status == 409:
                return Response({"error": "this namespace is already in kubernetes"}, status=status.HTTP_409_CONFLICT)
            elif e.status in [401, 403]:
                return Response({"error": "kubernetes access error or invalid token"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": f"error in connecting to k8s: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            return Response({"error": f"kubernetes is unavailable or address is invalid: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
            
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)


class NamespaceDetailAPIView(APIView):

    def delete(self, request, pk):
        start_time = time.time()
        try:
            ns_obj = Namespace.objects.get(pk=pk)
        except Namespace.DoesNotExist:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
            return Response({"error": "Namespace not found"}, status=status.HTTP_404_NOT_FOUND)

        cluster = ns_obj.cluster

        try:
            k8s_api = get_k8s_client(cluster)
            k8s_api.delete_namespace(name=ns_obj.name)
        except ApiException as e:
            if e.status != 404:
                K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='error').inc()
                K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
                return Response({"error": f"error in deleting: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
            return Response({"error": "could not connect to kubernetes"}, status=status.HTTP_502_BAD_GATEWAY)

        ns_obj.delete()
        K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='success').inc()
        K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
        return Response({"message": "Namespace deleted successfully"}, status=status.HTTP_200_OK)


class AppListCreateAPIView(APIView):

    def get(self, request):
        start_time = time.time()
        namespace_id = request.query_params.get('namespace_id')
        if not namespace_id:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='list', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='list').observe(time.time() - start_time)
            return Response({"error": "namespace is required"}, status=status.HTTP_400_BAD_REQUEST)

        namespace_obj = get_object_or_404(Namespace, pk=namespace_id)
        cluster = namespace_obj.cluster
        apps = App.objects.filter(namespace=namespace_obj)

        try:
            k8s_core_api = get_k8s_client(cluster)
            result = []
            for app in apps:
                app_data = AppSerializer(app).data
                try:
                    pods = k8s_core_api.list_namespaced_pod(
                        namespace=namespace_obj.name,
                        label_selector=f"app={app.name}"
                    )
                    
                    pod_statuses = []
                    all_ready = True if len(pods.items) > 0 else False
                    
                    for pod in pods.items:
                        is_ready = False
                        if pod.status.container_statuses:
                            is_ready = all(c.ready for c in pod.status.container_statuses)
                        
                        if not is_ready:
                            all_ready = False

                        pod_statuses.append({
                            "pod_name": pod.metadata.name,
                            "phase": pod.status.phase,
                            "ready": is_ready
                        })

                    app_data['status'] = {
                        "ready": all_ready,
                        "running_pods": len(pod_statuses),
                        "pods": pod_statuses
                    }
                except Exception as e:
                    app_data['status'] = {"error": f"unable to get pod status: {str(e)}"}

                result.append(app_data)

            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='list', outcome='success').inc()
            return Response(result, status=status.HTTP_200_OK)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='list', outcome='error').inc()
            raise
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='list').observe(time.time() - start_time)

    def post(self, request):
        start_time = time.time()
        serializer = AppSerializer(data=request.data)
        if not serializer.is_valid():
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='create').observe(time.time() - start_time)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        namespace_obj = serializer.validated_data['namespace']
        cluster = namespace_obj.cluster
        app_name = serializer.validated_data['name']
        image = serializer.validated_data['image']
        replicas = serializer.validated_data.get('replicas', 1)
        cpu_limit = serializer.validated_data.get('cpu_limit', '500m')
        memory_limit = serializer.validated_data.get('memory_limit', '512Mi')

        if App.objects.filter(namespace=namespace_obj, name=app_name).exists():
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='create').observe(time.time() - start_time)
            return Response({"error": "this app already in this namespace"}, status=status.HTTP_409_CONFLICT)

        try:
            k8s_apps_api = get_k8s_apps_api(cluster)
            
            container = V1Container(
                name=app_name,
                image=image,
                resources=V1ResourceRequirements(
                    limits={"cpu": cpu_limit, "memory": memory_limit},
                    requests={"cpu": "100m", "memory": "128Mi"}
                )
            )
            
            template = V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": app_name}),
                spec=V1PodSpec(containers=[container])
            )
            
            spec = V1DeploymentSpec(
                replicas=replicas,
                template=template,
                selector={"matchLabels": {"app": app_name}}
            )
            
            deployment = V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=V1ObjectMeta(name=app_name),
                spec=spec
            )

            k8s_apps_api.create_namespaced_deployment(
                namespace=namespace_obj.name,
                body=deployment
            )
            
            app_obj = serializer.save()
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='success').inc()
            return Response(AppSerializer(app_obj).data, status=status.HTTP_201_CREATED)

        except ApiException as e:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            return Response({"error": f"kubernetes error: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            return Response({"error": f"could not connect to kubernetes: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='create').observe(time.time() - start_time)


class AppDetailAPIView(APIView):

    def put(self, request, pk):
        start_time = time.time()
        app_obj = get_object_or_404(App, pk=pk)
        namespace_obj = app_obj.namespace
        cluster = namespace_obj.cluster

        serializer = AppSerializer(app_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='update', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='update').observe(time.time() - start_time)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            k8s_apps_api = get_k8s_apps_api(cluster)
            
            new_replicas = request.data.get('replicas', app_obj.replicas)
            new_cpu = request.data.get('cpu_limit', app_obj.cpu_limit)
            new_memory = request.data.get('memory_limit', app_obj.memory_limit)
            new_image = request.data.get('image', app_obj.image)

            patch_body = {
                "spec": {
                    "replicas": int(new_replicas),
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": app_obj.name,
                                "image": new_image,
                                "resources": {
                                    "limits": {"cpu": new_cpu, "memory": new_memory}
                                }
                            }]
                        }
                    }
                }
            }

            k8s_apps_api.patch_namespaced_deployment(
                name=app_obj.name,
                namespace=namespace_obj.name,
                body=patch_body
            )
            
            updated_app = serializer.save()
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='update', outcome='success').inc()
            return Response(AppSerializer(updated_app).data, status=status.HTTP_200_OK)

        except ApiException as e:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='update', outcome='error').inc()
            return Response({"error": f"error updating kubernetes: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='update').observe(time.time() - start_time)

    def delete(self, request, pk):
        start_time = time.time()
        app_obj = get_object_or_404(App, pk=pk)
        namespace_obj = app_obj.namespace
        cluster = namespace_obj.cluster

        try:
            k8s_apps_api = get_k8s_apps_api(cluster)
            k8s_apps_api.delete_namespaced_deployment(
                name=app_obj.name,
                namespace=namespace_obj.name
            )
        except ApiException as e:
            if e.status != 404:
                K8S_OPERATIONS_TOTAL.labels(resource='app', operation='delete', outcome='error').inc()
                K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='delete').observe(time.time() - start_time)
                return Response({"error": f"error deleting from kubernetes: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)

        app_obj.delete()
        K8S_OPERATIONS_TOTAL.labels(resource='app', operation='delete', outcome='success').inc()
        K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='delete').observe(time.time() - start_time)
        return Response({"message": "app deleted successfully"}, status=status.HTTP_200_OK)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from kubernetes.client.rest import ApiException
from kubernetes import client
from kubernetes.client import V1Deployment, V1ObjectMeta, V1DeploymentSpec, V1PodTemplateSpec, V1PodSpec, V1Container, V1ResourceRequirements

from .models import App, Cluster, Namespace
from .serializers import AppSerializer, ClusterSerializer, NamespaceSerializer
from .k8s_client import get_k8s_client, get_k8s_apps_api
from metrics import K8S_OPERATIONS_TOTAL, K8S_OPERATION_DURATION_SECONDS


class ClusterListCreateAPIView(APIView):
    def get(self, request):
        start_time = time.time()
        try:
            clusters = Cluster.objects.all().order_by('-created_at')
            serializer = ClusterSerializer(clusters, many=True)
            K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='list', outcome='success').inc()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='list', outcome='error').inc()
            raise
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='cluster', operation='list').observe(time.time() - start_time)

    def post(self, request):
        start_time = time.time()
        serializer = ClusterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='create', outcome='success').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='cluster', operation='create').observe(time.time() - start_time)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        K8S_OPERATIONS_TOTAL.labels(resource='cluster', operation='create', outcome='error').inc()
        K8S_OPERATION_DURATION_SECONDS.labels(resource='cluster', operation='create').observe(time.time() - start_time)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NamespaceListCreateAPIView(APIView):

    def get(self, request):
        start_time = time.time()
        cluster_id = request.query_params.get('cluster_id')
        if not cluster_id:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='list', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='list').observe(time.time() - start_time)
            return Response({"error": "cluster_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cluster = get_object_or_404(Cluster, pk=cluster_id)
            namespaces = Namespace.objects.filter(cluster=cluster)
            serializer = NamespaceSerializer(namespaces, many=True)
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='list', outcome='success').inc()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='list', outcome='error').inc()
            raise
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='list').observe(time.time() - start_time)

    def post(self, request):
        start_time = time.time()
        cluster_id = request.data.get('cluster_id')
        ns_name = request.data.get('name')

        if not cluster_id or not ns_name:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)
            return Response({"error": "sending cluster_id and name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cluster = Cluster.objects.get(pk=cluster_id)
        except Cluster.DoesNotExist:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)
            return Response({"error": "Cluster not found"}, status=status.HTTP_404_NOT_FOUND)

        if Namespace.objects.filter(cluster=cluster, name=ns_name).exists():
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)
            return Response({"error": "this namespace is already in database"}, status=status.HTTP_409_CONFLICT)

        try:
            k8s_api = get_k8s_client(cluster)
            body = client.V1Namespace(metadata=client.V1ObjectMeta(name=ns_name))
            k8s_api.create_namespace(body=body)
            
            ns_obj = Namespace.objects.create(cluster=cluster, name=ns_name)
            serializer = NamespaceSerializer(ns_obj)
            
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='success').inc()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ApiException as e:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            if e.status == 409:
                return Response({"error": "this namespace is already in kubernetes"}, status=status.HTTP_409_CONFLICT)
            elif e.status in [401, 403]:
                return Response({"error": "kubernetes access error or invalid token"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": f"error in connecting to k8s: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='create', outcome='error').inc()
            return Response({"error": f"kubernetes is unavailable or address is invalid: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
            
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='create').observe(time.time() - start_time)


class NamespaceDetailAPIView(APIView):

    def delete(self, request, pk):
        start_time = time.time()
        try:
            ns_obj = Namespace.objects.get(pk=pk)
        except Namespace.DoesNotExist:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
            return Response({"error": "Namespace not found"}, status=status.HTTP_404_NOT_FOUND)

        cluster = ns_obj.cluster

        try:
            k8s_api = get_k8s_client(cluster)
            k8s_api.delete_namespace(name=ns_obj.name)
        except ApiException as e:
            if e.status != 404:
                K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='error').inc()
                K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
                return Response({"error": f"error in deleting: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
            return Response({"error": "could not connect to kubernetes"}, status=status.HTTP_502_BAD_GATEWAY)

        ns_obj.delete()
        K8S_OPERATIONS_TOTAL.labels(resource='namespace', operation='delete', outcome='success').inc()
        K8S_OPERATION_DURATION_SECONDS.labels(resource='namespace', operation='delete').observe(time.time() - start_time)
        return Response({"message": "Namespace deleted successfully"}, status=status.HTTP_200_OK)


class AppListCreateAPIView(APIView):

    def get(self, request):
        start_time = time.time()
        namespace_id = request.query_params.get('namespace_id')
        if not namespace_id:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='list', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='list').observe(time.time() - start_time)
            return Response({"error": "namespace is required"}, status=status.HTTP_400_BAD_REQUEST)

        namespace_obj = get_object_or_404(Namespace, pk=namespace_id)
        cluster = namespace_obj.cluster
        apps = App.objects.filter(namespace=namespace_obj)

        try:
            k8s_core_api = get_k8s_client(cluster)
            result = []
            for app in apps:
                app_data = AppSerializer(app).data
                try:
                    pods = k8s_core_api.list_namespaced_pod(
                        namespace=namespace_obj.name,
                        label_selector=f"app={app.name}"
                    )
                    
                    pod_statuses = []
                    all_ready = True if len(pods.items) > 0 else False
                    
                    for pod in pods.items:
                        is_ready = False
                        if pod.status.container_statuses:
                            is_ready = all(c.ready for c in pod.status.container_statuses)
                        
                        if not is_ready:
                            all_ready = False

                        pod_statuses.append({
                            "pod_name": pod.metadata.name,
                            "phase": pod.status.phase,
                            "ready": is_ready
                        })

                    app_data['status'] = {
                        "ready": all_ready,
                        "running_pods": len(pod_statuses),
                        "pods": pod_statuses
                    }
                except Exception as e:
                    app_data['status'] = {"error": f"unable to get pod status: {str(e)}"}

                result.append(app_data)

            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='list', outcome='success').inc()
            return Response(result, status=status.HTTP_200_OK)
        except Exception:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='list', outcome='error').inc()
            raise
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='list').observe(time.time() - start_time)

    def post(self, request):
        start_time = time.time()
        serializer = AppSerializer(data=request.data)
        if not serializer.is_valid():
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='create').observe(time.time() - start_time)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        namespace_obj = serializer.validated_data['namespace']
        cluster = namespace_obj.cluster
        app_name = serializer.validated_data['name']
        image = serializer.validated_data['image']
        replicas = serializer.validated_data.get('replicas', 1)
        cpu_limit = serializer.validated_data.get('cpu_limit', '500m')
        memory_limit = serializer.validated_data.get('memory_limit', '512Mi')

        if App.objects.filter(namespace=namespace_obj, name=app_name).exists():
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='create').observe(time.time() - start_time)
            return Response({"error": "this app already in this namespace"}, status=status.HTTP_409_CONFLICT)

        try:
            k8s_apps_api = get_k8s_apps_api(cluster)
            
            container = V1Container(
                name=app_name,
                image=image,
                resources=V1ResourceRequirements(
                    limits={"cpu": cpu_limit, "memory": memory_limit},
                    requests={"cpu": "100m", "memory": "128Mi"}
                )
            )
            
            template = V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": app_name}),
                spec=V1PodSpec(containers=[container])
            )
            
            spec = V1DeploymentSpec(
                replicas=replicas,
                template=template,
                selector={"matchLabels": {"app": app_name}}
            )
            
            deployment = V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=V1ObjectMeta(name=app_name),
                spec=spec
            )

            k8s_apps_api.create_namespaced_deployment(
                namespace=namespace_obj.name,
                body=deployment
            )
            
            app_obj = serializer.save()
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='success').inc()
            return Response(AppSerializer(app_obj).data, status=status.HTTP_201_CREATED)

        except ApiException as e:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            return Response({"error": f"kubernetes error: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='create', outcome='error').inc()
            return Response({"error": f"could not connect to kubernetes: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='create').observe(time.time() - start_time)


class AppDetailAPIView(APIView):

    def put(self, request, pk):
        start_time = time.time()
        app_obj = get_object_or_404(App, pk=pk)
        namespace_obj = app_obj.namespace
        cluster = namespace_obj.cluster

        serializer = AppSerializer(app_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='update', outcome='error').inc()
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='update').observe(time.time() - start_time)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            k8s_apps_api = get_k8s_apps_api(cluster)
            
            new_replicas = request.data.get('replicas', app_obj.replicas)
            new_cpu = request.data.get('cpu_limit', app_obj.cpu_limit)
            new_memory = request.data.get('memory_limit', app_obj.memory_limit)
            new_image = request.data.get('image', app_obj.image)

            patch_body = {
                "spec": {
                    "replicas": int(new_replicas),
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": app_obj.name,
                                "image": new_image,
                                "resources": {
                                    "limits": {"cpu": new_cpu, "memory": new_memory}
                                }
                            }]
                        }
                    }
                }
            }

            k8s_apps_api.patch_namespaced_deployment(
                name=app_obj.name,
                namespace=namespace_obj.name,
                body=patch_body
            )
            
            updated_app = serializer.save()
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='update', outcome='success').inc()
            return Response(AppSerializer(updated_app).data, status=status.HTTP_200_OK)

        except ApiException as e:
            K8S_OPERATIONS_TOTAL.labels(resource='app', operation='update', outcome='error').inc()
            return Response({"error": f"error updating kubernetes: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        finally:
            K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='update').observe(time.time() - start_time)

    def delete(self, request, pk):
        start_time = time.time()
        app_obj = get_object_or_404(App, pk=pk)
        namespace_obj = app_obj.namespace
        cluster = namespace_obj.cluster

        try:
            k8s_apps_api = get_k8s_apps_api(cluster)
            k8s_apps_api.delete_namespaced_deployment(
                name=app_obj.name,
                namespace=namespace_obj.name
            )
        except ApiException as e:
            if e.status != 404:
                K8S_OPERATIONS_TOTAL.labels(resource='app', operation='delete', outcome='error').inc()
                K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='delete').observe(time.time() - start_time)
                return Response({"error": f"error deleting from kubernetes: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)

        app_obj.delete()
        K8S_OPERATIONS_TOTAL.labels(resource='app', operation='delete', outcome='success').inc()
        K8S_OPERATION_DURATION_SECONDS.labels(resource='app', operation='delete').observe(time.time() - start_time)
        return Response({"message": "app deleted successfully"}, status=status.HTTP_200_OK)