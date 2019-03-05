#!/bin/bash

if [[ $(id -u) -ne 0 ]] ; then echo "Please run as root" ; exit 1 ; fi

# default values
def_data_net_base_address="192.168.27.100/24"
def_mdn_net_base_address="172.27.27.100/24"

usage() { 
  if [ "$#" -ne 0 ]; then echo "Error: $@"; fi
  echo "Usage: $0 [ -m MDN-SW-NAME ] [ -d DATA-NET-ADDRESS ($def_data_net_base_address) ] [ -c MDN-NET-ADDRESS ($def_mdn_net_base_address) ]" 1>&2
  exit 1
}

ipvalid() {
  # check if no argumet provided
  [ -z $1 ] && return 1
  # Set up local variables
  #local ip=${1:-1.2.3.4}
  local ip=${1%%/*}
  local mask=$( [[ $1 == */* ]] && echo ${1##*/} )
  local IFS=.
  local -a a=($ip)
  # perform regex format test
  [[ $ip =~ ^[0-9]+(\.[0-9]+){3}$ ]] || return 1
  # TODO correct behavior for which addresses with trailing '/' are recognized as valid
  # test values of quads
  local quad
  for quad in {0..3}; do
    [[ "${a[$quad]}" -gt 255 ]] && return 1
  done
  # test value of netmask
  [[ "$mask" ]] && [[ "$mask" -gt 32 ]] && return 1

  return 0
}

cidr() {
  local a=$1
  [[ ! $a == */* ]] && a="$a/24"
  echo $a
}

add_host_id() {
  local a=$1
  local h=$2
  local prefix=${a%*.*}
  local suffix=$(local tmp=${a##*.}; echo ${tmp%%/*})
  local mask=$( [[ $a == */* ]] && echo ${a##*/} )

  echo "$prefix.$(($suffix + ${h#0}))/$mask"
}

while getopts ":m:d:c:" o; do
  case "$o" in
    m)
      mdn_sw_name=$OPTARG
      [ -z $mdn_sw_name ] && usage "specify a valid switch name."
      ;;
    d)
      data_net_base_address=$OPTARG
      ! ipvalid "$data_net_base_address" && usage "invalid IP address $data_net_base_address ."
      data_net_base_address=$(cidr $data_net_base_address)
      ;;
    c)
      mdn_net_base_address=$OPTARG
      ! ipvalid "$mdn_net_base_address" && usage "invalid IP address $mdn_net_base_address ."
      mdn_net_base_address=$(cidr $mdn_net_base_address)
      ;;    
    ?)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

[ -z "$data_net_base_address" ] && data_net_base_address=$def_data_net_base_address
[ -z "$mdn_net_base_address" ] && mdn_net_base_address=$def_mdn_net_base_address

b=$(basename -- "$0")
script_name=$(echo "${b%.*}")

if [ -n $mdn_sw_name ]; then
  if ! grep $mdn_sw_name <<< $(ovs-vsctl list-br) >/dev/null 2>&1; then
    echo "$mdn_sw_name is not an active Open vSwitch."
    exit 1
  fi
fi

echo "Get list of hosts..."
host_list=$(ip netns | grep -o -E "Host-[0-9]+" | sort | tr "\n" " ")
echo "Discovered hosts: $host_list"
echo

# sw_list=$(ovs-vsctl show | grep -o -E "sw[0-9]+" | sort | uniq)

echo "### Assign addresses on the data network ###"
echo

addr_file_name="/tmp/${script_name}_addresses.tmp"
cat /dev/null > $addr_file_name
ext_hosts_file_name="/tmp/${script_name}_ext_hosts.tmp"
cat /dev/null > $ext_hosts_file_name 

for host_netns_name in $host_list; do
  host_name=$(echo $host_netns_name | tr "[:upper:]" "[:lower:]" | tr -d "-")
  host_number=$(echo $host_name | grep -o -E "[0-9]+")

  if [ -n $mdn_sw_name ]; then
    host_iface_name=$(ip netns exec $host_netns_name ls /sys/class/net/ | grep -o -E "c\.sw[0-9]+-$host_name.1" | grep -v $mdn_sw_name)
  else
    host_iface_name=$(ip netns exec $host_netns_name ls /sys/class/net/ | grep -o -E "c\.sw[0-9]+-$host_name.1")
  fi

  if [[ -z $host_iface_name ]]; then
    echo "Warning: no data network interface found for host $host_name."
    # add host to list of hosts external to the data network
    echo "$host_netns_name" >> $ext_hosts_file_name
    echo
    continue
  fi
  host_iface_mac=$(ip netns exec $host_netns_name cat /sys/class/net/$host_iface_name/address)
  printf "Found interface %s of host %s having MAC address %s\n" "$host_iface_name" "$host_netns_name" "$host_iface_mac"
  # disable IPv6 on all interfaces of host
  echo "Disable IPv6..."
  ip netns exec $host_netns_name sysctl -w net.ipv6.conf.all.disable_ipv6=1
  # assign IPv4 address to interface
  address="$(add_host_id $data_net_base_address $host_number)"
  echo "Assign IPv4 address $address to interface $host_iface_name..."
  echo "$host_netns_name,$(echo $address | cut -d'/' -f1)" >> $addr_file_name
  ip netns exec $host_netns_name ip addr add $address dev $host_iface_name
  # bring interface up
  echo "Bring interface up..."
  ip netns exec $host_netns_name ip link set $host_iface_name up
  echo
