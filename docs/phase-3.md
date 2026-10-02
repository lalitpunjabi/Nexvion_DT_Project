# Nexvion Phase 3 — Infrastructure as Code (Terraform) & Configuration Management (Ansible)

## 1. Phase 3 Objective
Phase 3 establishes automated Infrastructure as Code (IaC) and Configuration Management directly mapping the active reference AWS EC2 environment (`i-057f6d6d0bbb33b37`).
- **Terraform** imports and models the existing AWS infrastructure (VPC, Subnet, Internet Gateway, Main Route Table, Security Group `launch-wizard-9`, and EC2 instance `i-057f6d6d0bbb33b37`).
- **Ansible** automates OS configuration, package installation, Docker Engine runtime, Jenkins LTS service, and server hardening on the live EC2 server (`15.207.89.170`).
- **Reference Protection:** The active EC2 instance running Jenkins (port 8080) and Nexvion Staging (port 8081) is strictly preserved without destructive recreation or replacement.

---

## 2. Discovered AWS Infrastructure Architecture

| Component | Resource ID / Identifier | Attributes |
| :--- | :--- | :--- |
| **AWS Region** | `ap-south-1` | Mumbai |
| **EC2 Instance** | `i-057f6d6d0bbb33b37` | `t3.small`, Ubuntu (`ami-01a00762f46d584a1`), Public IP: `15.207.89.170`, Private IP: `172.31.7.121` |
| **VPC** | `vpc-09df3f5fdabdcf81f` | CIDR: `172.31.0.0/16` |
| **Subnet** | `subnet-048f480df580a47f8` | CIDR: `172.31.0.0/20`, AZ: `ap-south-1b`, MapPublicIp: `true` |
| **Internet Gateway** | `igw-045a89bde29483b3a` | Attached to `vpc-09df3f5fdabdcf81f` |
| **Main Route Table** | `rtb-0b5c00adb98133d97` | Routes `0.0.0.0/0` -> `igw-045a89bde29483b3a`, `172.31.0.0/16` -> `local` |
| **Security Group** | `sg-0e2c619a238e449df` | Name: `launch-wizard-9`, Ingress TCP: `22`, `80`, `443`, `8080`, `8081` |
| **Key Pair** | `Nexvion` | Private Key: `~/.ssh/Nexvion.pem` |
| **Root Volume** | `vol-0e9b5502eeb28a762` | 20 GB `gp3`, `/dev/sda1`, Encrypted: `false` |

---

## 3. Ansible Architecture & Idempotency Controls
- **Target Host:** `15.207.89.170` (`ubuntu` user, SSH key `~/.ssh/Nexvion.pem`).
- **Idempotency Strategy:** Playbooks check existing binary paths (`which docker`, `which jenkins`) before modifying services to avoid service downtime or data overwrite.
- **Role Breakdown:**
  1. `common`: OS package update cache, UTC timezone, base packages (`curl`, `git`, `jq`, `ufw`), deployment path `/opt/nexvion`.
  2. `docker`: Checks existing installation, configures `/etc/docker/daemon.json` log limits (`10m`, 3 log files limit), adds `ubuntu` & `jenkins` users to `docker` group.
  3. `jenkins`: Checks existing Jenkins service, installs Java OpenJDK 17 LTS if missing, ensures service state is enabled and active on port 8080.
  4. `security`: Hardens kernel network via `sysctl` (`net.ipv4.tcp_syncookies = 1`), configures UFW firewall for ports `22`, `80`, `443`, `8080`, and `8081`.

---

## 4. Directory Structure

```
Nexvion_DT_Project/
├── terraform/
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── .gitignore
│   └── README.md
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/
│   │   ├── hosts.ini
│   │   └── hosts.ini.example
│   ├── playbooks/
│   │   └── site.yml
│   ├── roles/
│   │   ├── common/
│   │   │   ├── defaults/main.yml
│   │   │   └── tasks/main.yml
│   │   ├── docker/
│   │   │   ├── defaults/main.yml
│   │   │   ├── tasks/main.yml
│   │   │   └── handlers/main.yml
│   │   ├── jenkins/
│   │   │   ├── defaults/main.yml
│   │   │   └── tasks/main.yml
│   │   └── security/
│   │       ├── defaults/main.yml
│   │       └── tasks/main.yml
│   ├── group_vars/
│   │   └── all.yml.example
│   └── README.md
```

---

## 5. Required AWS Prerequisites
1. **AWS CLI v2** installed and authenticated (`aws configure`).
2. **Target EC2 Key Pair (`Nexvion.pem`)** downloaded and stored at `~/.ssh/Nexvion.pem` with `chmod 400` permissions.
3. **AWS Credentials** with permissions to read EC2, VPC, Subnet, Route Table, and Security Group details.

