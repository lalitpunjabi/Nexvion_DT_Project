# Phase 4.4 — Amazon EKS Cluster & Node Group Infrastructure Architecture

## Executive Summary

Phase 4.4 defines the Infrastructure as Code (IaC) configuration for provisioning an enterprise-grade **Amazon EKS (Elastic Kubernetes Service)** cluster and managed worker node group on AWS in region `ap-south-1`.

This architecture safely extends the existing Nexvion AWS environment without modifying, replacing, or destroying any pre-existing infrastructure (VPC, Jenkins/Ansible EC2 server, Elastic IP, Internet Gateway, route tables, security groups, or ECR container registry).

> [!WARNING]
> **COST-CONSTRAINED STAGING / LAB ARCHITECTURE & ACCOUNT-AWARE COST NOTICE**
> 
> This configuration is structured as a **COST-CONSTRAINED STAGING / LAB ARCHITECTURE** for internship and development testing.
>
> 1. **EKS Control Plane Charges:** AWS charges **$0.10 per hour (~$73.00/month)** for the EKS control plane (`aws_eks_cluster.nexvion`). The EKS control plane is **NOT** covered by the AWS Free Tier.
> 2. **Kubernetes Version & Extended Support Surcharge Avoidance:** Configured with Kubernetes **1.36** (Standard Support). Standard Support avoids AWS Extended Support surcharges ($0.60/hr extra charged for deprecated/extended releases such as 1.31, 1.32, and 1.33).
> 3. **Account-Specific Eligibility:** Service items below are marked as *potentially billable; verify current account-specific Free Tier eligibility*.
> 4. **Zero Automatic Apply:** `terraform apply` is **NOT** run automatically. To prevent unexpected AWS bills, the cluster should only be provisioned on-demand when actively testing.
> 5. **Safe Cleanup Procedure:** Never run a blind `terraform destroy` without target flags, as doing so would destroy your imported shared infrastructure. Follow the safe targeted cleanup procedure below.

---

## EKS Cluster & Networking Architecture Diagram

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                              AMAZON AWS VPC (vpc-09df3f5fdabdcf81f)                                     |
|                                                     172.31.0.0/16                                                       |
|                                                                                                                         |
|  +-------------------------------------------------------------+  +---------------------------------------------------+  |
|  | Existing Public Subnet (subnet-048f480df580a47f8)           |  | New Public Subnet (aws_subnet.eks_public_a)       |  |
|  | AZ: ap-south-1b | CIDR: 172.31.0.0/20                       |  | AZ: ap-south-1a | CIDR: 172.31.16.0/20             |  |
|  |                                                             |  |                                                   |  |
|  |  +---------------------------+  +------------------------+  |  |  +---------------------------------------------+  |  |
|  |  | Jenkins / Ansible EC2     |  | EKS Worker Nodes       |  |  |  | EKS Worker Nodes                            |  |  |
|  |  | i-057f6d6d0bbb33b37       |  | (t3.medium, Node Group)|  |  |  | (t3.medium, Node Group)                     |  |  |
|  |  | EIP: 52.66.25.69          |  |                        |  |  |  |                                             |  |  |
|  |  +---------------------------+  +------------------------+  |  |  +---------------------------------------------+  |  |
|  +-------------------------------------------------------------+  +---------------------------------------------------+  |
|                                 \                                 /                                                     |
|                                  \                               /                                                      |
|                                 +----------------------------------+                                                    |
|                                 | Amazon EKS Control Plane         |                                                    |
|                                 | Cluster Name: nexvion-eks        |                                                    |
|                                 | Kubernetes Version: 1.34         |                                                    |
|                                 +----------------------------------+                                                    |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## 1. Kubernetes Version & Support Status

- **Selected Kubernetes Version:** `1.36`
- **AWS EKS Support Status:** **Standard Support**
- **Support Status Breakdown:**
  - `1.36` — Standard Support
  - `1.35` — Standard Support
  - `1.34` — **Standard Support (Selected)**
  - `1.33` — Extended Support (Incurs +$0.60/hr surcharge)
  - `1.32` — Extended Support (Incurs +$0.60/hr surcharge)
  - `1.31` — Extended Support (Incurs +$0.60/hr surcharge)
- **Selection Rationale:** Choosing Kubernetes `1.36` ensures standard support on Amazon EKS, avoiding the $0.60/hour Extended Support surcharge while maintaining compatibility with core Kubernetes workloads and EKS add-ons.

---

## 2. Detailed Cost Analysis & Account-Aware Classification

