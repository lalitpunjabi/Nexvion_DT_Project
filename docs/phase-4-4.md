# Phase 4.4 — Amazon EKS Cluster & Node Group Infrastructure Architecture

## Executive Summary

Phase 4.4 defines the Infrastructure as Code (IaC) configuration for provisioning an enterprise-grade **Amazon EKS (Elastic Kubernetes Service)** cluster and managed worker node group on AWS in region `ap-south-1`.

This architecture safely extends the existing Nexvion AWS environment without modifying, replacing, or destroying any pre-existing infrastructure (VPC, Jenkins/Ansible EC2 server, Elastic IP, Internet Gateway, route tables, security groups, or ECR container registry).

> [!WARNING]
> **IMPORTANT AWS COST & FREE TIER DISCLAIMER**
> 
> This architecture is designed specifically as a **COST-CONSTRAINED STAGING / LAB ARCHITECTURE** for internship and development testing.
>
> 1. **EKS Control Plane is NOT FREE:** AWS charges **$0.10 per hour (~$73.00/month)** for the EKS control plane (`aws_eks_cluster.nexvion`). It is **NOT** covered by the AWS Free Tier.
> 2. **Worker Nodes:** Managed worker nodes (`t3.medium` or `t3.small`) exceed 750h micro Free Tier limits and incur EC2 compute charges (~$0.0416/hr each, ~$60.00/month for 2 nodes).
> 3. **Public IPv4 Addresses:** AWS charges $0.005/hr (~$3.60/month per IP) for public IPv4 addresses.
> 4. **Cost Control Safeguard:** `terraform apply` is **NOT** run automatically. To prevent unexpected AWS bills, the cluster should only be provisioned when actively testing, and destroyed immediately afterwards using `terraform destroy -target=aws_eks_node_group.nexvion -target=aws_eks_cluster.nexvion`.

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
|                                 | Kubernetes Version: 1.31         |                                                    |
|                                 +----------------------------------+                                                    |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## 1. Comprehensive AWS Free Tier & Cost Breakdown

| Service / Resource | Resource Identifier | Cost Classification | Estimated Monthly Cost | Architecture Notes & Safeguards |
|---|---|---|---|---|
| **EKS Control Plane** | `aws_eks_cluster.nexvion` (`nexvion-eks`) | **MAY INCUR CHARGES** | ~$73.00 / month ($0.10/hr) | **Not covered by AWS Free Tier.** Provisioned on-demand; destroy after testing. |
| **EC2 Worker Nodes** | `aws_eks_node_group.nexvion` (2x `t3.medium`) | **MAY INCUR CHARGES** | ~$60.00 / month ($0.0416/hr x 2) | `t3.medium` (4GB RAM) required for system pods (CNI, CoreDNS). `t3.small` can be set in `variables.tf`. |
| **Public IPv4 Addresses** | Node public IPs & EC2 EIP | **MAY INCUR CHARGES** | ~$3.60 / month per IP ($0.005/hr) | Standard AWS public IPv4 charge (effective Feb 2024). |
| **NAT Gateway** | N/A | **AVOIDED ($0.00)** | **$0.00 (Omitted)** | **Intentionally omitted** to save ~$32.00/mo per NAT GW + data fees. Worker nodes use public subnets + IGW. |
| **Application Load Balancer** | N/A | **AVOIDED ($0.00)** | **$0.00 (Omitted)** | Omitted for Phase 4.4 to prevent $18.00/mo ALB base charge. NodePort / Ingress evaluated in Phase 4.5. |
| **EBS Storage Volumes** | Worker node root EBS volumes | **POTENTIALLY FREE** | $0.00 (Within Free Tier) | 20 GB root EBS volume per node. Combined with EC2 volume (20 GB), stays within 30 GB/mo gp2/gp3 Free Tier limits if run sequentially. |
| **Amazon ECR** | `aws_ecr_repository.nexvion` (`nexvion-web`) | **POTENTIALLY FREE** | $0.00 (Within Free Tier) | Includes 500 MB storage/month in Free Tier. |

