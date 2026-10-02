# Nexvion Phase 4.1 — Kubernetes Manifests Architecture & Specifications

This directory contains production-grade, declarative Kubernetes manifests for deploying the **Nexvion E-Commerce Containerized Frontend** on Kubernetes clusters (Minikube / MicroK8s / AWS EKS).

---

## 1. Directory Structure & Manifest Purpose

| Manifest File | Resource Kind | Purpose & Description |
| :--- | :--- | :--- |
| [`namespace.yaml`](namespace.yaml) | `Namespace` | Creates isolated `nexvion` namespace for workload scoping and resource boundaries. |
| [`configmap.yaml`](configmap.yaml) | `ConfigMap` | Manages non-sensitive application environment variables (`APP_NAME`, `ENVIRONMENT`, `PORT`, `LOG_LEVEL`). |
| [`secret.yaml`](secret.yaml) | `Secret` | Provides safe placeholder structure for sensitive parameters (`API_KEY_PLACEHOLDER`, `SESSION_SECRET_PLACEHOLDER`). |
| [`deployment.yaml`](deployment.yaml) | `Deployment` | Manages 2-replica `nexvion-web` workload with RollingUpdate strategy, resource limits, health probes, and non-root security context. |
| [`service.yaml`](service.yaml) | `Service` | Exposes pods internally via ClusterIP service `nexvion-web-service` on port `80`. |
| [`ingress.yaml`](ingress.yaml) | `Ingress` | Configures external HTTP routing via NGINX Ingress Controller for host `nexvion.example.com`. |
| [`hpa.yaml`](hpa.yaml) | `HorizontalPodAutoscaler` | Automates pod scaling between 2 and 5 replicas based on a 70% CPU utilization threshold (`autoscaling/v2`). |

---

## 2. Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ EXTERNAL TRAFFIC                                                         │
│ http://nexvion.example.com                                               │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ INGRESS (Ingress / nexvion-web-ingress)                                  │
│ ingressClassName: nginx | Host: nexvion.example.com                     │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ SERVICE (ClusterIP / nexvion-web-service)                                │
│ Selector: app=nexvion-web | Port: 80 -> TargetPort: 80                   │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ DEPLOYMENT & PODS (Deployment / nexvion-web)                             │
│ Replicas: 2 (Scaling 2-5 via HPA) | Image: nexvion-web:<git-sha>          │
│ Probes: /healthz (Startup / Liveness / Readiness)                        │
│ Config: nexvion-config (ConfigMap) + nexvion-secret (Secret)            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Recommended Sequential Deployment Order

Apply manifests in dependency order to prevent missing resource errors:

```bash
# Step 1: Create Namespace
kubectl apply -f kubernetes/namespace.yaml

# Step 2: Apply Configuration & Secrets
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml

# Step 3: Deploy Application Workload
kubectl apply -f kubernetes/deployment.yaml

# Step 4: Expose Service Internally
kubectl apply -f kubernetes/service.yaml

# Step 5: Configure Ingress Routing
kubectl apply -f kubernetes/ingress.yaml

# Step 6: Enable Horizontal Pod Autoscaling
kubectl apply -f kubernetes/hpa.yaml
```

Alternatively, apply the entire directory:
```bash
kubectl apply -f kubernetes/
```

---

## 4. Workload Hardening & Security Profile

The [`deployment.yaml`](deployment.yaml) manifest implements container security hardening matching the Phase 1 NGINX Docker image:

- **Non-Root Execution:** Runs as user/group UID `101` (`nginx` non-root user in Alpine).
- **Read-Only Root Filesystem:** `readOnlyRootFilesystem: true` prevents unauthorized runtime filesystem modifications.
- **Privilege Escalation Block:** `allowPrivilegeEscalation: false` disables setuid/setgid privilege elevation.
- **Capability Drop:** Drops `ALL` Linux capabilities, adding back only `NET_BIND_SERVICE` for port 80 binding.
- **Writeable Temp Mounts:** `emptyDir` volumes mounted at `/tmp`, `/var/cache/nginx`, and `/var/run` allow NGINX operation under a read-only root filesystem.
- **Seccomp Profile:** Enforces `RuntimeDefault` Linux system call filtering.

---

## 5. Health Probes & Endpoint Verification

All health probes target the dedicated NGINX `/healthz` HTTP endpoint (returning `HTTP 200 OK`):

1. **Startup Probe:** Validates container startup (`initialDelaySeconds: 3`, `failureThreshold: 10`).
2. **Liveness Probe:** Detects container deadlocks and triggers pod restarts (`initialDelaySeconds: 5`, `periodSeconds: 10`).
3. **Readiness Probe:** Controls traffic routing to pods (`initialDelaySeconds: 3`, `periodSeconds: 5`). Pods receive traffic only when `/healthz` returns `200`.

---

## 6. Image Replacement & CI/CD Dynamic Tagging

In production CI/CD pipelines (Phase 4.2 / EKS), image references in `deployment.yaml` are substituted dynamically using immutable Git SHA commit tags:

```bash
# Example CI/CD Image Substitution Command
kubectl set image deployment/nexvion-web nexvion-web=<registry-url>/nexvion-web:${GIT_COMMIT_SHA} -n nexvion
```

---

## 7. Configuration Placeholders for Future EKS Deployment

| Resource | Placeholder Value | Required EKS / Production Update |
| :--- | :--- | :--- |
| `deployment.yaml` | `nexvion-web:v1.0.0` | Replace with ECR image URI (`<aws_account_id>.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:<git-sha>`). |
| `ingress.yaml` | `nexvion.example.com` | Replace with actual domain name registered in AWS Route 53 or ingress controller DNS. |
| `ingress.yaml` | `ingressClassName: nginx` | Update to `alb` if using AWS Load Balancer Controller (ALB Ingress). |
| `secret.yaml` | Safe stringData placeholders | Replace with production secret references via AWS Secrets Manager or External Secrets Operator. |

---

## 8. Manifest Syntax Validation

Validate manifest syntax without a live cluster using client-side dry-run checks:

```bash
kubectl apply --dry-run=client -f kubernetes/
```
