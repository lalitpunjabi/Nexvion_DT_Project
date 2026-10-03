# Phase 4.3 — Amazon ECR Container Registry Infrastructure & Security Gate

## Executive Summary

Phase 4.3 establishes **Amazon ECR (Elastic Container Registry)** as the central, immutable, and secure container image repository for the Nexvion Cloud-Native Delivery Platform.

This phase implements Infrastructure as Code (IaC) for ECR using Terraform, defines image lifecycle policies, enforces immutable Git SHA image tagging, integrates pre-push vulnerability scanning via Trivy `0.60.0`, and prepares Jenkins CI/CD pipeline automation for cloud-native registry pushing without hardcoded credentials.

---

## ECR Architecture & Specifications

```
+-----------------------------------------------------------------------------------+
|                                 AMAZON AWS ECR                                   |
|                                                                                   |
|  Account ID: 677012863109                                                        |
|  AWS Region: ap-south-1                                                           |
|  Repository Name: nexvion-web                                                     |
|  URI: 677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web                    |
|                                                                                   |
|  +------------------------+  +------------------------+  +---------------------+  |
|  | Tag Mutability         |  | Image Scanning         |  | Encryption at Rest  |  |
|  | IMMUTABLE              |  | Scan on Push: ENABLED  |  | AES256              |  |
|  +------------------------+  +------------------------+  +---------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 1. Terraform Infrastructure Definition

The ECR repository and lifecycle policy are declared declaratively in `terraform/main.tf` and exposed via `terraform/outputs.tf`.

### Repository Resource (`aws_ecr_repository.nexvion`)
```hcl
resource "aws_ecr_repository" "nexvion" {
  name                 = "nexvion-web"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}
```

### Lifecycle Policy (`aws_ecr_lifecycle_policy.nexvion`)
Prevents unbounded storage growth and cost accumulation while preserving release traceability:
- **Rule 1 (Untagged Clean-up):** Automatically expires untagged container images older than **7 days**.
- **Rule 2 (Tagged Retention):** Retains the **30 most recent** tagged Git SHA releases.

```hcl
resource "aws_ecr_lifecycle_policy" "nexvion" {
  repository = aws_ecr_repository.nexvion.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Retain maximum 30 tagged Git SHA images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

### Terraform Outputs (`terraform/outputs.tf`)
- `ecr_repository_url`: Exposes `677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web`
- `ecr_repository_name`: Exposes `nexvion-web`

---

## 2. IAM & Authentication Security Design

1. **Zero Hardcoded Secrets:** AWS Access Keys, Secret Keys, and Session Tokens are strictly prohibited in git configuration files or pipeline code.
2. **Short-Lived Token Authentication:** Docker authenticates to ECR via short-lived AWS CLI auth tokens (valid 12 hours):
   ```bash
   aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 677012863109.dkr.ecr.ap-south-1.amazonaws.com
   ```
3. **Jenkins Server Authentication:** In the current staging setup, Jenkins authenticates using short-lived tokens generated via AWS CLI (`aws ecr get-login-password`). In a production deployment, attaching an IAM Instance Profile containing `AmazonEC2ContainerRegistryPowerUser` to the Jenkins EC2 instance (`i-057f6d6d0bbb33b37`) eliminates credential management on the runner.

---

## 3. Immutable Tagging & Image Release Strategy

- **Primary Release Tag:** Short Git Commit SHA (7 characters, e.g., `0d575d0`).
- **Secondary Release Tag:** Pipeline Build Number (e.g., `:42`).
- **Immutable Policy:** Tag mutability is enforced as `IMMUTABLE`. Attempting to overwrite an existing tag (e.g., pushing `nexvion-web:0d575d0` twice) will be rejected by ECR, preventing silent artifact tampering.
- **`latest` Tag Usage:** Suppressed to enforce explicit versioning across all environments.

---

## 4. Jenkins CI/CD Pipeline Integration

Stage 6 (`Registry Push`) in `Jenkinsfile` is configured with parameter-driven control (`REGISTRY_TYPE` defaulting to `LOCAL_ONLY` and `PUSH_TO_REGISTRY` defaulting to `false`):

```groovy
if (params.REGISTRY_TYPE == 'AWS_ECR') {
    def registryUrl = params.REGISTRY_URL?.trim() ?: "677012863109.dkr.ecr.${env.AWS_REGION}.amazonaws.com/${env.APP_NAME}"
    def ecrHost = registryUrl.contains('/') ? registryUrl.split('/')[0] : registryUrl

    sh "aws ecr get-login-password --region ${env.AWS_REGION} | docker login --username AWS --password-stdin ${ecrHost}"
    sh "docker tag ${localCommit} ${registryUrl}:${commitSha}"
    sh "docker push ${registryUrl}:${commitSha}"
}
```

---

## 5. Verification & Validation Log

| Step | Command | Result | Details |
|---|---|---|---|
| **Terraform Format** | `terraform fmt -check -recursive` | **PASS** | 0 formatting errors |
| **Terraform Validate** | `terraform validate` | **PASS** | Valid configuration |
| **Terraform Plan** | `terraform plan -out=phase-4-3-ecr.tfplan` | **PASS** | `Plan: 2 to add, 0 to change, 0 to destroy` |
| **Infra Safety Check** | Infrastructure Preservation | **PASS** | 0 destroyed / replaced (EC2 `i-057f6d6d0bbb33b37` & EIP `52.66.25.69` untouched) |
| **AWS ECR Apply** | `terraform apply "phase-4-3-ecr.tfplan"` | **PASS** | ECR repository `nexvion-web` and lifecycle policy successfully created |
| **ECR Repository Check** | `aws ecr describe-repositories --repository-names nexvion-web` | **PASS** | Repository active, `IMMUTABLE` tags, `scanOnPush: true`, `AES256` encryption |
| **Lifecycle Policy Check** | `aws ecr get-lifecycle-policy --repository-name nexvion-web` | **PASS** | Rule 1 (untagged >7d) & Rule 2 (retain max 30 tagged) verified active |
| **Trivy Pre-Push Scan** | `aquasec/trivy:0.60.0 image nexvion-web:0d575d0` | **PASS** | **0 vulnerabilities found** (Clean Alpine 3.24.2 base) |
| **AWS ECR Auth & Push** | `aws ecr get-login-password` + `docker push` | **PASS** | Image `677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:0d575d0` pushed |
| **AWS Native ECR Scan** | `aws ecr describe-image-scan-findings` | **PASS** | Native ECR scan status `COMPLETE` with **0 vulnerability findings** |

---

## 6. Next Steps (Phase 4.4 Preparation)

1. Retain the immutable ECR image artifact `677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:0d575d0` for deployment.
2. Prepare Phase 4.4 — Amazon EKS Cluster & Node Group Provisioning with Terraform.
3. Update Helm values (`values-prod.yaml`) to reference the real ECR image repository URI.

