import socket
import sys
import time

class UDPClient:
    def __init__(self, server_ip, server_port, filename):
        self.server_ip = server_ip
        self.server_port = server_port
        self.filename = filename
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)  # Set timeout for receiving data

    def request_file(self):
        # Send file request to server
        self.sock.sendto(self.filename.encode(), (self.server_ip, self.server_port))
        start_time = time.time()

        received_packets = {}
        last_seq_num = -1
        file_transfer_complete = False

        # Open file to write the received data once all packets are received
        while not file_transfer_complete:
            try:
                data, _ = self.sock.recvfrom(4096)
                if data == b'END':
                    file_transfer_complete = True
                    continue
                seq_num, packet_data = self.parse_packet(data)
                received_packets[seq_num] = packet_data
                self.send_ack(seq_num)
            except socket.timeout:
                print("Timeout occurred, waiting for retransmission...")
                continue

        # Ensuring all packets are received
        if file_transfer_complete:
            with open("received_" + self.filename, "wb") as file:
                for i in sorted(received_packets):
                    file.write(received_packets[i])

        end_time = time.time()
        #print("File transfer completed.")
        total_time = end_time - start_time
        print(f"{total_time:.2f}")

    def parse_packet(self, data):
        seq_num = int.from_bytes(data[:4], byteorder='big')
        packet_data = data[4:]
        return seq_num, packet_data

    def send_ack(self, seq_num):
        ack_message = f"ACK-{seq_num}".encode()
        self.sock.sendto(ack_message, (self.server_ip, self.server_port))

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python client.py SERVER_IP SERVER_PORT FILENAME")
        sys.exit(1)

    client = UDPClient(sys.argv[1], int(sys.argv[2]), sys.argv[3])
    client.request_file()