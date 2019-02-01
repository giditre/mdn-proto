#!/bin/bash

[ -z $1 ] && echo "Usage: $0 <DATA-SW-NAME>" && exit 1

data_sw_name=$1
shift

iface_name=$(ls /sys/class/net | grep -o -E "c\.${data_sw_name}-host[0-9]+\.1")
iface_mac=$(cat /sys/class/net/$iface_name/address)

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

python3 $script_dir/player02.py $iface_name $iface_mac "$@"

