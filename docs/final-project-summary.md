# Nexvion — AI-Powered E-Commerce DevOps & Cloud-Native Delivery Platform

## Executive Summary

The **Nexvion AI-Powered E-Commerce DevOps & Cloud-Native Delivery Platform** is a complete end-to-end cloud-native engineering project that transforms a modern web workload into a secure, highly automated, observable, and AI-assisted cloud deployment on Amazon Web Services (AWS) using Kubernetes (EKS), Helm, Jenkins, Prometheus, Grafana, ELK, and Google Gemini AI.

---

## 1. Project Objective & Vision

The core objective of Nexvion is to demonstrate production-grade DevOps and Cloud-Native engineering practices:
- Automating DevSecOps code validation, secret scanning, and container vulnerability scanning.
- Managing AWS infrastructure reproducibly using Infrastructure as Code (Terraform) and Configuration Management (Ansible).
- Orchestrating micro-deployments on Kubernetes (AWS EKS) using Helm charts and capacity-aware rolling update strategies.
- Operating full-stack platform observability (Prometheus/Grafana) and centralized log aggregation (Fluent Bit/Elasticsearch/Kibana).
- Providing automated incident analysis using client-side AI diagnostic tooling (Google Gemini) with offline rule-based fallbacks.
- Guaranteeing automated failure recovery via dynamic Helm rollbacks upon deployment timeout or container failure.

---

## 2. Platform Architecture

```
GitHub Repository
   │ (Push / PR)
   ▼
Jenkins Automation Server
   │
   ├─► 1. Code Syntax Validation (`node -c`) & Dependency Audit (`npm audit`)
   ├─► 2. Secret Scanning (GitLeaks v8.28.0)
   ├─► 3. Immutable Docker Build (`nexvion-web:<GIT_SHA>`)
   ├─► 4. Container Vulnerability Scan (Trivy v0.60.0)
   ├─► 5. Authenticate & Push to Amazon ECR (AES256 Encrypted, Immutable)
   ├─► 6. Authenticate to Amazon EKS (`nexvion-eks` v1.36)
   ├─► 7. Helm Upgrade / Install (`helm/nexvion-web`, `maxSurge: 0, maxUnavailable: 1`)
   ├─► 8. Rollout Monitoring (`kubectl rollout status --timeout=300s`)
   └─► 9. Health Verification & Rollback Handling (`helm rollback`)
           │
           ▼
Amazon EKS Staging Cluster (`ap-south-1`)
   │
   ├──► Application Workload (`nexvion` namespace)
   │      ├── Deployment (2 Pod Replicas, non-root UID 101)
   │      ├── ClusterIP Service (`nexvion-web-service:80`)
   │      ├── NGINX Ingress Controller (`NodePort:31449`)
   │      └── HPA (Metrics Server, CPU 1%/70%, 2 min / 5 max)
   │
   ├──► Observability Stack (`monitoring` namespace)
   │      ├── Prometheus Server (PromQL Scraper)
   │      └── Grafana Dashboard (`Nexvion EKS Platform Observability`)
   │
   ├──► Centralized Logging (`logging` namespace)
   │      ├── Fluent Bit (CRI Log Collector DaemonSet)
   │      ├── Elasticsearch (Single-Node Log Indexing)
   │      └── Kibana (`nexvion-logs-*` Interface)
   │
   └──► AI Incident Analyzer (`tools/incident-analysis/`)
          ├── Telemetry Collector (K8s APIs + ES Logs + PromQL)
          ├── 12-Rule Classifier & 5-Tier Severity Engine
          └── AI Analysis (Google Gemini) -> Structured Reports (`reports/`)
```

---

## 3. Complete Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Source Control** | Git, GitHub |
| **CI/CD Automation** | Jenkins Declarative Pipeline |
| **DevSecOps Security** | GitLeaks v8.28.0, Trivy v0.60.0, npm audit, Node.js syntax checker |
| **Containerization** | Docker Engine, `nginx:alpine` (Non-root UID 101, Read-only root FS) |
| **Artifact Registry** | Amazon ECR (Immutable tags, AES256 encryption, scanOnPush) |
| **Infrastructure as Code** | Terraform (VPC, Subnets, IAM Roles, EKS Cluster, ECR Repository) |
| **Config Management** | Ansible (Host hardening, Docker Engine, Jenkins installation) |
| **Cloud Infrastructure** | AWS EKS (`nexvion-eks` v1.36), EC2 (`t3.small` worker node), IAM |
| **Container Orchestration**| Kubernetes (`v1.36.4`), Helm 3 (`nexvion-web` chart v0.1.0) |
| **Ingress & Networking** | NGINX Ingress Controller (NodePort `31449`), ClusterIP Service |
| **Autoscaling & Metrics** | Kubernetes Metrics Server, Horizontal Pod Autoscaler (HPA) |
| **Observability** | Prometheus (v27.5.0), Grafana (v10.5.15) |
| **Centralized Logging** | Fluent Bit (v2.2.0), Elasticsearch (7.17.18), Kibana (7.17.18) |
| **AI Incident Analysis** | Python Incident Analyzer, Google Gemini API (`gemini-flash-lite-latest`) |

---

## 4. Summary of Implementation Phases (15 Phases)

