from kubernetes import client
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_k8s_client(cluster):
    configuration = client.Configuration()
    
    address = cluster.address
    if not address.startswith("http"):
        address = f"https://{address}"
    
    configuration.host = address
    configuration.verify_ssl = False
    configuration.api_key['authorization'] = f"Bearer {cluster.token}"
    
    api_client = client.ApiClient(configuration)
    return client.CoreV1Api(api_client)


def get_k8s_apps_api(cluster):
    configuration = client.Configuration()
    
    address = cluster.address
    if not address.startswith("http"):
        address = f"https://{address}"
    
    configuration.host = address
    configuration.verify_ssl = False
    configuration.api_key['authorization'] = f"Bearer {cluster.token}"
    
    api_client = client.ApiClient(configuration)
    return client.AppsV1Api(api_client)