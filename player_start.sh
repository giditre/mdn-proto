#!/bin/bash

[ "$#" -lt 2 ] && echo "Usage: $0 <PLAYER-VERSION> <DATA-SW-NAME>" && exit 1

player_version=$(printf "%02d" $1)
data_sw_name=$2
shift 2

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
py_file_name="$script_dir/player$player_version.py"
[ ! -f $py_file_name ] && echo "Error: file $py_file_name does not exist." && exit 1

iface_name=$(ls /sys/class/net | grep -o -E "c\.${data_sw_name}-host[0-9]+\.1")
iface_mac=$(cat /sys/class/net/$iface_name/address)

python3 $py_file_name $iface_name $iface_mac "$@"

