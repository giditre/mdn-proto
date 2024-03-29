#!/bin/bash

{
/usr/bin/flock -xn 9 || exit 1

DEFAULT_CONTROLLER="tcp:127.0.0.1:6633"
DEFAULT_LISTEN="ptcp:6634"
DEFAULT_OFv="OpenFlow13"

# Strictly left (lower) triangular matrix in Bash specifying the OVS topology
SW=(
[0]=""
)

# Hosts and their connections with OVS instances
HOSTS=(
[0]="1"
[1]="1"
)

# The number of OVS instances
N=`expr "${#SW[@]}" - 1`

# The number of host instances
M=`expr "${#HOSTS[@]}" - 1`

for i in $(eval echo {0..$N})
do
    CONTROLLER[$i]=$DEFAULT_CONTROLLER
    LISTEN[$i]=$DEFAULT_LISTEN
    OFv[$i]=$DEFAULT_OFv
done

# If you want something different than values specified in DEFAULT_CONTROLLER, DEFAULT_LISTEN and DEFAULT_OFv
# for one or more OVS instances, this is the place make that change. For example:

# CONTROLLER[7]="tcp:147.91.1.83:6699"
# LISTEN[5]="ptcp:6635"
# OFv[4]="OpenFlow14"

############# trap and clean-up ############################

function clean_up {

N=$1
for i in $(eval echo {00..$N}); do ovs-vsctl del-br sw$i ; done

for i in $(eval echo {00..$N})
do
    for j in $(eval echo {00..$N})
    do
        if [ "$i" -gt "$j" ]
        then
            NUM_OF_CABLES=$(echo ${SW[$i]} | cut -d' ' -f`expr $j + 1`) # Practically NUM_OF_CABLES=SW[i][j]
            if [ "$NUM_OF_CABLES" != "0" ]
            then
                for k in $(eval echo {1..$NUM_OF_CABLES})
                do
                    ip link delete dev c.sw$i-sw$j.$k
                done
            fi
        fi
    done
done

M=$2
for i in $(eval echo {00..$M})
do
    ip netns del Host-$i
done

}

trap "clean_up $N $M" EXIT

##################### end trap #############################

sleep 3 # sometimes needed for /etc/rc.local

echo -e "\n(Re-)creating OVS instances..."
for i in $(eval echo {00..$N}); do ovs-vsctl -- --id=@sw$ic0 create Controller target=\"${CONTROLLER[$i]}\" max_backoff=1000 -- --id=@sw$i-listen create Controller target=\"${LISTEN[$i]}\" max_backoff=1000 -- --if-exists del-br sw$i -- add-br sw$i -- set bridge sw$i controller=[@sw$ic0,@sw$i-listen] other_config:datapath-id=00000000000000$i fail_mode=secure other-config:disable-in-band=true protocols=${OFv[$i]}; done
echo "The list of OVS instances is: "`ovs-vsctl list-br | tr '\n' ' '`

echo -e "\nInstantiating virtual crossover cables..."
for i in $(eval echo {00..$N})
do
    for j in $(eval echo {00..$N})
    do
        if [ "$i" -gt "$j" ]
        then
            NUM_OF_CABLES=$(echo ${SW[$i]} | cut -d' ' -f`expr $j + 1`) # Practically NUM_OF_CABLES=SW[i][j]
            if [ "$NUM_OF_CABLES" != "0" ]
            then
                for k in $(eval echo {1..$NUM_OF_CABLES})
                do
                    ip link add name c.sw$i-sw$j.$k type veth peer name c.sw$j-sw$i.$k
                    ip link set c.sw$i-sw$j.$k up
                    ip link set c.sw$j-sw$i.$k up
                done
            fi
        fi
    done
done

echo -e "\nConnecting OVS instances to each other...\n"
for i in $(eval echo {00..$N})
do
    for j in $(eval echo {00..$N})
    do
        if [ "$i" -gt "$j" ]
        then
            NUM_OF_CABLES=$(echo ${SW[$i]} | cut -d' ' -f`expr $j + 1`) # Practically NUM_OF_CABLES=SW[i][j]
            if [ "$NUM_OF_CABLES" != "0" ]
            then
                for k in $(eval echo {1..$NUM_OF_CABLES})
                do
                    ovs-vsctl add-port sw$i c.sw$i-sw$j.$k -- set Interface c.sw$i-sw$j.$k ofport_request=1
                    ovs-vsctl add-port sw$j c.sw$j-sw$i.$k -- set Interface c.sw$j-sw$i.$k ofport_request=1
                done
            fi
        fi
    done
done

echo -e "Creating hosts...\n"
for i in $(eval echo {00..$M})
do
    ip netns add Host-$i
done

echo -e "Creating and connecting virtual patch cables...\n"
for i in $(eval echo {00..$M})
do
    for j in $(eval echo {00..$N})
    do
        NUM_OF_CABLES=$(echo ${HOSTS[$i]} | cut -d' ' -f`expr $j + 1`) # Practically NUM_OF_CABLES=HOSTS[i][j]
        if [ "$NUM_OF_CABLES" != "0" ]
        then
            for k in $(eval echo {1..$NUM_OF_CABLES})
            do
                ip link add c.sw$j-host$i.$k type veth peer name c.host$i-sw$j.$k
                ip link set c.sw$j-host$i.$k up
                ip link set c.host$i-sw$j.$k up
                ip link set c.sw$j-host$i.$k netns Host-$i
                ovs-vsctl add-port sw$j c.host$i-sw$j.$k
            done
        fi
    done
done

# Hosts are implemented using namespaces. See ip-netns(8) for more details. For example:
# ip netns exec Host-01 ifconfig c.sw02-host01.2 192.168.0.1 netmask 255.255.255.0
# You can even get the full access to the host by running the shell of your choice:
# ip netns exec Host-03 bash
# ifconfig 192.168.0.3 netmask 255.255.255.0
# exit # To leave the host

echo "Press Ctrl-C to exit..."

while : ; do sleep 1 ; done

exit 0

} 9>/var/lock/ovs-mesh.lock

