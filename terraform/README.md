# Nexvion Infrastructure as Code (Terraform)

This module models the AWS infrastructure required for the **Nexvion DevOps & Cloud-Native Delivery Platform**.

## Architecture & Components
- **VPC & Subnet:** Dedicated VPC (`10.0.0.0/16`) with a public subnet (`10.0.1.0/24`), Internet Gateway, and Route Table.
- **Security Group (`nexvion-sg`):** Ingress rules for SSH (22), HTTP (80), HTTPS (443), Jenkins GUI (8080), and Nexvion Staging App (8081).
- **Compute Instance:** Ubuntu 22.04 LTS EC2 (`t3.small`) with an encrypted 20 GB `gp3` root volume.
- **IAM Role:** EC2 Instance Profile with `AmazonEC2ContainerRegistryReadOnly` policy for secure credential-less ECR authentication.

## Usage Commands

```bash
# 1. Format code
terraform fmt -recursive

# 2. Initialize provider and modules
terraform init

# 3. Validate syntax
terraform validate

# 4. Generate execution plan
terraform plan
```

> [!NOTE]
> Do not execute `terraform apply` or `terraform destroy` on the active reference EC2 instance.
