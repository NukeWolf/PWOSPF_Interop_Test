import sys
import os
import time
if os.getlogin() == "whyalex":
    sys.path.append("/home/whyalex/p4app/docker/scripts")

from p4app import P4Mininet
from mininet.cli import CLI
from mininet.link import Link, Intf

from alex_pwospf.controller import MacLearningController_Alex as alex_controller
from alex_pwospf.my_topo import SingleSwitchTopo as alex_topo

from michael_PWOPSF.controller import MacLearningController as michael_controller
from michael_PWOPSF.my_topo import CustomTopo as michael_topo

import pwospf_scapy



# Add three hosts. Port 1 (h1) is reserved for the CPU.
# Alex's switches

A_NUM_SWITCHES = 4
NUM_HOSTS_PER_SWITCH = 3
a_links = [(1,2),(2,3),(3,4)]

topo1 = alex_topo(A_NUM_SWITCHES,NUM_HOSTS_PER_SWITCH, a_links, network=1)
net1 = P4Mininet(program="alex_pwospf/router.p4", topo=topo1, auto_arp=False)

a_switches = [net1.get("n1_s%d" % x)for x in range(1,A_NUM_SWITCHES+1)]

#Michaels Switches
M_NUM_SWITCHES = 3
m_links = [[1,2],[2,3]]

topo2 = michael_topo(M_NUM_SWITCHES,NUM_HOSTS_PER_SWITCH,m_links)
net2 = P4Mininet(program="michael_PWOPSF/l2switch.p4", topo=topo2, auto_arp=False)

m_switches = [net2.get("s%d" % x)for x in range(1,M_NUM_SWITCHES+1)]
m_extra_links = [0 for x in range(1,M_NUM_SWITCHES+1)]


# Setup links between the two networks
am_links = [(2,2), (3,2), (3,1), (4,1)]

for alex_sw, mi_sw in am_links:
    a_sw = a_switches[alex_sw-1]
    m_sw = m_switches[mi_sw-1]
    net2.addLink(node1=a_sw,node2=m_sw)

    topo1.extra_links["n1_s%d" % alex_sw] += 1
    m_extra_links[mi_sw-1] += 1


net1.start()
net2.start()


cpus = [] 

#Alex Setup Switch
for n in range(1,2):
    # Setup Controllers
    for s in range(1,A_NUM_SWITCHES + 1):
    # Add a mcast group for all ports (except for the CPU port)
        bcast_mgid = 1
        sw = net1.get("n%d_s%d" % (n,s))
        # print(sw)
        sw.addMulticastGroup(mgid=bcast_mgid, ports=range(2, NUM_HOSTS_PER_SWITCH + 1 + topo1.extra_links["n%d_s%d" % (n,s)]))

        # Send MAC bcast packets to the bcast multicast group
        sw.insertTableEntry(
            table_name="MyIngress.fwd_l2",
            match_fields={"hdr.ethernet.dstAddr": ["ff:ff:ff:ff:ff:ff"]},
            action_name="MyIngress.set_mgid",
            action_params={"mgid": bcast_mgid},
        )
        
        ports = NUM_HOSTS_PER_SWITCH + topo1.extra_links["n%d_s%d" % (n,s)] - 1
        # Start the MAC learning controller
        cpu = alex_controller(sw,mac="00:00:00:%d:%d:01" % (n,s),ip="10.%d.%d.1" % (n,s),area=0, ports=ports, start_wait=1)
        cpu.start()
        cpus.append(cpu)
        

# Michael setup switch and controllers
for i in range(1, M_NUM_SWITCHES + 1):
    swName = 's%d' % i

    # Add a mcast group for all ports (except for the CPU port)
    bcast_mgid = 1
    sw = net2.get(swName)
    sw.addMulticastGroup(mgid=bcast_mgid, ports=range(2, topo2.link_count[swName] + m_extra_links[i-1] + 1))

    # Send MAC bcast packets to the bcast multicast group
    sw.insertTableEntry(
        table_name="MyIngress.fwd_l2",
        match_fields={"hdr.ethernet.dstAddr": ["ff:ff:ff:ff:ff:ff"]},
        action_name="MyIngress.set_mgid",
        action_params={"mgid": bcast_mgid},
    )

    # Start the MAC learning controller
    h1 = net2.get("s%dh1" % i)
    cpu = michael_controller(
        sw=sw,
        ip = h1.IP(),
        mac = h1.MAC(),
        mask='255.255.255.0',
        nPorts=topo2.link_count[swName] + m_extra_links[i-1]
    )
    cpu.start()
    cpus.append(cpu)


h1 = net1.get("n1_s1_h2")
h2 = net2.get("s2h3")
h3 = net2.get("s3h2")

time.sleep(30)

print("~~~~~~~~~~ALEX_SWITCH_1~~~~~~~~~}")
print(h1.cmd("ping -c3 10.1.4.2"))
print(h1.cmd("traceroute 10.1.4.2"))

print(h1.cmd("ping -c3 10.2.1.2"))
print(h1.cmd("traceroute 10.2.1.2"))

print(h1.cmd("ping -c3 10.2.3.2"))
print(h1.cmd("traceroute 10.2.3.2"))

print(h1.cmd("ping -c1 10.2.2.1"))

print("~~~~~~~~~~MICHAEL_SWITCH_2~~~~~~~~~}")
print(h2.cmd("traceroute 10.1.1.2"))
print(h2.cmd("traceroute 10.2.1.2"))

print(h3.cmd("ping -c1 10.1.3.1"))



a_switches[0].printTableEntries()
m_switches[1].printTableEntries()



