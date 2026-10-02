# Nexvion Configuration Management (Ansible)

This module provides idempotent Ansible playbooks and roles for configuring an EC2 Linux instance running the **Nexvion DevOps & Staging Environment**.

## Roles Overview
- **`common`**: Updates system package index, configures UTC timezone, installs base tools (`curl`, `git`, `jq`, `ufw`), creates `/opt/nexvion`.
- **`docker`**: Installs Docker Engine, Docker Buildx, Docker Compose plugin, configures log rotation (`10m`, 3 files), adds `ubuntu` & `jenkins` to `docker` group.
- **`jenkins`**: Installs Java OpenJDK 17, Jenkins LTS service, grants `jenkins` user access to Docker daemon socket.
- **`security`**: System hardening via `sysctl` (`net.ipv4.tcp_syncookies=1`), UFW firewall rules for ports `22`, `80`, `443`, `8080` (Jenkins), and `8081` (Nexvion Staging).

## Validation Commands

```bash
# 1. Syntax validation
ansible-playbook --syntax-check playbooks/site.yml

# 2. Dry-run check against inventory example
ansible-playbook -i inventory/hosts.ini.example playbooks/site.yml --check
```
