# TODO jour 2 : boucle for_each sur var.vms
# - libvirt_cloudinit_disk (injecte clé SSH + IP statique)
# - libvirt_domain (VM) rattaché au réseau privé

resource "libvirt_cloudinit_disk" "init" {
  for_each = var.vms
  name     = "${each.key}-cloudinit.iso"
  pool     = "default"

  user_data = templatefile("${path.module}/cloud-init/user-data.yaml.tpl", {
    hostname = each.key
    ssh_key  = var.ssh_public_key
  })

  network_config = templatefile("${path.module}/cloud-init/network-config.yaml.tpl", {
    ip      = each.value.ip
    prefix  = split("/", var.network_cidr)[1]
    gateway = cidrhost(var.network_cidr, 1)
  })
}

resource "libvirt_volume" "vm_disk" {
  for_each       = var.vms
  name           = "${each.key}.qcow2"
  pool           = "default"
  base_volume_id = libvirt_volume.base.id
  format         = "qcow2"
}

resource "libvirt_domain" "vm" {
  for_each = var.vms

  name   = each.key
  memory = each.value.memory
  vcpu   = each.value.vcpu

  cloudinit = libvirt_cloudinit_disk.init[each.key].id

  network_interface {
    network_id     = libvirt_network.private.id
    wait_for_lease = false
  }

  disk {
    volume_id = libvirt_volume.vm_disk[each.key].id
  }

  console {
    type        = "pty"
    target_type = "serial"
    target_port = "0"
  }

  graphics {
    type        = "vnc"
    listen_type = "address"
    autoport    = true
  }
}
