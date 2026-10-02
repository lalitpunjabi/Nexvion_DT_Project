# Nexvion Phase 3 — Infrastructure as Code (Terraform) & Configuration Management (Ansible)

---

## SECTION A: CURRENT CONFIGURATION

### 1. Overview & Objective
Phase 3 establishes automated Infrastructure as Code (IaC) and Configuration Management directly mapping the active reference AWS EC2 server (`i-057f6d6d0bbb33b37`).
- **Terraform:** Declaratively models and adopts the existing AWS infrastructure (VPC, Subnet, Internet Gateway, Main Route Table, Security Group `launch-wizard-9`, EC2 instance `i-057f6d6d0bbb33b37`, and Elastic IP `52.66.25.69`).
- **Ansible:** Automates OS configuration, official package repository setup, Docker Engine runtime, Jenkins LTS service, and server hardening on the live EC2 server via Elastic IP (`52.66.25.69`).
- **Reference Protection:** The active EC2 instance running Jenkins (port 8080) and Nexvion Staging (port 8081) is strictly preserved without destructive recreation or replacement.

### 2. Discovered AWS Infrastructure Architecture

| Component | Resource ID / Identifier | Attributes |
| :--- | :--- | :--- |
| **AWS Region** | `ap-south-1` | Mumbai |
| **EC2 Instance** | `i-057f6d6d0bbb33b37` | `t3.small`, Ubuntu (`ami-01a00762f46d584a1`), Tag Name: `Nexvion`, Private IP: `172.31.7.121` |
| **Elastic IP** | `52.66.25.69` | Allocation ID: `eipalloc-0662e014367e516bf`, Association ID: `eipassoc-0dfe320300f89e0da` |
| **VPC** | `vpc-09df3f5fdabdcf81f` | CIDR: `172.31.0.0/16` |
| **Subnet** | `subnet-048f480df580a47f8` | CIDR: `172.31.0.0/20`, AZ: `ap-south-1b`, MapPublicIp: `true` |
| **Internet Gateway** | `igw-045a89bde29483b3a` | Attached to `vpc-09df3f5fdabdcf81f` |
| **Main Route Table** | `rtb-0b5c00adb98133d97` | Routes `0.0.0.0/0` -> `igw-045a89bde29483b3a`, `172.31.0.0/16` -> `local` |
| **Security Group** | `sg-0e2c619a238e449df` | Name: `launch-wizard-9`, Ingress TCP: `22`, `80`, `443`, `8080`, `8081` |
| **Key Pair** | `Nexvion` | Private Key: `~/.ssh/Nexvion.pem` |
| **Root Volume** | `vol-0e9b5502eeb28a762` | 20 GB `gp3`, `/dev/sda1`, Encrypted: `false` |

### 3. Ansible Architecture & Role Specifications
- **Target Host:** `52.66.25.69` (`ubuntu` user, SSH key `~/.ssh/Nexvion.pem`).
- **Idempotency Strategy:** Playbooks gather package facts (`ansible.builtin.package_facts`) to detect existing installation packages before executing configuration tasks.
- **Role Breakdown:**
  1. `common`: OS package update cache, UTC timezone, base packages (`curl`, `git`, `jq`, `ufw`), deployment path `/opt/nexvion`.
  2. `docker`: Installs prerequisites, adds Docker official GPG key and APT repository, installs Docker Engine & Compose plugin, configures `/etc/docker/daemon.json` log limits (`10m`, 3 files), adds `ubuntu` & `jenkins` users to `docker` group.
  3. `jenkins`: Installs Java OpenJDK 17 LTS, adds Jenkins official GPG key & Debian repository, installs Jenkins package, ensures `jenkins` user is added to `docker` group with conditional service restart upon group change.
  4. `security`: Hardens kernel network via `sysctl` (`net.ipv4.tcp_syncookies = 1`), explicitly allows SSH port `22` in UFW before enabling, configures default incoming policy to `deny`, default outgoing to `allow`, and exposes ports `22`, `80`, `443`, `8080`, `8081`.

### 4. Directory & File Inventory

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
│   │   ├── hosts.ini (git-ignored live inventory)
│   │   └── hosts.ini.example (CI syntax-check template)
│   ├── playbooks/
│   │   └── site.yml
│   ├── roles/
│   │   ├── common/
│   │   ├── docker/
│   │   ├── jenkins/
│   │   └── security/
│   └── README.md
```

---

## SECTION B: VALIDATION PROCEDURE

### 1. Safe Terraform Validation Procedure
Execute the following non-destructive commands in the `terraform/` directory:
```bash
# 1. Format code check
terraform fmt -check -recursive

# 2. Initialize provider (without remote backend)
terraform init -backend=false

# 3. Validate HCL syntax and references
terraform validate

# 4. Generate plan matching existing resources via import blocks (local review only)
terraform plan
```
> [!IMPORTANT]
> `terraform plan` MUST be reviewed locally before any apply action. `terraform apply` is NEVER run automatically in CI.

### 2. Safe Ansible Validation Procedure
Execute the following commands in the `ansible/` directory:
```bash
# 1. Validate playbook syntax (using CI template inventory)
ansible-playbook -i inventory/hosts.ini.example playbooks/site.yml --syntax-check

# 2. Test live host connectivity (requires active hosts.ini & SSH key)
ansible -i inventory/hosts.ini nexvion_servers -m ping

# 3. Execute dry-run check mode (simulates changes without modifying target server)
ansible-playbook -i inventory/hosts.ini playbooks/site.yml --check
```

---

## SECTION C: ACTUAL VALIDATION RESULTS

The following results reflect empirical verification executed on the workspace environment:

| Component / Test | Command Executed | Empirical Result Observed | Status |
| :--- | :--- | :--- | :---: |
| **Terraform Code Format** | `terraform fmt -check -recursive` | Clean (0 unformatted files) | **PASS** |
| **Terraform Initialization** | `terraform init -backend=false` | Success! Initialized hashicorp/aws v5.100.0 | **PASS** |
| **Terraform Syntax Check** | `terraform validate` | `Success! The configuration is valid.` | **PASS** |
| **Terraform Plan (Import)** | `terraform plan` | `Plan: 8 to import, 0 to add, 7 to change, 0 to destroy.` | **PASS** |
| **Ansible Syntax Validation** | `ansible-playbook --syntax-check` | Clean syntax across all roles | **PASS** |
| **Ansible Host Ping** | `ansible -m ping` | `nexvion-ec2-staging \| SUCCESS => {"ping": "pong"}` | **PASS** |
| **Ansible Check Mode** | `ansible-playbook --check` | `PLAY RECAP: ok=22 changed=13 failed=0` | **PASS** |
| **Docker Compose Config** | `docker compose config` | Valid compose specification | **PASS** |
| **GitLeaks Secret Scan** | `gitleaks detect` | Scanned 943.89 KB; `no leaks found` | **PASS** |

---

## Relationship Between Terraform, Ansible, and Jenkins

```
┌────────────────────────────────────────────────────────────────────────┐
│ TERRAFORM (Infrastructure Declarative Mapping)                         │
│ Imports & manages existing AWS VPC, Subnet, IGW, SG, EIP & EC2         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Elastic IP: 52.66.25.69)
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

