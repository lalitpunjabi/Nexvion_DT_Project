# Nexvion Infrastructure as Code (Terraform)

This module adopts and declaratively manages the active AWS infrastructure for the **Nexvion DevOps & Cloud-Native Delivery Platform**.

## Infrastructure Adoption & Resource Mapping

Terraform uses native HCL `import` blocks to adopt existing AWS resources into the state management workflow without creating duplicate infrastructure or recreating active compute resources:

- **EC2 Instance:** `i-057f6d6d0bbb33b37` (`t3.small`, Ubuntu `ami-01a00762f46d584a1`, Name tag: `Nexvion`).
- **Elastic IP:** `52.66.25.69` (Allocation ID: `eipalloc-0662e014367e516bf`, Association ID: `eipassoc-0dfe320300f89e0da`).
- **VPC Network:** `vpc-09df3f5fdabdcf81f` (`172.31.0.0/16`) with public subnet `subnet-048f480df580a47f8` (`172.31.0.0/20`, AZ: `ap-south-1b`).
- **Internet Gateway:** `igw-045a89bde29483b3a`.
- **Main Route Table:** `rtb-0b5c00adb98133d97`.
- **Security Group (`launch-wizard-9`):** `sg-0e2c619a238e449df` with ingress rules for SSH (`22`), HTTP (`80`), HTTPS (`443`), Jenkins GUI (`8080`), and Nexvion Staging App (`8081`).

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
> `terraform plan` results in `0 to add, 0 to destroy` — guaranteeing non-destructive management of the active EC2 server `i-057f6d6d0bbb33b37` and Elastic IP `52.66.25.69`.
