# Nexvion DevOps Platform — Final Viva Questions & Technical Answers

This document provides comprehensive technical answers to potential viva, examination, and code review questions regarding the Nexvion AI-Powered E-Commerce DevOps & Cloud-Native Delivery Platform architecture, security gates, Kubernetes deployment strategies, AWS cloud infrastructure, observability stack, AI incident analysis, and failure recovery.

---

## 1. Architecture Questions

### Q1: What problem does the Nexvion project solve?
**Answer:** Nexvion bridges the gap between static e-commerce web applications and production-grade Cloud-Native DevOps infrastructure. It provides an automated, secure, highly observable delivery platform that automates code validation, secret scanning, container building, vulnerability scanning, immutable artifact registry storage, Kubernetes rolling updates, real-time monitoring, centralized logging, automated rollback on deployment failure, and AI-driven incident analysis.

### Q2: Why use Kubernetes for workload orchestration?
**Answer:** Kubernetes provides declarative container orchestration, automated self-healing (restarting failed containers), Horizontal Pod Autoscaling (HPA), service discovery, load balancing, and zero-downtime rolling updates. It decouples application runtime management from underlying physical server infrastructure.

### Q3: Why use Helm instead of raw Kubernetes manifests?
**Answer:** Helm is the package manager for Kubernetes. It allows parameterization of Kubernetes manifests through `values.yaml` files (enabling distinct configurations for `dev` and `prod`), manages release versioning and revision history (`helm history`), enables single-command upgrades (`helm upgrade`), and provides one-command automated rollbacks (`helm rollback`).

### Q4: Why use Jenkins for CI/CD automation?
**Answer:** Jenkins is an industry-standard, highly extensible declarative automation server. It supports complex pipelines defined as code (`Jenkinsfile`), integrates seamlessly with Docker, AWS CLI, Helm, and security scanners (GitLeaks, Trivy), and allows automated execution triggered by git commits or webhooks.

### Q5: Why use Amazon ECR instead of public Docker Hub?
**Answer:** Amazon ECR (Elastic Container Registry) provides private, highly secure container image storage integrated natively with AWS IAM authentication. It enforces image immutability (preventing tag overwriting), enables automatic image scanning on push (`scanOnPush`), encrypts images at rest with AES256, and avoids public Docker Hub rate limits.

### Q6: Why use Terraform for infrastructure provisioning?
**Answer:** Terraform is an open-source Infrastructure as Code (IaC) tool that uses declarative state files to provision AWS resources (VPC, Subnets, EKS Cluster, Node Groups, ECR) reproducibly. It calculates resource dependencies automatically, prevents drift, and enables safe planning (`terraform plan`) prior to execution.

### Q7: Why use Ansible alongside Terraform?
**Answer:** Terraform provisions the cloud infrastructure (IaaS level), whereas Ansible manages OS-level configuration and software installation (PaaS level). Ansible is used to harden EC2 Linux hosts, install Docker Engine, install Jenkins, manage system packages, and maintain baseline security configurations idempotently.

---

## 2. CI/CD & DevSecOps Questions

### Q8: Can you explain the stages of the Jenkins pipeline?
**Answer:** The declarative [`Jenkinsfile`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/Jenkinsfile) executes 8 sequential stages:
1. **Checkout**: Clones the exact Git commit SHA.
2. **App Validation**: Validates Node.js files (`node -c`) and dependencies (`npm audit`).
3. **Secret Scanning**: Scans for leaked keys/tokens using GitLeaks v8.28.0.
4. **Docker Build**: Compiles Docker image tagged with short Git commit SHA (`nexvion-web:${GIT_SHA}`).
5. **Container Security Scan**: Scans built image with Trivy v0.60.0 for `HIGH` or `CRITICAL` vulnerabilities.
6. **ECR Authentication & Push**: Authenticates to ECR via AWS CLI and pushes immutable Git SHA tag.
7. **EKS & Helm Deployment**: Configures `kubectl` context, dry-runs Helm chart, upgrades release, and monitors rolling update status.
8. **Health Check & Diagnostics**: Probes `/healthz` endpoints and automatically triggers `helm rollback` if deployment fails.

### Q9: Why use GitLeaks in the CI/CD pipeline?
**Answer:** GitLeaks scans source code, documentation, and git history for hardcoded secrets such as AWS credentials, private keys, database passwords, or API tokens before code is pushed or built into a container image.

### Q10: Why use Trivy for container image scanning?
**Answer:** Trivy scans container OS packages (e.g. Alpine Linux packages) and application libraries for known CVE vulnerabilities. Setting `--severity HIGH,CRITICAL --exit-code 1` enforces a hard security gate, failing the pipeline if unpatched vulnerabilities exist.

### Q11: Why use immutable Git SHA tags instead of `latest`?
**Answer:** The `latest` tag is mutable and non-deterministic; using it makes it impossible to know exactly which code version is running in production. Git SHA tags (`e.g. 685f1c1`) are unique, immutable, and create a strict 1-to-1 audit trail from git commit to ECR artifact to Kubernetes pod.

### Q12: Why verify the ECR digest after pushing?
**Answer:** Verifying the image digest (`sha256:...`) ensures that the container image was uploaded cleanly without corruption and that Kubernetes deploys the exact binary digest verified during scanning.

---

## 3. Kubernetes & Workload Questions

### Q13: Why run 2 application pod replicas?
**Answer:** Running 2 replicas provides high availability (HA). If one pod fails or undergoes maintenance, the second pod continues serving incoming user traffic without downtime.