| Service / Resource | Resource Identifier | Cost Classification | Estimated Monthly Cost | Architecture Notes & Account Eligibility |
|---|---|---|---|---|
| **EKS Control Plane** | `aws_eks_cluster.nexvion` (`nexvion-eks`) | **MUST INCUR CHARGES** | ~$73.00 / month ($0.10/hr) | **Not covered by AWS Free Tier.** Standard Support (v1.36) avoids $0.60/hr Extended Support penalty. |
| **EC2 Worker Nodes** | `aws_eks_node_group.nexvion` (2x `t3.medium`) | **POTENTIALLY BILLABLE** | ~$60.00 / month ($0.0416/hr x 2) | *Potentially billable; verify current account-specific Free Tier eligibility*. `t3.medium` (4GB RAM) supports CNI/CoreDNS. `t3.small` can be configured via `variables.tf`. |
| **Public IPv4 Addresses** | Node public IPs & EC2 EIP | **POTENTIALLY BILLABLE** | ~$3.60 / month per IP ($0.005/hr) | Standard AWS public IPv4 charge (effective Feb 2024). *Potentially billable; verify account eligibility*. |
| **EBS Storage Volumes** | Worker node root EBS volumes | **POTENTIALLY BILLABLE** | $0.00 – $3.20 / month | 20 GB root EBS volume per node. *Potentially billable if cumulative account storage exceeds 30 GB/mo gp2/gp3 Free Tier limit*. |
| **Amazon ECR Storage** | `aws_ecr_repository.nexvion` (`nexvion-web`) | **POTENTIALLY BILLABLE** | $0.00 – $0.50 / month | Includes 500 MB storage/month in Free Tier; excess is $0.10/GB-mo. |
| **NAT Gateway** | N/A | **AVOIDED ($0.00)** | **$0.00 (Omitted)** | **Intentionally omitted** to save ~$32.00/mo per NAT GW. Worker nodes run in public subnets with IGW routes. |
| **Application Load Balancer** | N/A | **AVOIDED ($0.00)** | **$0.00 (Omitted)** | **Intentionally omitted** for Phase 4.4 to prevent $18.00/mo ALB base charge. |

---

## 3. Worker Node Cost Settings & Sizing Tradeoffs

Worker node parameters are fully configurable in `terraform/variables.tf`:
- `eks_node_instance_types` (default: `["t3.medium"]`)
- `eks_desired_capacity` (default: `2`)
- `eks_min_capacity` (default: `1`)
- `eks_max_capacity` (default: `3`)

### Availability vs. Cost Tradeoff Analysis:
1. **Single Worker Node (`desired_size = 1`):**
   - **Cost:** Lower cost (~$30.00/mo for 1x `t3.medium` or ~$15.00/mo for 1x `t3.small`).
   - **Availability:** Lower availability. Worker node restart or maintenance results in total cluster pod downtime. Multi-AZ pod scheduling is disabled.
2. **Dual Worker Nodes (`desired_size = 2` - Current Default):**
   - **Cost:** Higher cost (~$60.00/mo for 2x `t3.medium` or ~$30.00/mo for 2x `t3.small`).
   - **Availability:** High availability. Pods are distributed across Availability Zones (`ap-south-1a` and `ap-south-1b`), enabling zero-downtime rolling updates and high availability evaluation.
   - **Justification for Internship Staging:** Defaulting to `desired_size = 2` validates production multi-AZ pod scheduling, while allowing simple override to `desired_size = 1` via `-var="eks_desired_capacity=1"` for minimal cost testing.

---

## 4. EKS Networking Review (Cost-Saving Staging Design)

- **VPC Preservation:** Reuses existing VPC `vpc-09df3f5fdabdcf81f` (`172.31.0.0/16`).
- **Multi-AZ Subnets:**
  - **AZ 1 (`ap-south-1b`):** Reuses existing public subnet (`subnet-048f480df580a47f8`, CIDR `172.31.0.0/20`).
  - **AZ 2 (`ap-south-1a`):** Provisions additional public subnet (`aws_subnet.eks_public_a`, CIDR `172.31.16.0/20`) attached to existing route table (`rtb-0b5c00adb98133d97`) and Internet Gateway (`igw-045a89bde29483b3a`).
- **Subnet Tagging for EKS Discovery:**
  - `kubernetes.io/cluster/nexvion-eks = shared`
  - `kubernetes.io/role/elb = 1`
- **NAT Gateway Omission Rationale:** Running worker nodes in public subnets directly connected to the Internet Gateway avoids dual NAT Gateway charges (~$64.00/month). Worker nodes assign public IPv4 addresses to communicate with ECR and EKS control plane endpoints directly.

---

## 5. IAM Provisioning Permissions & Role Design

### A. Pre-Attached Policies vs. Required Custom Policy for User `Nexvion`

The IAM user `arn:aws:iam::677012863109:user/Nexvion` has the following pre-attached managed policies:
- **`AmazonEC2FullAccess`:** Grants permissions for VPCs, Subnets, Route Tables, Internet Gateways, Security Groups, and EC2 instances.
- **`AmazonEC2ContainerRegistryFullAccess`:** Grants permissions for ECR repository management and image pushing.

