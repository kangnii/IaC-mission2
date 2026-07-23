resource "ansible_host" "vm" {
  for_each = var.vms
  name     = each.key
  groups   = ["role_${each.key}"]

  variables = {
    ansible_host = each.value.ip
    ansible_user = "debian"
  }
}