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

In the folder 'topo' there are some bash scripts that create emulated network topologies by means of Linux network namespaces. Same principle as mininet, but invoking directly the command line functions to build and configure namespaces and virtual switches, thus resulting less user-friendly but more tunable to specific needs. Also, the bash scripts 'assign_ip_to_hosts' and 'forward_to_hosts' are used to configure IP addresses on the network namespaces and to forward traffic flowing through the virtual switches to the network namespaces, this way allowing the namespace to capture all the traffic going through its switch. See 'honeycomb7src7dst.png' for a graphical representation of the topology built by script 'topo_honeycomb_7src7dst.sh'.
HOWEVER, for the PoC development of the protocol, we do not necessarily need to deploy an emulated network, as this part on network emulation requires a pretty solid understanding of network namespaces and scripting applied to them. For basic tests on the protocol, one can just bring up (even manually) a pair of namespaces, assign IP to them, and run the 'conductor' on one and the 'player' on the other. Extension to multiple conductors and players can be considered a following step.
