variable "network_name" {
  description = "Nom du réseau privé libvirt"
  type        = string
  default     = "iac-net"
}

variable "network_cidr" {
  description = "Plage d'adressage du réseau privé"
  type        = string
  default     = "192.168.100.0/24"
}

variable "base_image_path" {
  description = "Chemin vers l'image cloud de base (qcow2)"
  type        = string
  default     = "/var/lib/libvirt/images/debian-12-base.qcow2"
}

variable "ssh_public_key" {
  description = "Clé publique SSH injectée dans les VM via cloud-init"
  type        = string
}

variable "vms" {
  description = "Définition des VM à créer"
  type = map(object({
    memory = number # Mo
    vcpu   = number
    ip     = string
  }))
  default = {
    bastion = { memory = 1024, vcpu = 1, ip = "192.168.100.10" }
    web     = { memory = 2048, vcpu = 2, ip = "192.168.100.20" }
    db      = { memory = 2048, vcpu = 2, ip = "192.168.100.30" }
  }
}
