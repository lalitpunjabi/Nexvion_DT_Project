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
> 2. **Kubernetes Version & Standard Support:** Configured with Kubernetes **1.36** (Standard Support). Standard Support avoids AWS Extended Support surcharges ($0.60/hr extra charged for deprecated/extended releases such as 1.31, 1.32, and 1.33).
> 3. **Account-Specific Eligibility:** Service items below are marked as *potentially billable; verify current account-specific Free Tier eligibility*.
> 4. **Initial Node Sizing:** Configured with **1 x `t3.small`** worker node (`desired_size = 1`, `min_size = 1`, `max_size = 2`) to minimize initial EC2 compute costs while remaining scalable.
> 5. **Zero Automatic Apply:** `terraform apply` is **NOT** run automatically.
> 6. **Safe Cleanup Procedure:** Never run a blind `terraform destroy` without target flags, as doing so would destroy your imported shared infrastructure. Follow the safe targeted cleanup procedure below.

---

## EKS Cluster & Networking Architecture Diagram

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                              AMAZON AWS VPC (vpc-09df3f5fdabdcf81f)                                     |
|                                                     172.31.0.0/16                                                       |
|                                                                                                                         |
|  +-------------------------------------------------------------+  +---------------------------------------------------+  |
|  | Existing Public Subnet (subnet-048f480df580a47f8)           |  | New Public Subnet (aws_subnet.eks_public_a)       |  |
|  | AZ: ap-south-1b | CIDR: 172.31.0.0/20                       |  | AZ: ap-south-1a | CIDR: 172.31.48.0/20             |  |
|  |                                                             |  |                                                   |  |
|  |  +---------------------------+  +------------------------+  |  |  +---------------------------------------------+  |  |
|  |  | Jenkins / Ansible EC2     |  | EKS Worker Node        |  |  |  | EKS Worker Node                             |  |  |
|  |  | i-057f6d6d0bbb33b37       |  | (t3.small, Node Group) |  |  |  | (t3.small, Node Group)                      |  |  |
|  |  | EIP: 52.66.25.69          |  |                        |  |  |  |                                             |  |  |
|  |  +---------------------------+  +------------------------+  |  |  +---------------------------------------------+  |  |
|  +-------------------------------------------------------------+  +---------------------------------------------------+  |
|                                 \                                 /                                                     |
|                                  \                               /                                                      |
|                                 +----------------------------------+                                                    |
|                                 | Amazon EKS Control Plane         |                                                    |
|                                 | Cluster Name: nexvion-eks        |                                                    |
|                                 | Kubernetes Version: 1.36         |                                                    |
|                                 +----------------------------------+                                                    |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## 1. Subnet Discovery & Non-Overlapping CIDR Selection

An AWS CLI discovery of existing subnets in VPC `vpc-09df3f5fdabdcf81f` revealed:

```text
+---------------------------+--------------+-----------------+------------+
| SubnetId                  | AZ           | CidrBlock       | State      |
+---------------------------+--------------+-----------------+------------+
| subnet-048f480df580a47f8  | ap-south-1b  | 172.31.0.0/20   | available  |
| subnet-01b935ef8f0931396  | ap-south-1c  | 172.31.16.0/20  | available  |
| subnet-0be45e1e52c618a4f  | ap-south-1a  | 172.31.32.0/20  | available  |
+---------------------------+--------------+-----------------+------------+
```

- **Conflict Analysis:** CIDR `172.31.16.0/20` was already allocated to default subnet `subnet-01b935ef8f0931396` in `ap-south-1c`, causing initial subnet creation failure (`InvalidSubnet.Conflict`).
- **Selected Non-Overlapping CIDR:** **`172.31.48.0/20`** (Range: `172.31.48.0` – `172.31.63.255`).
- **AZ Placement:** `ap-south-1a` (Satisfies EKS multi-AZ requirement alongside `ap-south-1b` without overlapping existing subnet ranges).

---

## 2. Kubernetes Version & Support Status

- **Selected Kubernetes Version:** `1.36`
- **AWS EKS Support Status:** **Standard Support**
- **Support Status Breakdown:**
  - `1.36` — **Standard Support (Selected)**
  - `1.35` — Standard Support
  - `1.34` — Standard Support
  - `1.33` — Extended Support (Incurs +$0.60/hr Extended Support surcharge)
  - `1.32` — Extended Support (Incurs +$0.60/hr Extended Support surcharge)
  - `1.31` — Extended Support (Incurs +$0.60/hr Extended Support surcharge)
