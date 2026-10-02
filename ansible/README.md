# Nexvion Configuration Management (Ansible)

This module provides idempotent Ansible playbooks and roles for configuring an EC2 Linux instance running the **Nexvion DevOps & Staging Environment**.

## Roles Overview
- **`common`**: Updates system package index, configures UTC timezone, installs base tools (`curl`, `git`, `jq`, `ufw`), creates `/opt/nexvion`.
- **`docker`**: Detects existing Docker Engine, installs Docker Compose plugin if needed, configures log rotation (`10m`, 3 files), adds `ubuntu` & `jenkins` to `docker` group.
- **`jenkins`**: Detects existing Jenkins service, installs Java OpenJDK 17 LTS, ensures service enabled/active on port 8080, grants `jenkins` user access to Docker daemon socket.
- **`security`**: System hardening via `sysctl` (`net.ipv4.tcp_syncookies=1`), ensures SSH port 22 is allowed before enabling UFW firewall for ports `22`, `80`, `443`, `8080` (Jenkins), and `8081` (Nexvion Staging).

## Setup & Execution Workflow

Follow this 7-step workflow safely:

1. **Copy Inventory Template:**
   Copy the example inventory template to create your active `hosts.ini` (git-ignored):
   ```bash
   cp inventory/hosts.ini.example inventory/hosts.ini
   ```

2. **Configure SSH Key:**
   Ensure your AWS EC2 SSH key (`Nexvion.pem`) is placed at `~/.ssh/Nexvion.pem` with strict permissions:
   ```bash
   chmod 400 ~/.ssh/Nexvion.pem
   ```

3. **Test Connectivity:**
   Verify SSH connectivity and Python availability on the target host:
   ```bash
   ansible -i inventory/hosts.ini nexvion_servers -m ping
   ```

4. **Run Syntax Check:**
   Validate playbook and role syntax without connecting to host:
   ```bash
   ansible-playbook -i inventory/hosts.ini playbooks/site.yml --syntax-check
   ```

5. **Run Check Mode:**
   Perform a dry-run check mode simulation:
   ```bash
   ansible-playbook -i inventory/hosts.ini playbooks/site.yml --check
   ```

6. **Review Changes:**
   Carefully review all planned changes output by the check-mode dry-run to ensure no unexpected modifications will take place.

7. **Execute Live Playbook:**
   Only after reviewing check-mode output and confirming safety, execute the live playbook:
   ```bash
   ansible-playbook -i inventory/hosts.ini playbooks/site.yml
   ```

