import psutil
import ipaddress
import socket

def get_active_interfaces():
    interfaces = psutil.net_if_addrs()
    active_interfaces = []

    for interface, addresses in interfaces.items():
        for addr in addresses:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                network = ipaddress.IPv4Network(f"{addr.address}/24", strict=False)
                active_interfaces.append((interface, addr.address, network))

    return active_interfaces