### Q14: Why use `maxSurge: 0` and `maxUnavailable: 1` for the rolling update strategy?
**Answer:** This is a **Capacity-Safe Rolling Update strategy** tailored for single-node `t3.small` EKS worker clusters with strict pod limits (`maxPods=11`). `maxSurge: 0` ensures Kubernetes does not try to create additional pods before terminating old ones, preventing `FailedScheduling: Too many pods` quota errors. `maxUnavailable: 1` ensures 1 pod remains active to process requests while the other pod updates.

### Q15: Why use Horizontal Pod Autoscaler (HPA)?
**Answer:** HPA monitors resource metrics (such as CPU utilization) via Metrics Server and automatically scales the deployment replica count between min 2 and max 5 pods when traffic load exceeds 70% target CPU utilization.

### Q16: Why configure readiness, liveness, and startup probes?
**Answer:** 
- **Startup Probe**: Gives slow-starting applications time to boot without being killed prematurely.
- **Liveness Probe**: Monitors whether the container is healthy; if the endpoint fails repeatedly, Kubernetes restarts the container.
- **Readiness Probe**: Determines whether the pod is ready to accept HTTP traffic; if it fails, Kubernetes temporarily removes the pod from the Service load balancer.

### Q17: Why run application containers as non-root user `nginx` (UID 101)?
**Answer:** Running as non-root aligns with the Least Privilege Principle. If an attacker breaches the web application, running as non-root prevents them from gaining root privilege on the underlying host node filesystem.

---

## 4. AWS Infrastructure Questions

### Q18: Why use Amazon EKS instead of self-managed Kubernetes (kubeadm)?
**Answer:** Amazon EKS provides a fully managed, highly available Kubernetes control plane (API server and etcd) backed by AWS SLAs, removing the operational burden of managing control-plane master nodes.

### Q19: Why deploy on a single `t3.small` worker node for staging?
**Answer:** A single `t3.small` instance (2 vCPUs, 2 GB RAM) provides a cost-constrained staging environment adequate for demonstrating container deployment, HPA metrics, logging, and AI incident analysis while minimizing AWS hourly compute costs.

### Q20: Why use NGINX Ingress with NodePort instead of AWS ALB?
**Answer:** An AWS Application Load Balancer (ALB) incurs additional hourly provisioning costs (~$18–$25/month) plus data processing charges. Using an NGINX Ingress Controller configured with `NodePort` (port `31449`) provides full L7 HTTP routing capability within existing worker capacity without incurring extra AWS service charges.

---

## 5. Observability & Centralized Logging Questions

### Q21: What metrics does Prometheus monitor?
**Answer:** Prometheus scrapes node-level metrics (CPU, RAM, disk I/O), Kubernetes cluster metrics (`kube-state-metrics` for pod phases, ready status, restart counts, HPA status), and container resource consumption via `cAdvisor`.

### Q22: What role does Grafana play in the platform?
**Answer:** Grafana provides visual dashboarding. It queries Prometheus via PromQL and displays real-time graphs for node health, pod replica status, CPU utilization, memory allocation, and container restart counters on the `Nexvion EKS Platform Observability` dashboard.

### Q23: How does Fluent Bit centralize log collection?
**Answer:** Fluent Bit runs as a `DaemonSet` on every Kubernetes node. It reads container log files from `/var/log/containers/`, parses CRI JSON log formats, enriches logs with Kubernetes metadata (pod name, namespace, container name, labels), and forwards them to Elasticsearch.

### Q24: Why use Elasticsearch and Kibana?
**Answer:** Elasticsearch indexes structured JSON logs for high-speed full-text searching across historical data. Kibana provides a web GUI (`nexvion-logs-*`) to search, filter, and visualize log streams across pods and namespaces.

---

## 6. AI Incident Analysis Questions

### Q25: What evidence does the Incident Analyzer tool collect?
**Answer:** The analyzer framework (`tools/incident-analysis/incident_analyzer.py`) queries 3 sources:
1. **Kubernetes API**: Pod status, restart counts, event messages.
2. **Elasticsearch REST API**: Error log entries matching search terms.
3. **Prometheus PromQL API**: Node readiness, pod CPU/RAM, restart counters.

### Q26: How does the AI incident classification and severity model work?
**Answer:** It applies a 12-rule classifier (e.g. `CrashLoopBackOff`, `Dependency Failure`, `High CPU`) and a 5-tier severity model (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`) based on pod ready counts, exit codes, and error log frequencies.

### Q27: What happens if an AI API key is not provided?
**Answer:** The engine features a 100% offline, deterministic `Rule-Based Analysis` fallback that evaluates collected telemetry against pre-defined diagnostic logic without calling external LLM services.

---

## 7. Failure Handling & Dynamic Rollback Questions

### Q28: How does the CI/CD pipeline detect deployment failures?
**Answer:** During `helm upgrade`, Jenkins runs `kubectl rollout status deployment/nexvion-web -n nexvion --timeout=300s`. If pods enter `ImagePullBackOff`, `CrashLoopBackOff`, or fail readiness probes within 300 seconds, the command exits with an error code, triggering the pipeline failure block.

### Q29: How does automated rollback work in Jenkins?
**Answer:** Prior to deployment, Jenkins queries `PREVIOUS_HELM_REVISION=$(helm history nexvion-web -n nexvion ...)`. Upon rollout failure, Jenkins captures pod diagnostic logs (`kubectl describe pods`, `kubectl logs`) and executes:
```bash
helm rollback nexvion-web ${PREVIOUS_HELM_REVISION} -n nexvion
```
This instantly reverts Kubernetes to the last known healthy deployment revision.
