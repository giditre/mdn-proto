#!/bin/bash

# if [[ -z $1 ]]; then
#   echo "Provide switch list."
#   exit 1
# fi

# get sw_list from command line arguments
echo "Get list of hosts..."
host_list=$(ip netns | grep -o -E "Host-[0-9]+" | sort | tr "\n" " ")
echo "Discovered hosts: $host_list"
echo

# sw_list=$(ovs-vsctl show | grep -o -E "sw[0-9]+" | sort | uniq)

for host_netns_name in $host_list; do
  host_name=$(echo $host_netns_name | tr "[:upper:]" "[:lower:]" | tr -d "-")
  host_number=$(echo $host_name | grep -o -E "[0-9]+")
  host_iface_name=$(ip netns exec $host_netns_name ls /sys/class/net/ | grep -o -E "c\.sw[0-9]+-$host_name.1")
  if [[ -z $host_iface_name ]]; then
    echo "Error: no interface found for host $host_name"
    exit 1
  fi
  host_iface_mac=$(ip netns exec $host_netns_name cat /sys/class/net/$host_iface_name/address)
  printf "Found interface %s of host %s having MAC address %s\n" "$host_iface_name" "$host_netns_name" "$host_iface_mac"
  # disable IPv6 on all interfaces of host
  echo "Disable IPv6..."
  ip netns exec $host_netns_name sysctl -w net.ipv6.conf.all.disable_ipv6=1
  # assign IPv4 address to interface
  address="192.168.27.$((100+$host_number))/24"
  echo "Assign IPv4 address $address to interface $host_iface_name..."
  ip netns exec $host_netns_name ip addr add $address dev $host_iface_name
  # bring interface up
  echo "Bring interface up..."
  ip netns exec $host_netns_name ip link set $host_iface_name up
  # make every host emit something to notify Ryu they're there
  echo "Send a packet... "
  #( sleep 5; ip netns exec $host_netns_name echo -e $(date) | nc -u -w 1 192.168.27.254 55934 ) &
  ( sleep 5; ip netns exec $host_netns_name arping -b -c 1 -w 1 -I $host_iface_name 1.2.3.4 ) & echo $! >> /tmp/$0.pidlist
  echo
  sleep 3
done

while ps $(cat /tmp/$0.pidlist); do
  sleep 1
done

rm /tmp/$0.pidlist

echo "Done."
