#!/bin/bash

iface_name=$(ls /sys/class/net | grep -o -E "c\.sw[0-9]+-host[0-9]+\.1")
iface_mac=$(cat /sys/class/net/$iface_name/address)

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

python3 $script_dir/player01.py $iface_name $iface_mac

