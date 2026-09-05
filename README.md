# Kubernetes Management & Automation API

A robust RESTful API built with Django REST Framework to interact dynamically with Kubernetes clusters, manage application deployments, and handle asynchronous backup orchestration using Celery and Redis.

---

## 🚀 Features

- **Cluster & Namespace Orchestration:** Dynamic management of Kubernetes API connections, namespaces, and application deployments.
- **Asynchronous Instant Backups:** Non-blocking backup requests triggered via Celery workers with immediate HTTP status response.
- **Scheduled Backups (Cron):** Automated periodic backups powered by Celery Beat and Crontab scheduling.
- **Kubernetes Streaming Integration:** Live data stream extraction from Pod containers using `tar` execution over WebSockets/Streams.
- **Status Tracking & Stale Cleanup:** Real-time backup status checks and automated cleanup for stale pending tasks (>24h).
- **Redis Caching:** High-performance live app status caching with a 60-second TTL to minimize unnecessary Kubernetes API calls.

---

## 🔄 Backup Task Execution Workflow

```text
1. Task Invoked (with backup_db_id)
   │
   ▼
2. Fetch Backup record from Database
   │
   ▼
3. Update status to 'running'
   │
   ▼
4. Extract App, Cluster, and Namespace details
   │
   ▼
5. Connect to Kubernetes API
   │
   ▼
6. Locate Pod matching label selector: app={app.name}
   │
   ▼
7. Create local backup directory (based on current date)
   │
   ▼
8. Execute `tar cfz -` command inside Pod (via streaming)
   │
   ▼
9. Receive compressed data stream
   │
   ▼
10. Write stream to `.tar.gz` archive on local disk
    │
    ▼
11. Update status to 'completed'
    │
    ▼
12. Return success response
```

---

## 🛠️ Tech Stack

- **Framework:** Django, Django REST Framework (DRF)
- **Task Queue & Scheduler:** Celery, Celery Beat
- **Message Broker & Cache:** Redis
- **Orchestration Client:** Kubernetes Python Client (`kubernetes`)
- **Containerization:** Docker

---

## ⚡ Quick Start & Services Setup

### 1. Prerequisites & Virtual Environment

```bash
git clone https://github.com/SinaSnyder/k8s-management-api.git
cd k8s-management-api

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
```

### 2. Running Required Services

Open **4 separate terminals** (ensure the virtual environment is active) and run:

#### Terminal 1: Redis Broker

```bash
docker run -d -p 6379:6379 --name redis-server redis:alpine
```

#### Terminal 2: Django API Server

```bash
python manage.py runserver
```

#### Terminal 3: Celery Worker

```bash
celery -A config worker --loglevel=info
```

#### Terminal 4: Celery Beat (Scheduler)

```bash
celery -A config beat --loglevel=info
```

---

## 📡 API Endpoints

### 1. Trigger Instant Backup

**Endpoint:**

```http
POST /backup
```

**Request Body:**

```json
{
  "app_id": 1,
  "source_path": "/var/lib/myapp/data.db"
}
```

**Response — `202 Accepted`:**

```json
{
  "backup_id": "bkp_8f31c2",
  "status": "pending"
}
```

---

### 2. Schedule Periodic Backup

**Endpoint:**

```http
POST /backup
```

**Request Body:**

```json
{
  "app_id": 1,
  "source_path": "/var/lib/myapp/data.db",
  "schedule": "0 20 * * *"
}
```

**Response — `201 Created`:**

```json
{
  "message": "Periodic backup successfully scheduled."
}
```

---

### 3. Get Backup Status

**Endpoint:**

```http
GET /backup/<backup_id>
```

**Response — `200 OK`:**

```json
{
  "backup_id": "bkp_8f31c2",
  "app_id": 1,
  "status": "completed"
}
```

---

### 4. List App Backups

**Endpoint:**

```http
GET /backup?app_id=1
```

**Response — `200 OK`:**

```json
[
  {
    "backup_id": "bkp_8f31c2",
    "status": "completed"
  },
  {
    "backup_id": "bkp_19ac0f",
    "status": "failed"
  }
]
```

---

## 📊 Observability & Metrics (VictoriaMetrics Pipeline)

This project exposes custom and standard system metrics from the Django application and collects them using a light, operator-based VictoriaMetrics stack inside the Kubernetes cluster.

### 1. Exposed Metrics (`/metrics`)
The application uses Prometheus client middleware to expose observability data at `/metrics`. Key metrics include:
- **`http_requests_total`**: Tracks incoming REST API request rates grouped by method, endpoint, and status code.
- **`http_request_duration_seconds`**: Measures request latency to monitor API performance.
- **`django_db_query_duration_seconds`**: Observes database query execution times.

---

### 2. Monitoring Pipeline Architecture

```text
[ Django App Pod ] --(Exposes /metrics)--> [ VMServiceScrape CRD ]
                                                    │
                                                    ▼
                                          [ VictoriaMetrics Agent ]
                                                    │
                                                    ▼
                                          [ VMSingle Storage ]
                                                    │
                                                    ▼
                                          [ VMUI Visualizer ]
```

---

