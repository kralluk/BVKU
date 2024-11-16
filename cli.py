from network.interfaces import get_active_interfaces
from network.scanner import scan_network_with_nmap
from database.mongodb import save_network_info_to_db, get_network_info
from scenario_manager import execute_scenario
from database.mongodb import get_mongo_client

def choose_network():
    networks = get_network_info()
    
    print("Dostupné sítě:")
    for idx, network in enumerate(networks):
        print(f"{idx + 1}. Rozhraní: {network['interface']}, Síť: {network['network']}")
    
    choice = int(input("Zadejte číslo sítě, kterou chcete zvolit: ")) - 1
    return networks[choice]["network"] if 0 <= choice < len(networks) else None


def list_scenarios():
    """
    Retrieves the list of scenarios from the database.
    """
    client = get_mongo_client()
    db = client["cybertest_tool"]
    return list(db["attack_scenarios"].find({}, {"name": 1, "_id": 0}))

def main():
    client = get_mongo_client()
    active_interfaces = get_active_interfaces() # Zjisteni aktivnich rozhrani
    save_network_info_to_db(client, active_interfaces) # Ulozeni informaci o sitich do DB

    
    # Attempt to set the default network to `eth0`, or use the first non-loopback available network
    selected_network = None
    for iface, ip, net in active_interfaces:
        if iface == "eth0":
            selected_network = net
            break

    # If `eth0` was not found, use the first non-loopback network
    if not selected_network:
        for iface, ip, net in active_interfaces:
            if not ip.startswith("127."):  # Exclude loopback addresses
                selected_network = net
                print(f"Výchozí síť nastavena na: {selected_network}")
                break

    while True:
        print("\nMožnosti:")
        print("1. Proskenovat aktuální síť")
        print("2. Zobrazit dostupné scénáře")
        print("3. Změnit testovanou síť")
        print("4. Spustit scénář útoku")
        print("5. Ukončit")
        choice = input("Vyberte možnost: ")

        if choice == "1":
            print(f"Skenování sítě: {selected_network}")
            scan_results = scan_network_with_nmap(selected_network)
            print("Výsledek skenování:")
            for device in scan_results:
                print(f"IP: {device['ip']}, Stav: {device['state']}, Hostname: {device['hostname']}")
        
        elif choice == "2":
            scenario_list = list_scenarios()
            print("Dostupné scénáře:")
            for idx, scenario in enumerate(scenario_list):
                print(f"{idx + 1}. {scenario['name']}")

        elif choice == "3":
            new_network = choose_network()
            if new_network:
                selected_network = new_network
                print(f"Testovaná síť byla změněna na: {selected_network}")

        elif choice == "4":
               # Retrieve scenarios so the user can select by indeqx
            scenarios = list_scenarios()
            if not scenarios:
                print("Žádné dostupné scénáře nebyly nalezeny.")
                continue
            
            # Display scenario options with indexes
            print("\nDostupné scénáře:")
            for idx, scenario in enumerate(scenarios):
                print(f"{idx + 1}. {scenario['name']}")

            # Prompt the user to select a scenario by number
            try:
                scenario_choice = int(input("Vyberte číslo scénáře k provedení: ")) - 1
                if 0 <= scenario_choice < len(scenarios):
                    scenario_name = scenarios[scenario_choice]["name"]
                    print(f"Spouštím scénář: {scenario_name}")
                    execute_scenario(scenario_name, selected_network)

                else:
                    print("Neplatná volba scénáře. Zadejte číslo zobrazeného scénáře.")
            except ValueError:
                print("Prosím, zadejte platné číslo scénáře.")
            #execute_scenario(scenario_name, selected_network)

        elif choice == "5":
            print("Ukončuji program.")
            break
        else:
            print("Neplatná volba. Zkuste to znovu.")

if __name__ == "__main__":
    main()