# TODO jour 2 : définir le réseau privé libvirt (libvirt_network)
# et le volume de base cloné pour chaque VM. 

resource "libvirt_network" "private" {
  name = var.network_name
  mode = "nat"
  domain = "iac.local"
  autostart = true
  addresses = [var.network_cidr]

    dhcp {
        enabled = false
    }

    dns {
        enabled = true
    }
}

resource "libvirt_volume" "base" {
  name   = "iac-base.qcow2"
  pool   = "default"
  source = var.base_image_path
  format = "qcow2"
}