### 3. Deployment & Setup (VictoriaMetrics Operator)
Instead of full Helm charts for the whole stack, the setup is built natively using the VictoriaMetrics Operator and custom Kubernetes CRDs:

##### Step 1: Install VictoriaMetrics Operator via Helm
```Bash
helm repo add vm [https://victoriametrics.github.io/helm-charts/](https://victoriametrics.github.io/helm-charts/)
helm repo update

helm upgrade --install vm-operator vm/victoria-metrics-operator \
  --namespace monitoring-system \
  --create-namespace
```
##### Step 2: Apply Custom Monitoring Resources (CRDs)
Apply the manifests located in the k8s/monitoring/ directory:

```Bash
kubectl apply -f k8s/monitoring/
```
This sets up:

- **`VMSingle`**: Lightweight single-node metric storage instance.

- **`VMServiceScrape`**: Targets the django-app-service on port 8000 at path /metrics every 15s.

- **`VMAgent`**: Handles the metric scraping and forwards data to VMSingle.

### 4. Metrics Visualization (VMUI)
To visualize metrics via VictoriaMetrics' built-in UI (VMUI):

**Port-forward the VMSingle Service**:

```Bash
kubectl port-forward -n monitoring-system svc/vmsingle-vmsingle-instance 8428:8428
```
**Access VMUI**:
Open `http://localhost:8428/vmui` in your browser.

**Check Target Health**:
Navigate to `http://localhost:8428/targets` to verify that the django-app target status is UP.

---

# 🌐 Multi-Node Production Deployment & High-Availability Infrastructure

The application is deployed in a multi-node Kubernetes (K3d) environment across physically separated public servers. It features an automated reverse-proxy routing pipeline with zero-downtime traffic forwarding.

## ✨ Key Infrastructure Highlights

- 🏢 **Dual-Node Distributed Architecture:** Spanning across dedicated Master (`37.32.26.255`) and Worker (`95.38.161.112`) nodes.
- 🚦 **Traefik Ingress Controller Integration:** Native routing handling both Frontend and API domain ingress rules at NodePort `31969`.
- 🔗 **Persistent Auto-Healing Tunnels:** Uses background `autossh` processes to bridge public node traffic directly into internal K3d container bridge networks (`172.23.0.2`).
- ⚡ **Low-Latency Kernel Traffic Routing:** Leverages Linux `iptables` with `DNAT` and `MASQUERADE` rules on both nodes to route standard HTTP/HTTPS (`80`/`443`) ports seamlessly without high-privilege container bindings.
- 🔄 **Dynamic Image Pull Enforcement:** Configured with `imagePullPolicy: Always` and patched deployment triggers to allow live updates bypassing local Docker layer caches.

## 🔗 Live Production Endpoints

| Component | Domain | Target Service |
| :--- | :--- | :--- |
| **Frontend Dashboard** | [http://rahimi.osdl.ir](http://rahimi.osdl.ir) | `k8s-frontend-service:80` |
| **Backend REST API** | [http://api.rahimi.osdl.ir](http://api.rahimi.osdl.ir) | `k8s-backend-service:8000` |

## 🛠️ Deployment & Maintenance Commands

### 1. Apply Kubernetes Resources

Apply all manifests including Deployments, Services, and Ingress:

```bash
kubectl apply -f k8s/
```

### 2. Reverse Proxy & IPTables Setup (Per Node)

Forward public ports to the internal SSH tunnel entrypoint (`8080`):

```bash
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to-destination 127.0.0.1:8080
sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -j DNAT --to-destination 127.0.0.1:8080
```

### 3. Initiate Persistent Tunneling (`sinavm`)

Connect the K3d internal Ingress to public nodes:

```bash
autossh -M 0 -f -N -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -R 8080:172.23.0.2:31969 ubuntu@37.32.26.255
autossh -M 0 -f -N -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -R 8080:172.23.0.2:31969 ubuntu@95.38.161.112
```

### 4. Force Instant Deployment Rollout

Trigger zero-downtime updates without altering tag versions:

```bash
kubectl patch deployment k8s-frontend --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/imagePullPolicy", "value": "Always"}]'
kubectl rollout restart deployment/k8s-frontend deployment/k8s-backend
```

---

🖼️ Application Screenshots & UI Showcase

<details open>
  <summary><b>📱 Main Dashboard & UI Features</b></summary>
  <br>

  | Cluster Management |
  | :---: |
  | <img src="https://github.com/user-attachments/assets/4215be91-b102-4310-8390-2e2a613c0657" width="100%"/> |
  | <img src="https://github.com/user-attachments/assets/721a988f-993a-4457-b489-d99ce5a28721" width="100%"/> |
  | <img src="https://github.com/user-attachments/assets/282942fd-9fae-4c7f-acf0-727c6d1b96d6" width="100%"/> |
  | <img src="https://github.com/user-attachments/assets/8d4125c2-8cfb-423d-90f1-bf27929987ea" width="100%"/> |
  | <img src="https://github.com/user-attachments/assets/93347d8c-545c-43ee-bef0-fd298e03f14b" width="100%"/> |
  | <img src="https://github.com/user-attachments/assets/e8801447-8b80-4693-8193-e164e8494ca2" width="100%"/> |

</details>


