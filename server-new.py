import socket
import sys
import threading
import time

class PacketGenerator:
    def __init__(self, filename, packet_size_kb):
        self.filename = filename
        self.packet_size = packet_size_kb * 1024  # Convert KB to bytes

    def generate_packets(self):
        with open(self.filename, 'rb') as file:
            seq_num = 0
            while True:
                data = file.read(self.packet_size)
                if not data:
                    break
                yield self.create_packet(seq_num, data)
                seq_num += 1

    @staticmethod
    def create_packet(seq_num, data):
        seq_bytes = seq_num.to_bytes(4, byteorder='big')
        return seq_bytes + data

class UDPServer:
    def __init__(self, ip, port, protocol, window_size, timeout):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.window_size = window_size
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.clients = {}
        self.lock = threading.Lock()

    def start(self):
        print(f"Server starting on {self.ip}:{self.port} using {self.protocol}")
        while True:
            data, addr = self.sock.recvfrom(1024)
            if data:
                with self.lock:
                    if addr not in self.clients:
                        self.clients[addr] = {'base': 0, 'next_seq_num': 0, 'packets': None}
                threading.Thread(target=self.handle_client, args=(addr, data)).start()

    def handle_client(self, client_addr, data):
        print(f"Connection from {client_addr}")
        with self.lock:
            if self.clients[client_addr]['packets'] is None:
                filename = data.decode()
                generator = PacketGenerator(filename, 1)
                self.clients[client_addr]['packets'] = list(generator.generate_packets())

        if self.protocol == 'SW':
            self.stop_and_wait(client_addr)
        elif self.protocol == 'GBN':
            self.go_back_n(client_addr)
        elif self.protocol == 'SR':
            self.selective_repeat(client_addr)

    def stop_and_wait(self, client_addr):
        packets = self.clients[client_addr]['packets']
        for packet in packets:
            while True:
                self.sock.sendto(packet, client_addr)
                self.sock.settimeout(self.timeout)
                try:
                    response, _ = self.sock.recvfrom(1024)
                    if response.decode() == f'ACK-{int.from_bytes(packet[:4], "big")}':
                        break
                except socket.timeout:
                    continue
        self.send_end_signal(client_addr)

    def go_back_n(self, client_addr):
        packets = self.clients[client_addr]['packets']
        base = 0
        next_seq_num = 0

        while base < len(packets):
            while next_seq_num < base + self.window_size and next_seq_num < len(packets):
                self.sock.sendto(packets[next_seq_num], client_addr)
                next_seq_num += 1

            self.sock.settimeout(self.timeout)
            try:
                response, _ = self.sock.recvfrom(1024)
                ack_num = int(response.decode().split('-')[1])
                base = ack_num + 1
            except socket.timeout:
                next_seq_num = base

        self.send_end_signal(client_addr)

    def selective_repeat(self, client_addr):
        packets = self.clients[client_addr]['packets']
        acked = [False] * len(packets)
        base = 0

        while base < len(packets):
            for i in range(base, min(base + self.window_size, len(packets))):
                if not acked[i]:
                    self.sock.sendto(packets[i], client_addr)

            self.sock.settimeout(self.timeout)
            try:
                response, _ = self.sock.recvfrom(1024)
                ack_num = int(response.decode().split('-')[1])
                if ack_num < base + self.window_size:
                    acked[ack_num] = True
                    if ack_num == base:
                        while base < len(packets) and acked[base]:
                            base += 1
            except socket.timeout:
                continue

        self.send_end_signal(client_addr)

    def send_end_signal(self, client_addr):
        end_packet = b'END'
        self.sock.sendto(end_packet, client_addr)

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python server.py IP PORT PROTOCOL WINDOW_SIZE TIMEOUT")
        sys.exit(1)

    server = UDPServer(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), float(sys.argv[5]))
    server.start()