To provision EKS and IAM roles via Terraform without granting `AdministratorAccess`, attach the following **additional custom IAM policy** to user `Nexvion`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EKSServiceManagement",
      "Effect": "Allow",
      "Action": [
        "eks:CreateCluster",
        "eks:DescribeCluster",
        "eks:ListClusters",
        "eks:DeleteCluster",
        "eks:CreateNodegroup",
        "eks:DescribeNodegroup",
        "eks:ListNodegroups",
        "eks:DeleteNodegroup",
        "eks:UpdateClusterConfig",
        "eks:UpdateClusterVersion",
        "eks:UpdateNodegroupConfig",
        "eks:CreateAddon",
        "eks:DescribeAddon",
        "eks:DeleteAddon",
        "eks:ListAddons",
        "eks:DescribeClusterVersions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMRoleManagementForEKS",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:DeleteRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:CreateServiceLinkedRole"
      ],
      "Resource": [
        "arn:aws:iam::677012863109:role/nexvion-eks-cluster-role",
        "arn:aws:iam::677012863109:role/nexvion-eks-node-group-role",
        "arn:aws:iam::677012863109:role/aws-service-role/eks.amazonaws.com/*"
      ]
    }
  ]
}
```

### B. Dedicated Terraform-Created Roles
1. **Cluster Role (`nexvion-eks-cluster-role`):** Trusted by `eks.amazonaws.com`, attached with `AmazonEKSClusterPolicy`.
2. **Node Group Role (`nexvion-eks-node-group-role`):** Trusted by `ec2.amazonaws.com`, attached with `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, and `AmazonEC2ContainerRegistryReadOnly`.

---

## 6. EKS Add-ons & Hardening Limitations

- **Kubernetes Version:** `1.36` (Standard Support release).
- **Core Add-ons Declared:**
  - `vpc-cni`: AWS VPC CNI plugin for pod networking (compatible with K8s 1.36).
  - `coredns`: Kubernetes DNS service (compatible with K8s 1.36).
  - `kube-proxy`: Worker node network proxy (compatible with K8s 1.36).
- **EBS CSI Driver (`aws-ebs-csi-driver`):** Deferred because the NGINX web workload is stateless.
- **CNI Security Tradeoff Note:** `AmazonEKS_CNI_Policy` is attached directly to the worker node role. In high-security production clusters, IRSA (IAM Roles for Service Accounts) can isolate `aws-node` pod permissions to a dedicated IAM role. For this staging setup, attaching CNI policy to the node role is standard and avoids OIDC provider complexity.

---

## 7. Terraform Safety Audit (Zero-Destruction Guarantee)

Execution of `terraform plan "-out=phase-4-4-eks.tfplan"` produces:

```text
Plan: 13 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + eks_cluster_arn               = (known after apply)
  + eks_cluster_endpoint          = (known after apply)
  + eks_cluster_name              = "nexvion-eks"
  + eks_cluster_security_group_id = (known after apply)
  + eks_node_group_arn            = (known after apply)
  + eks_node_group_name           = "nexvion-node-group"
```

### Shared Infrastructure Safety Matrix
| Resource Type | Resource Identifier | Planned Action | Safety Status |
|---|---|---|---|
| EC2 Server | `i-057f6d6d0bbb33b37` (Jenkins/Ansible) | **NO CHANGE** | Preserved |
| Elastic IP | `52.66.25.69` | **NO CHANGE** | Preserved |
| VPC | `vpc-09df3f5fdabdcf81f` | **NO CHANGE** | Preserved |
| Subnet | `subnet-048f480df580a47f8` | **NO CHANGE** | Preserved |
| Internet Gateway | `igw-045a89bde29483b3a` | **NO CHANGE** | Preserved |
| Security Group | `sg-0e2c619a238e449df` | **NO CHANGE** | Preserved |
| ECR Registry | `nexvion-web` | **NO CHANGE** | Preserved |

---

## 8. SAFE Targeted Cleanup Procedure

> [!CAUTION]
> **NEVER RUN A BLIND `terraform destroy`**
> 
> Running `terraform destroy` without target flags will destroy all imported shared infrastructure (EC2 `i-057f6d6d0bbb33b37`, EIP `52.66.25.69`, VPC, Subnets, ECR `nexvion-web`).

### Safe Targeted Destruction Command:
To teardown Phase 4.4 EKS resources after testing without impacting shared infrastructure, execute:

```bash
cd terraform

terraform destroy \
  -target=aws_eks_addon.coredns \
  -target=aws_eks_addon.kube_proxy \
  -target=aws_eks_addon.vpc_cni \
  -target=aws_eks_node_group.nexvion \
  -target=aws_eks_cluster.nexvion \
  -target=aws_iam_role_policy_attachment.eks_worker_node_policy \
  -target=aws_iam_role_policy_attachment.eks_cni_policy \
  -target=aws_iam_role_policy_attachment.eks_ecr_read_only \
  -target=aws_iam_role_policy_attachment.eks_cluster_policy \
  -target=aws_iam_role.eks_node_group \
  -target=aws_iam_role.eks_cluster \
  -target=aws_route_table_association.eks_public_a_assoc \
  -target=aws_subnet.eks_public_a
```
