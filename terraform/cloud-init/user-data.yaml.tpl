#cloud-config
hostname: ${hostname}
fqdn: ${hostname}.iac.local
manage_etc_hosts: true

users:
  - name: debian
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    lock_passwd: true
    ssh_authorized_keys:
      - ${ssh_key}

ssh_pwauth: false
disable_root: true

package_update: true
packages:
  - qemu-guest-agent
  - python3

runcmd:
  - systemctl enable --now qemu-guest-agent