---

## 2. EKS Networking Design & Cost-Saving Tradeoffs

- **VPC Preservation:** Reuses existing VPC `vpc-09df3f5fdabdcf81f` (`172.31.0.0/16`).
- **Multi-AZ Requirement:** AWS EKS requires subnets in at least **2 Availability Zones**:
  - **AZ 1 (`ap-south-1b`):** Reuses existing public subnet (`subnet-048f480df580a47f8`, CIDR `172.31.0.0/20`).
  - **AZ 2 (`ap-south-1a`):** Provisions additional public subnet (`aws_subnet.eks_public_a`, CIDR `172.31.16.0/20`) attached to existing route table (`rtb-0b5c00adb98133d97`) and Internet Gateway (`igw-045a89bde29483b3a`).
- **Subnet Tags for EKS Discovery:**
  - `kubernetes.io/cluster/nexvion-eks = shared`
  - `kubernetes.io/role/elb = 1`
- **Why NAT Gateway is Omitted:** Standard production EKS designs place worker nodes in private subnets behind dual NAT Gateways (~$64.00/month). For this staging/lab setup, worker nodes run in public subnets with `map_public_ip_on_launch = true`. Nodes communicate directly with AWS ECR and EKS control plane endpoints without needing NAT Gateways.

---

## 3. IAM Security Architecture & Required Provisioning Permissions

### A. Minimal IAM Permissions Required for Provisioning User `Nexvion`
To run `terraform apply` for Phase 4.4, the IAM user `arn:aws:iam::677012863109:user/Nexvion` requires the following minimal IAM permissions (attach via custom IAM policy in AWS Console):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
        "eks:ListAddons"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:DeleteRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies"
      ],
      "Resource": [
        "arn:aws:iam::677012863109:role/nexvion-eks-cluster-role",
        "arn:aws:iam::677012863109:role/nexvion-eks-node-group-role"
      ]
    }
  ]
}
```

> [!NOTE]
> Do **NOT** attach `AdministratorAccess` or broad wildcard IAM permissions to the `Nexvion` user.

### B. Dedicated IAM Roles Created by Terraform

1. **EKS Cluster IAM Role (`nexvion-eks-cluster-role`):**
   - Trust Policy: `eks.amazonaws.com`
   - Managed Policy: `arn:aws:iam::aws:policy/AmazonEKSClusterPolicy`

2. **EKS Node Group IAM Role (`nexvion-eks-node-group-role`):**
   - Trust Policy: `ec2.amazonaws.com`
   - Managed Policies:
     - `arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy`
     - `arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy`
     - `arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly`

---

## 4. EKS Add-ons & Kubernetes Version

- **Kubernetes Version:** `1.31` (Supported stable release in AWS EKS & Terraform AWS Provider v5.x).
- **Core Add-ons Declared:**
  - `vpc-cni`: AWS VPC CNI plugin for pod networking.
  - `coredns`: Kubernetes DNS resolution service.
  - `kube-proxy`: Network proxy on worker nodes.
- **EBS CSI Driver (`aws-ebs-csi-driver`):** Deferred. Stateless NGINX web containers do not require persistent EBS storage volumes.

---

## 5. Terraform Safety Audit (Zero-Destruction Guarantee)

Running `terraform plan -out=phase-4-4-eks.tfplan` outputs:

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

### Infrastructure Safety Matrix
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

## 6. Execution, Verification & Cost Cleanup Commands

### Provisioning (Only run when ready to test):
```bash
cd terraform
terraform apply "phase-4-4-eks.tfplan"
```

### Cluster Verification:
```bash
aws eks update-kubeconfig --region ap-south-1 --name nexvion-eks
kubectl get nodes
kubectl get pods -A
```

### Cost Teardown Command (Run immediately after testing to stop charges):
```bash
cd terraform
terraform destroy -target=aws_eks_node_group.nexvion -target=aws_eks_cluster.nexvion -target=aws_eks_addon.coredns -target=aws_eks_addon.vpc_cni -target=aws_eks_addon.kube_proxy
```
