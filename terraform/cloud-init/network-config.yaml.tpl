version: 2
ethernets:
  ens3:
    dhcp4: false
    addresses:
      - ${ip}/${prefix}
    gateway4: ${gateway}
    nameservers:
      addresses: [8.8.8.8, 1.1.1.1]