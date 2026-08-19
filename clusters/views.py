from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from kubernetes.client.rest import ApiException
from kubernetes import client
from kubernetes.client import V1Deployment, V1ObjectMeta, V1DeploymentSpec, V1PodTemplateSpec, V1PodSpec, V1Container, V1ResourceRequirements
from .models import App
from .serializers import AppSerializer
from .k8s_client import get_k8s_apps_api
from .models import Cluster, Namespace
from .serializers import ClusterSerializer, NamespaceSerializer
from .k8s_client import get_k8s_client


class ClusterListCreateAPIView(APIView):
    def get(self, request):
        clusters = Cluster.objects.all().order_by('-created_at')
        serializer = ClusterSerializer(clusters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ClusterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NamespaceListCreateAPIView(APIView):

    def get(self, request):
        cluster_id = request.query_params.get('cluster_id')
        if not cluster_id:
            return Response({"error": "cluster_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        cluster = get_object_or_404(Cluster, pk=cluster_id)
        namespaces = Namespace.objects.filter(cluster=cluster)
        serializer = NamespaceSerializer(namespaces, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        cluster_id = request.data.get('cluster_id')
        ns_name = request.data.get('name')

        if not cluster_id or not ns_name:
            return Response({"error": "sending cluster_id and name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cluster = Cluster.objects.get(pk=cluster_id)
        except Exception as e:
            print("=== K8S EXCEPTION DETAILS ===", repr(e))
            return Response({"error": f"جزئیات خطا: {repr(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

        if Namespace.objects.filter(cluster=cluster, name=ns_name).exists():
            return Response({"error": "this namesapce is already in database"}, status=status.HTTP_409_CONFLICT)

        try:
            k8s_api = get_k8s_client(cluster)
            body = client.V1Namespace(metadata=client.V1ObjectMeta(name=ns_name))
            k8s_api.create_namespace(body=body)

        except ApiException as e:
            if e.status == 409:
                return Response({"error": "this namesapce is already in kubernetes"}, status=status.HTTP_409_CONFLICT)
            elif e.status in [401, 403]:
                return Response({"error": "kubernetes access error or invalid token"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": f"error in conneting to kuber: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({"error": "kubernetet is unavailable or address is invalid"}, status=status.HTTP_502_BAD_GATEWAY)

        ns_obj = Namespace.objects.create(cluster=cluster, name=ns_name)
        serializer = NamespaceSerializer(ns_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NamespaceDetailAPIView(APIView):

    def delete(self, request, pk):
        try:
            ns_obj = Namespace.objects.get(pk=pk)
        except Namespace.DoesNotExist:
            return Response({"error": "Namespace not found"}, status=status.HTTP_404_NOT_FOUND)

        cluster = ns_obj.cluster

        try:
            k8s_api = get_k8s_client(cluster)
            k8s_api.delete_namespace(name=ns_obj.name)
        except ApiException as e:
            if e.status != 404:  
                return Response({"error": f"error in deleting: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            return Response({"error": "could not connect to kubernetes"}, status=status.HTTP_502_BAD_GATEWAY)

        ns_obj.delete()
        return Response({"message": "Namespace deleted successfully"}, status=status.HTTP_200_OK)



class AppListCreateAPIView(APIView):

    def get(self, request):
        namespace_id = request.query_params.get('namespace_id')
        if not namespace_id:
            return Response({"error": "namespace is required"}, status=status.HTTP_400_BAD_REQUEST)

        namespace_obj = get_object_or_404(Namespace, pk=namespace_id)
        cluster = namespace_obj.cluster
        apps = App.objects.filter(namespace=namespace_obj)

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

        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AppSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        namespace_obj = serializer.validated_data['namespace']
        cluster = namespace_obj.cluster
        app_name = serializer.validated_data['name']
        image = serializer.validated_data['image']
        replicas = serializer.validated_data.get('replicas', 1)
        cpu_limit = serializer.validated_data.get('cpu_limit', '500m')
        memory_limit = serializer.validated_data.get('memory_limit', '512Mi')

        if App.objects.filter(namespace=namespace_obj, name=app_name).exists():
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
        except ApiException as e:
            return Response({"error": f"kubernetes error: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({"error": f"could not connect to kubetnetes: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

        app_obj = serializer.save()
        return Response(AppSerializer(app_obj).data, status=status.HTTP_201_CREATED)


class AppDetailAPIView(APIView):

    def put(self, request, pk):
        app_obj = get_object_or_404(App, pk=pk)
        namespace_obj = app_obj.namespace
        cluster = namespace_obj.cluster

        serializer = AppSerializer(app_obj, data=request.data, partial=True)
        if not serializer.is_valid():
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
        except ApiException as e:
            return Response({"error": f"error updating kubernetes: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)

        updated_app = serializer.save()
        return Response(AppSerializer(updated_app).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
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
                return Response({"error": f"error deleting from kubernetes: {e.reason}"}, status=status.HTTP_502_BAD_GATEWAY)

        app_obj.delete()
        return Response({"message": "app deleted successfully"}, status=status.HTTP_200_OK)