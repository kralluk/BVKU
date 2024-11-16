import nmap

def scan_network_with_nmap(network):
    nm = nmap.PortScanner()
    scan_result = nm.scan(hosts=str(network), arguments='-sP')
    devices = []
    for host in nm.all_hosts():
        devices.append({
            "ip": host,
            "state": nm[host].state(),
            "hostname": nm[host].hostname()
        })
    return devices