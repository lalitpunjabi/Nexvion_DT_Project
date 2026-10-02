# Nexvion Configuration Management (Ansible)

This module provides idempotent Ansible playbooks and roles for configuring an EC2 Linux instance running the **Nexvion DevOps & Staging Environment**.

## Roles Overview
- **`common`**: Updates system package index, configures UTC timezone, installs base tools (`curl`, `git`, `jq`, `ufw`), creates `/opt/nexvion`.
- **`docker`**: Detects existing Docker Engine, installs Docker Compose plugin if needed, configures log rotation (`10m`, 3 files), adds `ubuntu` & `jenkins` to `docker` group.
- **`jenkins`**: Detects existing Jenkins service, installs Java OpenJDK 17 LTS, ensures service enabled/active on port 8080, grants `jenkins` user access to Docker daemon socket.
- **`security`**: System hardening via `sysctl` (`net.ipv4.tcp_syncookies=1`), ensures SSH port 22 is allowed before enabling UFW firewall for ports `22`, `80`, `443`, `8080` (Jenkins), and `8081` (Nexvion Staging).

## Setup & Execution Workflow

### 1. Local Inventory Setup
Copy the inventory template to create your local `hosts.ini` (which is excluded from Git tracking via `.gitignore`):

```bash
cp inventory/hosts.ini.example inventory/hosts.ini
```

### 2. SSH Key Requirement
Ensure your EC2 SSH private key (`Nexvion.pem`) is located at `~/.ssh/Nexvion.pem` with restricted read-only permissions:

```bash
chmod 400 ~/.ssh/Nexvion.pem
```

### 3. Connectivity Ping Test
Test SSH connectivity and Python interpreter availability on the target server:

```bash
ansible -i inventory/hosts.ini nexvion_servers -m ping
```

### 4. Playbook Syntax Validation
Verify syntax correctness across all playbooks and roles:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/site.yml --syntax-check
```

### 5. Dry-Run Check Mode
Run dry-run simulation to review planned configuration changes without modifying live server state:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/site.yml --check
```

### 6. Live Playbook Execution
After reviewing check-mode output, apply server configuration changes:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/site.yml
```
