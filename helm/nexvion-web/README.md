# Nexvion Phase 4.2 — Helm Chart Documentation (`nexvion-web`)

This directory contains the production-oriented Helm 3 chart for packaging and deploying the **Nexvion E-Commerce Containerized Frontend Workload** across development (Minikube) and production (AWS EKS) environments.

---

## 1. Chart Structure

```
helm/
└── nexvion-web/
    ├── Chart.yaml              # Chart metadata (name, version 0.1.0, appVersion 1.0.0)
    ├── values.yaml              # Centralized default configuration values
    ├── values-dev.yaml          # Minikube / local development environment overrides
    ├── values-prod.yaml         # AWS EKS production environment overrides
    ├── README.md                # Helm chart documentation
    └── templates/
        ├── _helpers.tpl         # Named template helpers (labels, fullnames, selectors)
        ├── namespace.yaml       # Namespace manifest template (default: nexvion)
        ├── configmap.yaml       # ConfigMap template (APP_NAME, ENVIRONMENT, LOG_LEVEL)
        ├── secret.yaml          # Secret template with safe placeholders
        ├── deployment.yaml      # 2-replica Deployment template with probes & securityContext
        ├── service.yaml         # ClusterIP Service template (port 80)
        ├── ingress.yaml         # Ingress template (ingressClassName: nginx)
        └── hpa.yaml             # HorizontalPodAutoscaler template (2-5 replicas, 70% CPU)
```

---

## 2. Environment Configuration Strategy

| Values File | Target Environment | Image Repository | Tag Strategy | Key Features |
| :--- | :--- | :--- | :--- | :--- |
| [`values.yaml`](values.yaml) | Base Default | `nexvion-web` | `v1.0.0` | Centralized defaults for all chart parameters. |
| [`values-dev.yaml`](values-dev.yaml) | Local Minikube | `nexvion-web` | `v1.0.0` | Uses local Minikube Docker daemon image (`pullPolicy: IfNotPresent`). |
| [`values-prod.yaml`](values-prod.yaml) | AWS EKS | `<aws-account-id>.dkr.ecr.<region>.amazonaws.com/nexvion-web` | `<git-sha>` | ECR repository URI placeholder, immutable Git SHA tag, `pullPolicy: Always`. |

---

## 3. Usage & Lifecycle Commands

### Lint Chart Syntax
```bash
helm lint helm/nexvion-web
```

### Render Templates (Dry-Run Check)
```bash
# Render base defaults
helm template nexvion-web helm/nexvion-web

# Render local development values
helm template nexvion-web helm/nexvion-web -f helm/nexvion-web/values-dev.yaml

# Render production EKS values
helm template nexvion-web helm/nexvion-web -f helm/nexvion-web/values-prod.yaml
```

### Install Chart on Minikube
```bash
# Create namespace and install release
helm install nexvion-web helm/nexvion-web -f helm/nexvion-web/values-dev.yaml --namespace nexvion --create-namespace
```

### Upgrade Release
```bash
helm upgrade nexvion-web helm/nexvion-web -f helm/nexvion-web/values-dev.yaml --namespace nexvion
```

### Rollback Release
```bash
helm rollback nexvion-web 1 --namespace nexvion
```

### Uninstall Release
```bash
helm uninstall nexvion-web --namespace nexvion
```

---

## 4. Workload Security & Probe Verification

- **Non-Root Execution:** Container runs under UID/GID `101` (`nginx` non-root user).
- **Read-Only Root Filesystem:** `readOnlyRootFilesystem: true` enforced alongside `emptyDir` temp mounts at `/tmp`, `/var/cache/nginx`, and `/var/run`.
- **Capability Hardening:** Drops `ALL` Linux capabilities, adding back `NET_BIND_SERVICE`.
- **Probes:** Startup, liveness, and readiness probes target `/healthz` on port `80`.

---

## 5. Secrets Management Strategy

The `secret.yaml` template provides safe stringData placeholders (`API_KEY_PLACEHOLDER`, `SESSION_SECRET_PLACEHOLDER`) for local validation.

> [!IMPORTANT]
> Plain Kubernetes Secrets are not a complete secret-management solution. In production AWS EKS (Phase 4.4+), real secrets should be injected securely using AWS Secrets Manager integrated via External Secrets Operator (ESO) or Secrets Store CSI Driver.