| Phase | Title | Status | Summary |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Containerization & Hardening | **PASS** | Hardened `nginx:alpine` container running as UID 101 non-root with read-only root FS and `/healthz`. |
| **Phase 2** | Jenkins CI/CD & DevSecOps | **PASS** | Declarative Jenkins pipeline with static validation, GitLeaks secret scan, Trivy container scan, and Docker build. |
| **Phase 3** | Terraform & Ansible IaC | **PASS** | Automated provisioning of AWS VPC, Subnets, EKS cluster, IAM roles, ECR, and Ansible host hardening. |
| **Phase 4.1** | Raw Kubernetes Manifests | **PASS** | Production-ready K8s manifests (`Deployment`, `Service`, `Ingress`, `HPA`, `Secret`, `ConfigMap`). |
| **Phase 4.2** | Helm Packaging | **PASS** | Templated Helm 3 chart (`nexvion-web`) with environment overrides (`values-dev.yaml`, `values-prod.yaml`). |
| **Phase 4.3** | Amazon ECR Integration | **PASS** | Immutable ECR repository `nexvion-web` with AES256 encryption, lifecycle policy, and Trivy gate. |
| **Phase 4.4** | AWS EKS Infrastructure | **PASS** | Amazon EKS cluster `nexvion-eks` (v1.36) and managed node group on `t3.small` in `ap-south-1`. |
| **Phase 4.5** | EKS Workload Deployment | **PASS** | Helm deployment to EKS pulling ECR image `0d575d0`, 2/2 Ready pods, ClusterIP service, HTTP 200 health. |
| **Phase 4.6** | Metrics, HPA & Ingress | **PASS** | Metrics Server, active CPU HPA (`1%/70%`), and cost-conscious NGINX Ingress NodePort `31449` routing. |
| **Phase 4.7** | Prometheus & Grafana | **PASS** | Scraped node/pod PromQL metrics and Grafana dashboard (`Nexvion EKS Platform Observability`). |
| **Phase 4.8** | ELK Centralized Logging | **PASS** | Fluent Bit log collection DaemonSet, single-node Elasticsearch, and Kibana `nexvion-logs-*` interface. |
| **Phase 4.9** | AI Incident Analysis Engine | **PASS** | Python analyzer aggregating K8s, ES, and Prometheus evidence, 12-rule classifier, Gemini AI, JSON/MD reports. |
| **Phase 5** | End-to-End Integration & Rollback | **PASS** | Unified Jenkins pipeline with capacity-safe rolling update (`maxSurge: 0`), health checks, and automated `helm rollback`. |
| **Phase 6.1** | Integration Audit | **PASS** | Complete architecture, implementation, security, and documentation audit confirmed ready for final validation. |
| **Phase 6.2** | End-to-End Validation | **PASS WITH CORRECTIONS** | Executed 20 validation steps; updated K8s version `v1.36` and documented 3-step GitLeaks sequence. |

---

## 5. Security & DevSecOps Control Model

1. **Static Analysis & Syntax Validation**: Automated `node -c` checks syntax before build.
2. **Dependency Audit**: `npm audit` validates 0 high/critical runtime vulnerabilities.
3. **Secret Scanning**: GitLeaks scans all commits and files against custom `.gitleaks.toml` rules. Non-secret placeholders are allowlisted.
4. **Container Security**: Trivy scans container filesystem for OS/library CVEs (`--severity HIGH,CRITICAL --exit-code 1`).
5. **Runtime Container Hardening**:
   - `runAsNonRoot: true` (UID 101 `nginx`)
   - `readOnlyRootFilesystem: true`
   - `capabilities: drop ALL`, `add NET_BIND_SERVICE`
   - `allowPrivilegeEscalation: false`
6. **Artifact Immutability**: ECR tag immutability prevents image tampering or tag overwriting.

---

## 6. Observability, Logging & AI Analysis

- **Prometheus**: Scrapes cluster metrics every 15s. Key PromQL queries track pod availability, CPU/memory usage, and restart counts.
- **Grafana**: Pre-configured dashboard (`Nexvion EKS Platform Observability`) visualizes infrastructure metrics live.
- **Fluent Bit**: Formats container stdout/stderr logs into structured JSON enriched with Kubernetes metadata.
- **Elasticsearch & Kibana**: Stores log documents under index pattern `nexvion-logs-YYYY.MM.DD` searchable via Kibana GUI.
- **AI Incident Analyzer**: Aggregates multi-source evidence (K8s events, ES logs, PromQL metrics) and generates AI-assisted incident root cause reports via Google Gemini API.

---

## 7. Current Staging Limitations vs. Future Production Enhancements

### Current Staging Implementation
- Single `t3.small` EC2 worker node (2 vCPUs, 2 GB RAM, `maxPods=11`).
- Capacity-Safe Rolling Update strategy (`maxSurge: 0, maxUnavailable: 1`) to fit within single-node pod limits.
- NGINX Ingress NodePort `31449` internal cluster routing (omits AWS ALB to eliminate hourly charges).
- Single-node Elasticsearch instance in namespace `logging`.
- Ephemeral monitoring storage (`emptyDir` volumes).

### Future Production Enhancements
- Multi-node EKS Node Group across multiple Availability Zones with Auto Scaling Group (ASG).
- Zero-downtime rolling update strategy (`maxSurge: 1, maxUnavailable: 0` or Canary deployments).
- Provisioning of AWS Application Load Balancer (ALB) via AWS Load Balancer Controller with Route 53 DNS and ACM SSL/TLS certificates.
- Multi-node Elasticsearch cluster with persistent EBS / AWS OpenSearch storage.
- HashiCorp Vault or AWS Secrets Manager / External Secrets Operator (ESO) integration for dynamic production secret injection.

---

## 8. Final Project Status

**PROJECT COMPLETION STATUS: READY FOR FINAL SUBMISSION**
