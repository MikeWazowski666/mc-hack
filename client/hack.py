#!/usr/bin/python3

from twisted.internet import reactor
from quarry.net.proxy import DownstreamFactory, Bridge
import sys
import struct
import argparse
import time
import random
import math

class QuietBridge(Bridge):
    entity_id = None
    prev_pos = None
    prev_look = None
    prev_slot = None

    def packet_upstream_player_position(self, buff):
        buff.save()
        x, y, z, ground = struct.unpack('>dddB', buff.read())
        print(f"[*] player_position     {int(x)} / {int(y)} / {int(z)}     | {ground}")
        self.prev_pos = (x, y, z, ground)
        buf = struct.pack('>dddB', x, y, z, ground)
        self.upstream.send_packet('player_position', buf)
        
    def packet_upstream_player_look(self, buff):
        buff.save()
        yaw, pitch, ground = struct.unpack('>ffB', buff.read())
        print(f"[*] player_rotation     {yaw} / {pitch}     | {ground}")
        self.prev_look = (yaw, pitch, ground)
        buf = struct.pack('>ffB', yaw, pitch, ground)
        self.upstream.send_packet('player_look', buf)

    # def packet_downstream_set_slot(self, buff): # [!] set_slot b'\x00 \x02 \x00 & \x01 \x01 \x07 \x00'
    #     buff.save()
        # wid, stateid, slot, slot_data = struct.unpack('>sshp', buff.read())
        # print(f"[*] {wid} {stateid} {slot} {slot_data}")


    # def packet_upstream_player_digging(self, buff):
    #     buff.save()
    #     print(struct.unpack('>ddd', buff.read()))


    def packet_upstream_chat_message(self, buff):
        buff.save()
        chat_message = buff.unpack_string()
        print(f'>> {chat_message}')
        
        # Own command method
        if chat_message[:1] == '!':
            
            # Teleportation
            if chat_message[1:3] == "tp":

                distance, up = chat_message.split(' ')[1:] # Get the blocks to tp

                x, y, z, ground = self.prev_pos
                yaw, pitch, ground = self.prev_look

                # Super hard math
                f = pitch * 0.017453292
                g = -yaw * 0.017453292
                h = math.cos(g)
                i = math.sin(g)
                j = math.cos(f)
                k = math.sin(f)
                _x = i*j
                _y = -k
                _z = h*j
                x += _x * float(distance)
                y += _y * float(distance)
                z += _z * float(distance)

                # Send to server
                buf = struct.pack('>dddB', x, y+ float(up), z, ground)
                self.upstream.send_packet('player_position', buf)

                # Send to client
                buf = struct.pack('>dddffBBB', x, y+ float(up), z, yaw, pitch, 0, 0, 0)
                self.downstream.send_packet('player_position_and_look', buf)

            # Give items
            elif chat_message[1:5] == "give":
                item, ammount = chat_message.split(' ')[1:]
                
                prev_slot = self.prev_slot

                array = struct.pack('>7b', 0, 2, 0, 26, int(item), int(ammount), 0x00)

                print(array)

                # self.downstream.send_packet('set_slot', array)
        else:
            self.upstream.send_packet("chat_message", self.buff_type.pack_string(chat_message))


    def packet_unhandled(self, buff, direction, name):
        # print(f"[*][{direction}] {name}")
        if direction == "downstream":
            self.downstream.send_packet(name, buff.read())
        elif direction == "upstream":
            self.upstream.send_packet(name, buff.read())

        # if name == "chat_message":
        #     buff.save()
            # print("[!]", buff.read())
        

class QuietDownstreamFactory(DownstreamFactory):
    bridge_class = QuietBridge
    motd = "Proxied minecraft"

def main(argv):
    # Parse options
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--listen-host", default="0.0.0.0", help="address to listen on")
    parser.add_argument("-p", "--listen-port", default=25565, type=int, help="port to listen on")
    parser.add_argument("-b", "--connect-host", default="127.0.0.1", help="address to connect to")
    parser.add_argument("-q", "--connect-port", default=25565, type=int, help="port to connect to")
    args = parser.parse_args(argv)

    # Create factory
    factory = QuietDownstreamFactory()
    factory.connect_host = args.connect_host
    factory.connect_port = args.connect_port

    # Listen
    factory.listen(args.listen_host, args.listen_port)
    reactor.run()

if __name__ == "__main__":
    main(sys.argv[1:])