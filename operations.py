import pexpect, sys, time
#from globals import stop_scenario, scenario_lock
from globals import stop_scenario_execution, check_scenario_status


def interact_with_ssh(parameters, ssh_command):
    """
    Interaguje s SSH relací pomocí pexpect a zajišťuje zadávání hesla pro jakoukoli výzvu během relace.
    """
    global stop_scenario
    remote_command = parameters["command"]
    ssh_user = parameters["ssh_user"]
    ssh_password = parameters["ssh_password"]

    try:
        # Spuštění SSH relace
        child = pexpect.spawn(ssh_command, timeout=30, encoding='utf-8')
        # child.logfile = sys.stdout  # Logování výstupu pro ladění
        print("Připojuji se přes SSH...")

        # Smyčka pro zpracování relace
        output = ""
        remote_command_sent = False  # Zajistí, že příkaz bude spuštěn pouze jednou

        while True:         
            try:
                match_index = child.expect([
                    r"'s password:",         # Výzva k zadání hesla pro SSH nebo sudo
                    r"yes/no",               # Nový host key
                    f"Welcome",          # Shell prompt po přihlášení
                    r"\[sudo\] password for",  # Výzva pro sudo heslo
                    r"hping in flood mode",  # Hping byl spuštěn v flood módu
                    pexpect.EOF,             # Konec relace
                    pexpect.TIMEOUT          # Timeout bez výstupu
                ], timeout=2)
                if check_scenario_status():
                    # print("Scénář zastaven uživatelem. Ukončuji relaci...")
                    child.sendcontrol('c')  # Poslat Ctrl+C
                    try:
                        child.expect(pexpect.EOF, timeout=5)  # Čekat na ukončení relace
                    except pexpect.exceptions.TIMEOUT:
                        child.kill(0)
                    break
                                
                if match_index == 0:  # "[Pp]assword:"
                    print("Zadávám heslo pro SSH...")
                    child.sendline(ssh_password)

                elif match_index == 1:  # "yes/no"
                    print("Přijímám nový host key...")
                    child.sendline("yes")

                elif match_index == 2:  # Shell prompt
                    print("SSH připojení úspěšné.")
                    # Pokud je připojení úspěšné a příkaz nebyl dosud spuštěn
                    if remote_command and not remote_command_sent:
                        time.sleep(2) # Čekáme na inicializaci shellu
                        print(f"Spouštím vzdálený příkaz: {remote_command}")
                        child.sendline(remote_command)
                        remote_command_sent = True  # Zabráníme opakování
                elif match_index == 3:
                    print("Ping flood byl spuštěn.")
                elif match_index == 4:  # "[sudo] password for"
                    print("Zadávám heslo pro sudo...")
                    child.sendline(ssh_password)

                elif match_index == 5:  # EOF
                    print("Relace byla ukončena.")
                    break

                # elif match_index == 5:  # TIMEOUT
                    # Pripadne dodelat co se stane kdyz se nic nestane
                    # print("Žádný nový výstup, čekám...")

            except pexpect.exceptions.TIMEOUT:
                continue 

            # Uložení výstupu z každé iterace
            output += child.before.strip() + "\n"   

        child.close()
        return True, output

    except Exception as e:
        print(f"Chyba v SSH relaci: {e}")
        return False, str(e)

        