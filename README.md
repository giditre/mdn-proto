
## Layout of the Repository

mdn-proto

musicproto.py is the file with the definition of the MDN packets and all the functions needed for the execution of the protocol (proof of concept implementation)

mpsoundlib.py is an auxiliary library for the handling of actual sounds, as sent and received through the sounddevice module.

mpsoundlib.py is an auxiliary library for the handling of "emulated" sounds, used to test the protocol without actually producing hearable sound. "Emulated" sounds are just sequence of samples, generated programmatically, which represent the same samples one would obtain by sampling a sound captured via an audio interface.

In order to handle vibrations, we could write another auxiliary library, similar to mpsoundlib, that is capable of handling vibrations and exposes the functions send and receive (similarly to mpsoundlib) so that the integration with the existing code would be as smooth as possible.

player*.py and conductor*.py (* representing the version number) are the files with the PoC implementation of the behavior of the two MDN entities (conductor and player). Highest number means most recent version - just consider most recent version, the others are there only in case of need to rollback.
Run the help function to understand which parameters are required. For example, to run the help function of conductor09.py, run:

  pyhton3 conductor09.py --help

Examples of invocation of conductor and player:

  python3 conductor09.py --cond-ip 172.27.27.109 --cond-port 30000

  python3 player09.py eth0 b1:55:50:eb:e2:96 p1 --cond-ip 172.27.27.109 --cond-port 30000 --play-ip 172.27.27.102

where the conductor's interface has been previously assigned IP address 172.27.27.109, and the player's interface with MAC b1:55:50:eb:e2:96 has IP address 172.27.27.102. With this invocation, the conductor will listen on UDP port 30000 for messages from the player.

In the folder 'topo' there are some bash scripts that create emulated network topologies by means of Linux network namespaces. Same principle as mininet, but invoking directly the command line functions to build and configure namespaces and virtual switches, thus resulting less user-friendly but more tunable to specific needs. Also, the bash scripts 'assign\_ip\_to\_hosts' and 'forward\_to\_hosts' are used to configure IP addresses on the network namespaces and to forward traffic flowing through the virtual switches to the network namespaces, this way allowing the namespace to capture all the traffic going through its switch. See 'honeycomb7src7dst.png' for a graphical representation of the topology built by script 'topo\_honeycomb\_7src7dst.sh'.
HOWEVER, for the PoC development of the protocol, we do not necessarily need to deploy an emulated network, as this part on network emulation requires a pretty solid understanding of network namespaces and scripting applied to them. For basic tests on the protocol, one can just bring up (even manually) a pair of namespaces, assign IP to them, and run the 'conductor' on one and the 'player' on the other. Extension to multiple conductors and players can be considered a following step.


  
## Simple Setup Instructions

### Quick Start Code

---

Below are the commands needed to start the simple setup. This assumes Ryu is installed, as well as the necessary python dependencies. For explanations and step-by-step instructions, see the next section.

Begin in the mdn-proto directory
```
ryu-manager --app-list ryu.app.simple_switch_stp_13 ryu.app.ofctl_rest
```
(New Terminal)
```
cd topo
sudo ./topo_test_1sw2h.sh
```
(New Terminal)
```
sudo ip netns exec Host-00 ifconfig c.sw00-host00.1 10.0.0.1/24
sudo ip netns exec Host-01 ifconfig c.sw00-host01.1 10.0.0.2/24
sudo ip netns exec Host-00 python3 conductor09.py --cond-ip 10.0.0.1 --cond-port 30000
```
(New Terminal)
```
mac=`sudo ip netns exec Host-01 ifconfig -a | egrep 'ether' | egrep -o '..:..:..:..:..:..'`
sudo ip netns exec Host-01 python3 player09.py c.sw00-host01.1 $mac p1 --cond-ip 10.0.0.1 --cond-port 30000 --play-ip 10.0.0.2
```
<br>
<br>
  

### How to run conductor and player on an emulated network built with the scripts in the "topo" folder
 ---
 
--- install a SDN controller. Usually for these tests I use Ryu ( https://osrg.github.io/ryu/ ) because it's lightweight and written in Python. Once installed, open a terminal on your machine and run:

ryu-manager --app-list ryu.app.simple_switch_stp_13 ryu.app.ofctl_rest

and this should start a Ryu SDN controller process listening for OpenFlow messages on TCP port 6633 on the localhost interface (127.0.0.1). The additional apps we are loading are, respectively, a simple learning switch supporting OpenFlow version 1.3 with Spanning Tree Protocol enabled, plus a module that allows to communicate with Ryu via REST (HTTP) messages. Actually, for a very simple test on a loopless topology (such as the 2sw1h), one could also run Ryu with just:

ryu-manager --app-list ryu.app.simple_switch

which only loads basic OpenFlow 1.0 capabilities, which should be enough for basic tests requiring just basic packet forwarding.

--- open a new terminal, navigate to the "topo" folder and run:

sudo ./topo_test_1sw2h.sh

and this should set up 2 network namespaces acting as hosts, plus a virtual switch which by default should try and connect to the SDN controller at 127.0.0.1 on TCP port 6633 (where our instance of Ryu is listening)

--- open a new terminal and run:

sudo ip netns

and this should yield a list of active network namespaces, in this case you should find Host-00 and Host-01. If so, you can now input commands on each of those host by typing:

sudo ip netns exec (host name) (command)

for example, to gather the list of interfaces of the first host, you can run:

sudo ip netns exec Host-00 ifconfig -a

and you should see two interfaces, namely the loopback interface "lo" and another interface whose name starts with "c", then continues with the name of the switch this interface is connected to, then the name of this host, then a number representing the number of interfaces of this host.

--- in the same terminal where you just listed the namespaces, you can now assign IP addresses to the interfaces of the hosts. This is what my scripts "assign_IP" are for, but I reckon that some parts are case-specific, and you don't need to over-complicate things here anyway, so I suggest that here you assign IP addresses manually to the two hosts, with:

sudo ip netns exec (host name) ifconfig (interface name) (IP address with netmask length)

so for example

sudo ip netns exec Host-00 ifconfig c.sw00-host00.1 10.0.0.1/24

--- now you should be able to test the conductor and player. Say Host-00 is the conductor and Host-01 is the player. I suggest to open two terminals. I mean regular terminals on the machine you are working on. navigate to the mdn-proto folder. In one of the terminals run the conductor with:

sudo ip netns exec Host-00 python3 conductor09.py --cond-ip (IP address of Host-00) --cond-port 30000

and in the other terminal run the player with:

sudo ip netns exec Host-01 python3 player09.py (Host-01 eth interface name) (Host-01 eth interface mac address) (arbitrary player symbolic name) --cond-ip (IP address of Host-00) --cond-port 30000 --play-ip (IP address of Host-01)



### How to avoid using a SDN controller

---

--- discover the name of the switch
sudo ovs-vsctl show

--- set the specific switch to act as standalone with:
sudo ovs-vsctl set-fail-mode (switch-name) standalone
  
and now the switch should be able to forward packets without needing a SDN controller



### Important notes about the simple setup

---
- To this point, we have been unsuccessful in running these tests on mininet. For now, stick to the scripts in the topo directory

- If you typically use python virtual environments, make note that in this case, the python dependencies need to be installed on the computer, outside of a virtual environment. Unfortunately, when creating the hosts, the virtual environment is not carried over.

- The desired final outcome of the setup is for the conductor to display "Start listening to players... " and the player to display "Start packet capture... ". If you see these two messages, you have successfully set up the basic tests!
