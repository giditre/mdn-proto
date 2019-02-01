#!/bin/bash

if [[ $(id -u) -ne 0 ]] ; then echo "Please run as root" ; exit 1 ; fi

if [[ -z $1 ]]; then
  echo "Provide switch list."
  exit 1
fi

# get sw_list from command line arguments
sw_list=$1

# sw_list=$(ovs-vsctl show | grep -o -E "sw[0-9]+" | sort | uniq)

for sw_name in $sw_list; do
  line=$(ovs-ofctl -O OpenFlow13 dump-ports-desc $sw_name | grep -o -E "[0-9]+\(c\.($sw_name|host[0-9]+)-($sw_name|host[0-9]+)\.[0-9]+\)" | grep -E "host.*\.1")
  host_name=$(echo $line | grep -o -E "host[0-9]+")
  host_number=$(echo $host_name | grep -o -E "[0-9]+")
  host_netns_name="Host-$host_number"
  host_iface_name="c.$sw_name-$host_name.1"
  host_iface_mac=$(ip netns exec $host_netns_name cat /sys/class/net/$host_iface_name/address)
  host_port_number=$(echo $line | grep -o -E "^[0-9]+")
  printf "Interface %s of host %s having MAC address %s is attached to switch %s on port number %s\n" "$host_iface_name" "$host_netns_name" "$host_iface_mac" "$sw_name" "$host_port_number"
  # enable ip_forward /proc/sys/net/ipv4/ip_forward on player hosts
  ip netns exec $host_netns_name sysctl -w net.ipv4.ip_forward=1
  # disable ICMP redirect messages on player hosts
  # need to edit both all and interface-specific flags, as they are in logical OR
  ip netns exec $host_netns_name sysctl -w net.ipv4.conf.all.send_redirects=0
  # if $host_iface_name is c.sw01-host01.1 then ${host_iface_name//.//} is c/sw01-host01/1
  ip netns exec $host_netns_name sysctl -w net.ipv4.conf.${host_iface_name//.//}.send_redirects=0
  #ip netns exec $host_netns_name sysctl -w net.ipv4.conf.all.accept_redirects=0
  # ip netns exec $host_netns_name sysctl -w net.ipv4.conf.default.send_redirects=0
  # inject appropriate flow rules with Ryu
  in_port=1
  dpid=$(echo $sw_name | grep -o -E "[1-9]+")
  priority=1234
  curl -X POST -d '{"match":{"eth_type":2048,"in_port":'"$in_port"'},"actions":[{"type":"SET_FIELD","field":"eth_dst","value":"'"$host_iface_mac"'"},{"type":"OUTPUT","port":"'"$host_port_number"'"}],"dpid":'"$dpid"',"priority":'"$priority"'}' http://127.0.0.1:8080/stats/flowentry/add
  # TODO use iptables to drop all traffic that is handled by the Scapy script (if any)
done