done

# make every host emit something to notify Ryu they're there
for host_netns_name in $host_list; do
  if grep $host_netns_name < $ext_hosts_file_name >/dev/null 2>&1; then
    # it means this host is not in the data network
    continue
  fi
  cat $addr_file_name | grep -v "$host_netns_name" | cut -d, -f2 | while read other_host_address; do
    while ! ip netns exec $host_netns_name ping -c1 -w1 $other_host_address >/dev/null 2>&1; do
      # echo "$host_netns_name awaits response from $other_host_address"
      continue
    done
  done
done & echo $! >> /tmp/$0_ping.pidlist

echo -n "Waiting for pingall success on the data network..."
while ps $(cat /tmp/$0_ping.pidlist) >/dev/null 2>&1; do
  echo -n "."
  sleep 1
done
rm /tmp/$0_ping.pidlist
echo
echo

if [ -n $mdn_sw_name ]; then

  echo "### Assign addresses on the MDN control network ###"
  echo
  
  addr_file_name="/tmp/${script_name}_mdncn_addresses.tmp"
  cat /dev/null > $addr_file_name
  ext_hosts_file_name="/tmp/${script_name}_mdncn_ext_hosts.tmp"
  cat /dev/null > $ext_hosts_file_name
  
  for host_netns_name in $host_list; do
    host_name=$(echo $host_netns_name | tr "[:upper:]" "[:lower:]" | tr -d "-")
    host_number=$(echo $host_name | grep -o -E "[0-9]+")
    host_iface_name=$(ip netns exec $host_netns_name ls /sys/class/net/ | grep -o -E "c\.sw[0-9]+-$host_name.1" | grep $mdn_sw_name)
    if [[ -z $host_iface_name ]]; then
      echo "Warning: no MDN control network interface found for host $host_name."
      # add host to list of hosts external to the data network
      echo "$host_netns_name" >> $ext_hosts_file_name
      echo
      continue
    fi
    host_iface_mac=$(ip netns exec $host_netns_name cat /sys/class/net/$host_iface_name/address)
    printf "Found interface %s of host %s having MAC address %s\n" "$host_iface_name" "$host_netns_name" "$host_iface_mac"
    # disable IPv6 on all interfaces of host
    echo "Disable IPv6..."
    ip netns exec $host_netns_name sysctl -w net.ipv6.conf.all.disable_ipv6=1
    # assign IPv4 address to interface
    address="$(add_host_id $mdn_net_base_address $host_number)"
    echo "Assign IPv4 address $address to interface $host_iface_name..."
    echo "$host_netns_name,$(echo $address | cut -d'/' -f1)" >> $addr_file_name
    ip netns exec $host_netns_name ip addr add $address dev $host_iface_name
    # bring interface up
    echo "Bring interface up..."
    ip netns exec $host_netns_name ip link set $host_iface_name up
    echo
  done
  
  # make every host emit something to notify Ryu they're there
  for host_netns_name in $host_list; do
    if grep $host_netns_name < $ext_hosts_file_name >/dev/null 2>&1; then
      # it means this host is not in the data network
      continue
    fi
    cat $addr_file_name | grep -v "$host_netns_name" | cut -d, -f2 | while read other_host_address; do
      while ! ip netns exec $host_netns_name ping -c1 -w3 $other_host_address >/dev/null 2>&1; do continue; done
    done
  done & echo $! >> /tmp/$0_ping.pidlist
  
  echo -n "Waiting for pingall success on the MDN control network..."
  while ps $(cat /tmp/$0_ping.pidlist) >/dev/null 2>&1; do
    echo -n "."
    sleep 1
  done
  rm /tmp/$0_ping.pidlist
  echo
  echo

fi

echo "Done."
echo

