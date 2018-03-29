from proxmoxer import ProxmoxAPI
import netifaces
import os
from subprocess import call
import sys

# send prints to a log file
sys.stdout = open('whoami.log', 'w')
# vars
host_pool = [
  '32.32.0.3',
  '32.32.0.4',
  '32.32.0.5',
  '32.32.0.6'
]
user = 'root@pam'
password = '!kF78afer'
proxmox = None
hostname = ''

# pull in the mac address for eth0
mac_addr_eth0 = netifaces.ifaddresses('eth0')[netifaces.AF_LINK][0]['addr']
print('MAC addr: ' + mac_addr_eth0)

# establish a management connection to a proxmox host
for ip in host_pool:
  try:
    proxmox = ProxmoxAPI(ip, user=user, password=password, verify_ssl=False)
    print('Management connection established to: ' + ip)
    break
  except TimeoutError as t:
    print(t)

# make sure we were able to connect
if not proxmox:
  print('Oh no, we failed to connect :(')
else:
  # iterate through all vms on all nodes to find the one which has the same MAC address we do
  for node in proxmox.cluster.config.nodes.get():
    print('Checking ' + node['name'])
    for vm in proxmox.nodes(node['name']).qemu.get():
      vm_name = vm['name']
      vm_config = proxmox.nodes(node['name']).qemu(vm['vmid']).config.get()
      print('Found vm with name: ' + vm['name'] + ' and net0: ' + vm_config['net0'])
      if mac_addr_eth0.lower() in vm_config['net0'].lower():
        # set the hostname of the system to the vm_name given in proxmox
        print('Found a MAC match')
        hostname = vm_name
        call('hostnamectl', 'set-hostname', hostname, '--static')
        print('Set the system hostname to: ' + hostname)
        break
    if hostname:
      break

  # update ifcfg-eth0 with new hostname
  with open('/etc/sysconfig/network-scripts/ifcfg-eth0', 'r') as file :
    filedata = file.read()
  filedata = filedata.replace('REPLACE_ME', hostname)
  with open('/etc/sysconfig/network-scripts/ifcfg-eth0', 'w') as file:
    file.write(filedata)
  print('Rewrote ifcfg-eth0 with new hostname')

  # restart network so that Hostname is pushed to the DHCP server
  call(["systemctl", "restart", "network"])
  print('Restarted network')
