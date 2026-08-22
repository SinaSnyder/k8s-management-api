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