---

## 6. Required IAM Permissions
- `ec2:DescribeInstances`, `ec2:DescribeVpcs`, `ec2:DescribeSubnets`, `ec2:DescribeSecurityGroups`, `ec2:DescribeInternetGateways`, `ec2:DescribeRouteTables`.

---

## 7. Terraform Import & Execution Commands

```bash
cd terraform

# 1. Format code
terraform fmt -recursive

# 2. Initialize provider
terraform init

# 3. Validate HCL syntax
terraform validate

# 4. Generate plan matching existing resources via import blocks
terraform plan
```

---

## 8. Ansible Commands

```bash
cd ansible

# 1. Test SSH ping connectivity
ansible -i inventory/hosts.ini nexvion_servers -m ping

# 2. Validate playbook syntax
ansible-playbook -i inventory/hosts.ini playbooks/site.yml --syntax-check

# 3. Execute dry-run check against live EC2 instance
ansible-playbook -i inventory/hosts.ini playbooks/site.yml --check
```

---

## 9. Inventory Configuration (`ansible/inventory/hosts.ini`)

```ini
[nexvion_servers]
nexvion-ec2-staging ansible_host=15.207.89.170 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/Nexvion.pem

[nexvion_servers:vars]
ansible_python_interpreter=/usr/bin/python3
```

---

## 10. Security Considerations
- **No Secrets Committed:** Private key `Nexvion.pem`, `terraform.tfstate`, `.terraform/`, and `hosts.ini` are explicitly ignored by `.gitignore`.
- **Existing Security Group Ingress:** Restricted to standard web/management ports (`22`, `80`, `443`, `8080`, `8081`).
- **Server Hardening:** TCP SYN flood protection enabled via sysctl (`net.ipv4.tcp_syncookies = 1`).

---

## 11. What is Automated
- Terraform import and declarative mapping of active AWS EC2 server `i-057f6d6d0bbb33b37` and networking stack.
- Ansible automated ping connectivity, package management, Docker Engine setup, Jenkins service verification, and sysctl hardening.

---

## 12. What Remains Manual
- Workstation AWS CLI credential management (`aws configure`).
- AWS EC2 Key Pair management (`Nexvion.pem`).

---

## 13. Validation Results

| Component | Tool / Command | Result | Status |
| :--- | :--- | :---: | :---: |
| **AWS CLI Discovery** | `aws ec2 describe-instances` | Extracted `i-057f6d6d0bbb33b37` (`15.207.89.170`) | **PASS** |
| **Terraform Syntax Check** | `terraform validate` | `Success! The configuration is valid.` | **PASS** |
| **Terraform Plan (Import)** | `terraform plan` | `Plan: 6 to import, 0 to add, 6 to change, 0 to destroy.` | **PASS** |
| **Ansible Ping Check** | `ansible -m ping` | `SUCCESS => {"ping": "pong"}` | **PASS** |
| **Ansible Playbook Syntax** | `ansible-playbook --syntax-check` | Clean Syntax | **PASS** |
| **Live Jenkins GUI** | `http://15.207.89.170:8080` | Active | **PASS** |
| **Live Nexvion Web App** | `http://15.207.89.170:8081/healthz` | `HTTP 200 OK` | **PASS** |

---

## 14. Relationship Between Terraform, Ansible, and Jenkins

```
┌────────────────────────────────────────────────────────────────────────┐
│ TERRAFORM (Infrastructure Declarative Mapping)                         │
│ Imports & manages existing AWS VPC, Subnet, IGW, SG, and EC2           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Host IP: 15.207.89.170)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ANSIBLE (Server Configuration Management)                              │
│ Configures OS, hardening, verifies Docker Engine, Compose & Jenkins    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Running Engine & CI/CD Controller)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ JENKINS (CI/CD Pipeline Orchestration)                                 │
│ Runs GitLeaks, Docker Build, Trivy scanning, Staging Compose Deploy    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 15. How Phase 3 Connects to Jenkins
Terraform and Ansible validate infrastructure and server configuration without disturbing live services:
- Stage 2 (`Validate`) in `Jenkinsfile` runs non-destructive `terraform validate` and `ansible-playbook --syntax-check`.
- `terraform plan` verifies zero resource replacements (`0 to add, 0 to destroy`).
- Phase 2 core workflow (`Checkout` -> `Validate` -> `Secret Scan` -> `Docker Build` -> `Image Scan` -> `Staging Deployment` -> `Health Check`) remains 100% operational.