- **Selection Rationale:** Choosing Kubernetes `1.36` ensures standard support on Amazon EKS, avoiding the $0.60/hour Extended Support surcharge while maintaining compatibility with core Kubernetes workloads and EKS add-ons (`vpc-cni`, `coredns`, `kube-proxy`).

---

## 3. Detailed Cost Analysis & Account-Aware Classification

| Service / Resource | Resource Identifier | Cost Classification | Estimated Monthly Cost | Architecture Notes & Account Eligibility |
|---|---|---|---|---|
| **EKS Control Plane** | `aws_eks_cluster.nexvion` (`nexvion-eks`) | **MUST INCUR CHARGES** | ~$73.00 / month ($0.10/hr) | **Not covered by AWS Free Tier.** Standard Support (v1.36) avoids $0.60/hr Extended Support penalty. |
| **EC2 Worker Nodes** | `aws_eks_node_group.nexvion` (1x `t3.small`) | **POTENTIALLY BILLABLE** | ~$15.00 / month ($0.0208/hr x 1) | *Potentially billable; verify current account-specific Free Tier eligibility*. `t3.small` (2GB RAM) supports CNI/CoreDNS. Initial deployment set to 1 node (`desired_size = 1`). |
| **Public IPv4 Addresses** | Node public IPs & EC2 EIP | **POTENTIALLY BILLABLE** | ~$3.60 / month per IP ($0.005/hr) | Standard AWS public IPv4 charge (effective Feb 2024). *Potentially billable; verify account eligibility*. |
| **EBS Storage Volumes** | Worker node root EBS volumes | **POTENTIALLY BILLABLE** | $0.00 – $1.60 / month | 20 GB root EBS volume per node. *Potentially billable if cumulative account storage exceeds 30 GB/mo gp2/gp3 Free Tier limit*. |
| **Amazon ECR Storage** | `aws_ecr_repository.nexvion` (`nexvion-web`) | **POTENTIALLY BILLABLE** | $0.00 – $0.50 / month | Includes 500 MB storage/month in Free Tier; excess is $0.10/GB-mo. |
| **NAT Gateway** | N/A | **AVOIDED ($0.00)** | **$0.00 (Omitted)** | **Intentionally omitted** to save ~$32.00/mo per NAT GW. Worker nodes run in public subnets with IGW routes. |
| **Application Load Balancer** | N/A | **AVOIDED ($0.00)** | **$0.00 (Omitted)** | **Intentionally omitted** for Phase 4.4 to prevent $18.00/mo ALB base charge. |

---

## 4. Worker Node Sizing & Initial Deployment Configuration

Worker node parameters in `terraform/variables.tf`:
- `eks_node_instance_types` = `["t3.small"]`
- `eks_desired_capacity` = `1` (Initial Free Tier / cost-conscious deployment)
- `eks_min_capacity` = `1`
- `eks_max_capacity` = `2`

### Sizing & Availability Justification:
- **Initial Deployment (1x `t3.small`):** Reduces EC2 compute cost to ~$15.00/month for initial EKS validation while leaving headroom for system pods (CNI, CoreDNS, kube-proxy).
- **Scalability:** The cluster can be scaled to 2 nodes (`desired_size = 2`) for multi-AZ pod scheduling and zero-downtime rolling update demonstrations via `-var="eks_desired_capacity=2"`.

---

## 5. IAM Provisioning Permissions & Required Custom Policy

### A. Pre-Attached Policies vs. Required Custom Policy for User `Nexvion`

The IAM user `arn:aws:iam::677012863109:user/Nexvion` has the following pre-attached managed policies:
- **`AmazonEC2FullAccess`:** Grants permissions for VPCs, Subnets, Route Tables, Internet Gateways, Security Groups, and EC2 instances.
- **`AmazonEC2ContainerRegistryFullAccess`:** Grants permissions for ECR repository management and image pushing.

To resolve initial `iam:TagRole` access errors and provision EKS without granting `AdministratorAccess`, attach the following **additional custom IAM policy** to user `Nexvion` in the AWS IAM Console:

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
        "iam:TagRole",
        "iam:UntagRole",
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

## 6. Partial Apply Failure & State Analysis

- **Initial Apply Error 1:** Subnet creation failed due to CIDR overlap on `172.31.16.0/20`.
- **Initial Apply Error 2:** IAM role tagging failed due to missing `iam:TagRole` on user `Nexvion`.
- **Partial State Verification:** Inspection via AWS CLI confirmed that **no partially created resources** (`nexvion-eks-cluster-role`, `nexvion-eks-node-group-role`, or `nexvion-eks-public-a`) exist in AWS.
- **Import Requirement:** **0 imports required.** Terraform will cleanly create all 13 Phase 4.4 resources once permissions are updated.

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
