# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import datetime
from nis import match
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet,udp
from ryu.lib.packet import ether_types
import json
from flask import Flask,jsonify
from ryu.controller.controller import Datapath
from eventlet.green.socket import socket
class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]


    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 270, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        print(str(datapath.send_msg(mod)))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        print(datapath.address)
        print('datapath here')
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        print(str(msg.match))
        print("match here")
        time = 6
        e = datetime.datetime.now()
        print("The time is: = %s:%s:%s" % (e.hour,e.minute,e.second))
        if e.hour > time:
            with open('time.txt', "r") as myfile:
                data = int(myfile.readline())
                print("data is %s" % (data))
                if data == 0:
                    print("here")
                    with open('time.txt', "w") as other:
                        other.write("1")
                        print("Time is bigger than %s" % (time))
                if data == "1":
                    print("time.txt gowaha 1")

        pkt = packet.Packet(msg.data)
        
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        if src == "c6:bb:fe:03:70:db":
            self.logger.info("aywa")
        else:
            self.logger.info(src)                                    
        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})
        #self.logger.info("packetsaya in %s %s %s %s", dpid, src, dst, in_port)

        def switch_fl(info):
            switcher ={
                1: "1here",
                2: "1here",
                3: "3here",
                4: "4here",
                5: self.sendC(datapath)
            }
            print (switcher.get(info, "invalid"))

        with open('FL.txt',"r") as flfile:
            info = int(flfile.readline())
            switch_fl(info)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            print(str(out_port))
            print("outport here")
        else:
            out_port = ofproto.OFPP_FLOOD
            

        up = pkt.get_protocols(udp.udp)
        DYPR=3
        if len(up) >0:
            print("protocol type: UDP")
            DYPR=500
        #self.logger.info(up)
        
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, DYPR, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, DYPR, match, actions)
        f = open("orders.txt","r")
        flag = f.read()
        if flag == "0":
            print("feha zero")
        if flag == "1":
            print("feha one")
            self.sendC(datapath)
        
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def sendC(self,dp):
        sock = socket()
        #dp = Datapath(sock,('127.0.0.1', 39972))
        ofprotoT = dp.ofproto
        priorityT=1836
        parserT=dp.ofproto_parser
        matchT=parserT.OFPMatch(in_port=1)
        actionsT = [parserT.OFPActionOutput(7,
                                            ofprotoT.OFPCML_NO_BUFFER)]
        instT = [parserT.OFPInstructionActions(ofprotoT.OFPIT_APPLY_ACTIONS,
                                                actionsT)]
        test=parserT.OFPFlowMod(datapath=dp, priority=priorityT,match=matchT, instructions=instT)
        dp.send_msg(test)
        print("flow added")

        req=parserT.OFPFlowStatsRequest(dp, 0,ofprotoT.OFPTT_ALL,ofprotoT.OFPP_ANY, ofprotoT.OFPG_ANY,0, 0,matchT)
        #req=parserT.OFPTableStatsRequest(dp, 0)
        print(dp.send_msg(req))

        print("retrieve")

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        flows = []
        for stat in ev.msg.body:
            flows.append('table_id=%s '
                        'duration_sec=%d duration_nsec=%d '
                        'priority=%d '
                        'idle_timeout=%d hard_timeout=%d flags=0x%04x '
                        'cookie=%d packet_count=%d byte_count=%d '
                        'match=%s instructions=%s' %
                        (stat.table_id,
                        stat.duration_sec, stat.duration_nsec,
                        stat.priority,
                        stat.idle_timeout, stat.hard_timeout, stat.flags,
                        stat.cookie, stat.packet_count, stat.byte_count,
                        stat.match, stat.instructions))
        self.logger.info('FlowStats: %s', flows)