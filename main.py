import sys
import os
import time
if os.getlogin() == "whyalex":
    sys.path.append("/home/whyalex/p4app/docker/scripts")

from p4app import P4Mininet
from mininet.cli import CLI
from mininet.link import Link, Intf

from alex_pwospf import MacLearningController as alex_controller
from alex_pwospf import SingleSwitchTopo as alex_topo



# Add three hosts. Port 1 (h1) is reserved for the CPU.
NUM_SWITCHES = 5
NUM_HOSTS_PER_SWITCH = 3
AREA = 1
links = [(1,2),(2,3), (2,5), (3,8), (8,4), (4,6), (4,5), (5,7)]
# links = [(1,2), (2,3), (3,4)]
links = [(1,2),(2,5),(1,3), (3,4), (4,5)]

topo1 = alex_topo(NUM_SWITCHES,NUM_HOSTS_PER_SWITCH, links, network=1)
topo2 = alex_topo(NUM_SWITCHES,NUM_HOSTS_PER_SWITCH, links, network=2)


net1 = P4Mininet(program="alex_pwospf/l2switch.p4", topo=topo1, auto_arp=False)
net2 = P4Mininet(program="alex_pwospf/l2switch.p4", topo=topo2, auto_arp=False)

n1_s1 = net1.get("n1_s5")
n2_s1 = net2.get("n2_s1")

Link(node1=n1_s1,node2=n2_s1)


topo1.extra_links["n1_s5"] += 1
topo2.extra_links["n2_s1"] += 1

net1.start()
net2.start()


nets = [net1,net2]
topos = [topo1,topo2]
cpus = [] 

for n in range(1,3):
    # Setup Controllers
    for s in range(1,NUM_SWITCHES + 1):
    # Add a mcast group for all ports (except for the CPU port)
        bcast_mgid = 1
        sw = nets[n-1].get("n%d_s%d" % (n,s))
        # print(sw)
        sw.addMulticastGroup(mgid=bcast_mgid, ports=range(2, NUM_HOSTS_PER_SWITCH + 1 + topos[n-1].extra_links["n%d_s%d" % (n,s)]))

        # Send MAC bcast packets to the bcast multicast group
        sw.insertTableEntry(
            table_name="MyIngress.fwd_l2",
            match_fields={"hdr.ethernet.dstAddr": ["ff:ff:ff:ff:ff:ff"]},
            action_name="MyIngress.set_mgid",
            action_params={"mgid": bcast_mgid},
        )
        
        ports = NUM_HOSTS_PER_SWITCH + topos[n-1].extra_links["n%d_s%d" % (n,s)] - 1
        # Start the MAC learning controller
        cpu = alex_controller(sw,mac="00:00:00:%d:%d:01" % (n,s),ip="10.%d.%d.1" % (n,s),area=1, ports=ports, start_wait=1)
        cpu.start()
        cpus.append(cpu)


h1, h2 = net1.get("n1_s1_h2"), net2.get("n2_s1_h2")
h1 = net1.get("n1_s1_h2")

time.sleep(30)
print(h1.cmd("ping -c3 10.2.5.2"))



