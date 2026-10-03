# Phase 4.4 — Amazon EKS Cluster & Node Group Infrastructure Architecture

## Executive Summary

Phase 4.4 defines the Infrastructure as Code (IaC) configuration for provisioning an enterprise-grade **Amazon EKS (Elastic Kubernetes Service)** cluster and managed worker node group on AWS in region `ap-south-1`.

This architecture safely extends the existing Nexvion AWS environment without modifying, replacing, or destroying any pre-existing infrastructure (VPC, Jenkins/Ansible EC2 server, Elastic IP, Internet Gateway, route tables, or security groups).

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

## 1. Networking Design & High Availability

- **VPC Preservation:** Utilizes the existing VPC (`vpc-09df3f5fdabdcf81f`, `172.31.0.0/16`).
- **Multi-AZ Subnet Requirement:** EKS requires subnets across at least **2 Availability Zones**.
  - **AZ 1 (`ap-south-1b`):** Reuses the existing public subnet (`subnet-048f480df580a47f8`, CIDR `172.31.0.0/20`).
  - **AZ 2 (`ap-south-1a`):** Provisions an additional public subnet (`aws_subnet.eks_public_a`, CIDR `172.31.16.0/20`) associated with the existing Internet Gateway (`igw-045a89bde29483b3a`) via the existing route table (`rtb-0b5c00adb98133d97`).
- **Subnet Tagging:** Configured with standard EKS discovery tags:
  - `kubernetes.io/cluster/nexvion-eks = shared`
  - `kubernetes.io/role/elb = 1`

---

## 2. IAM Role & Security Design (Least Privilege)

1. **EKS Cluster IAM Role (`nexvion-eks-cluster-role`):**
   - Trust Policy: `eks.amazonaws.com`
   - Managed Policy: `arn:aws:iam::aws:policy/AmazonEKSClusterPolicy`
   - Grants EKS control plane permissions to manage AWS networking resources (ENIs, Security Groups).

2. **EKS Node Group IAM Role (`nexvion-eks-node-group-role`):**
   - Trust Policy: `ec2.amazonaws.com`
   - Managed Policies:
     - `arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy`
     - `arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy`
     - `arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly`
   - Enables nodes to join the cluster, establish AWS VPC CNI networking, and pull container images from ECR.

---

## 3. Terraform Resource Specifications

### EKS Control Plane Cluster (`aws_eks_cluster.nexvion`)
- **Cluster Name:** `nexvion-eks` (configurable via `var.eks_cluster_name`)
- **Kubernetes Version:** `1.31` (latest stable production release supported by AWS EKS and Terraform AWS Provider v5.x)
- **Endpoint Access:** Public and Private endpoint access enabled.

### EKS Managed Node Group (`aws_eks_node_group.nexvion`)
- **Node Group Name:** `nexvion-node-group`
- **Instance Types:** `t3.medium` (2 vCPUs, 4 GB RAM per node)
- **Capacity Type:** `ON_DEMAND`
- **Scaling Configuration:**
  - Desired Capacity: `2` worker nodes
  - Minimum Capacity: `1` worker node
  - Maximum Capacity: `3` worker nodes
- **Update Configuration:** `max_unavailable = 1`

---

## 4. Cost Optimization & Architecture Rationale

- **NAT Gateway Avoidance ($0.00 extra networking cost):** Rather than creating expensive NAT Gateways ($32/month per NAT GW + data processing charges), worker nodes run in public subnets with `map_public_ip_on_launch = true` attached to the existing Internet Gateway. Nodes communicate directly with AWS ECR, AWS APIs, and internet endpoints safely via AWS Security Groups.
- **Node Sizing:** `t3.medium` instances provide adequate CPU and memory headroom for NGINX workloads, Kubernetes system components (CoreDNS, kube-proxy, aws-node CNI), and Helm releases at reasonable cost ($0.0416/hr each).

---

## 5. Terraform Plan & Safety Audit

Execution of `terraform plan -out=phase-4-4-eks.tfplan` confirms:

```text
Plan: 10 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + eks_cluster_arn               = (known after apply)
  + eks_cluster_endpoint          = (known after apply)
  + eks_cluster_name              = "nexvion-eks"
  + eks_cluster_security_group_id = (known after apply)
  + eks_node_group_arn            = (known after apply)
  + eks_node_group_name           = "nexvion-node-group"
```

### Infrastructure Safety Audit
| Resource Type | Resource ID | Expected Action | Status |
|---|---|---|---|
| EC2 Instance | `i-057f6d6d0bbb33b37` (Jenkins/Ansible) | **NO CHANGE** | Preserved |
| Elastic IP | `52.66.25.69` | **NO CHANGE** | Preserved |
| VPC | `vpc-09df3f5fdabdcf81f` | **NO CHANGE** | Preserved |
| Subnet | `subnet-048f480df580a47f8` | **NO CHANGE** | Preserved |
| Internet Gateway | `igw-045a89bde29483b3a` | **NO CHANGE** | Preserved |
| Security Group | `sg-0e2c619a238e449df` | **NO CHANGE** | Preserved |
| ECR Repository | `nexvion-web` | **NO CHANGE** | Preserved |

---

## 6. Execution & Rollback Instructions

### Provisioning (Manual Execution):
```bash
cd terraform
terraform apply "phase-4-4-eks.tfplan"
```

### kubectl Kubeconfig Configuration:
```bash
aws eks update-kubeconfig --region ap-south-1 --name nexvion-eks
kubectl get nodes
```

### Rollback / Destruction Procedure (If required):
```bash
cd terraform
terraform destroy -target=aws_eks_node_group.nexvion -target=aws_eks_cluster.nexvion
```
