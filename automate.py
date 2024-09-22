import subprocess
import threading
import time
import re
import csv

# Define the parameters for the experiment
protocols = ['GBN', 'SR']
packet_loss_rates = ['0.1%', '0.5%', '1%', '1.5%', '2%', '5%']
latencies = [('50ms', '10ms'), ('100ms', '10ms'), ('150ms', '10ms'), ('200ms', '10ms'), ('250ms', '10ms'), ('500ms', '10ms')]
ip = '127.0.0.1'
port = '12345'
filename = 'loco.jpg'
window_size = '6'  # Fixed window size
timeout = '0.2'  # 200 ms as the RTO

def set_network_conditions(loss, latency, delay_variation):
    """ Configure network conditions with tc. """
    subprocess.run('sudo tc qdisc add dev wlo1 root handle 1: htb default 11', shell=True, check=True)
    subprocess.run('sudo tc class add dev wlo1 parent 1: classid 1:1 htb rate 100kbps', shell=True, check=True)
    subprocess.run(f'sudo tc qdisc add dev wlo1 parent 1:1 handle 10: netem loss {loss} delay {latency} {delay_variation} distribution normal', shell=True, check=True)

def reset_network_conditions():
    """ Reset network conditions to default. """
    subprocess.run('sudo tc qdisc del dev wlo1 root', shell=True, check=True)

def run_server(protocol):
    """ Run server in a separate thread. """
    return subprocess.Popen(['python3', 'server-new.py', ip, port, protocol, window_size, timeout])

def run_client():
    """ Run client and capture output. """
    client_output = subprocess.run(['python3', 'client-new.py', ip, port, filename], capture_output=True, text=True)
    time_match = re.search(r"(\d+\.\d+)", client_output.stdout)
    return time_match.group(0) if time_match else "No Time Found"

def main():
    results = []
    for protocol in protocols:
        for loss in packet_loss_rates:
            for mean, dev in latencies:
                print(f"Running {protocol} with {loss} loss and {mean} delay...")
                set_network_conditions(loss, mean, dev)
                server_process = run_server(protocol)
                time.sleep(3)  # Allow server to initialize
                total_time = run_client()
                results.append((protocol, loss, mean, total_time))
                server_process.terminate()
                server_process.wait()
                reset_network_conditions()
                time.sleep(1)  # Cool-down period

    # Output results
    print("\nExperiment Results:")
    for result in results:
        print(f"Protocol: {result[0]}, Loss: {result[1]}, Latency: {result[2]}, Time: {result[3]} s")

    # Optionally, write results to a CSV file
    with open('experiment_results.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Protocol', 'Packet Loss', 'Latency', 'Download Time (s)'])
        writer.writerows(results)

if __name__ == "__main__":
    main()