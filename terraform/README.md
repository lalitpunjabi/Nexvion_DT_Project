# Nexvion Infrastructure as Code (Terraform)

This module models the active AWS infrastructure required for the **Nexvion DevOps & Cloud-Native Delivery Platform**.

## Discovered AWS Architecture & Mapped Resources
- **EC2 Instance:** `i-057f6d6d0bbb33b37` (`t3.small`, Ubuntu `ami-01a00762f46d584a1`, Name: `Nexvion`).
- **Elastic IP:** `52.66.25.69` (`eipalloc-0662e014367e516bf`, Association: `eipassoc-0dfe320300f89e0da`).
- **VPC & Subnet:** Existing VPC `vpc-09df3f5fdabdcf81f` (`172.31.0.0/16`) with subnet `subnet-048f480df580a47f8` (`172.31.0.0/20`).
- **Security Group (`launch-wizard-9`):** Ingress rules for SSH (`22`), HTTP (`80`), HTTPS (`443`), Jenkins GUI (`8080`), and Nexvion Staging App (`8081`).
- **Main Route Table:** `rtb-0b5c00adb98133d97`.

## Usage Commands

```bash
# 1. Format code
terraform fmt -recursive

# 2. Initialize provider and modules
terraform init

# 3. Validate syntax
terraform validate

# 4. Generate execution plan (Adopt existing resources via import blocks)
terraform plan
```

> [!NOTE]
> `terraform plan` results in `0 to add, 0 to destroy` — guaranteed non-destructive adoption of active EC2 server `i-057f6d6d0bbb33b37` and Elastic IP `52.66.25.69`.
