from database.mongodb import get_mongo_client
from operations import interact_with_ssh
#from globals import stop_scenario
from globals import stop_scenario_execution, check_scenario_status, reset_scenario_status
import subprocess, threading, os, signal, time

# Nacteni scenare z DB
def load_scenario_from_db(scenario_name):
    """Load an attack scenario by name from the database."""
    client = get_mongo_client()
    db = client["cybertest_tool"]
    return db["attack_scenarios"].find_one({"name": scenario_name})

# Nacteni akce z DB podle ID
def load_action(action_id):
    client = get_mongo_client()
    db = client["cybertest_tool"]
    return db["actions"].find_one({"_id": action_id})

def monitor_user_input():
    """Sleduje uživatelský vstup a zastaví scénář při stisknutí Enter."""
    #global stop_scenario
    input("Stiskněte Enter pro ukončení scénáře...\n")
    stop_scenario_execution()
    #stop_scenario = True
    #print("Scénář byl ukončen uživatelem.")


def execute_action(action, parameters):
    command = action["command"]
    command = replace_placeholders(command, parameters)
    print(f"Executing command: {command}")

    output = []

    def process_task():
        """Zpracuje příkaz – buď lokální, nebo vzdálený SSH."""
        if command.startswith("ssh"):
            success, cmd_output = interact_with_ssh(parameters, command)
        else:
            success, cmd_output = execute_local_command(command)
        output.append((success, cmd_output))

    # Spuštění procesu ve vlákně
    process_thread = threading.Thread(target=process_task, daemon=True)
    process_thread.start()

    while process_thread.is_alive(): # Čekáme na dokončení procesu nebo přerušení scénáře
        if check_scenario_status():
            print("Scénář byl zastaven uživatelem. Ukončuji proces...") # Preruseni je zajisteno v konkretnich process funkcich
            break

    time.sleep(2)  # Počkáme chvilku, aby se výstup stihl zpracovat
    process_thread.join()  # Po uplynutí timeoutu se vlákno ukončí

        # Získání výsledku
    if output and not check_scenario_status():
        success, cmd_output = output[0]

        # Kontrola výstupu
        if not cmd_output.strip():
            print("Výstup akce je prázdný. Akce považována za selhání.")
            return False, "Output was empty, action failed."

        if "success_keywords" in action:
            print(f"Klíčová slova pro úspěch: {action['success_keywords']}")
            if not all(keyword in cmd_output for keyword in action["success_keywords"]):
                print("Výstup neobsahuje žádné z klíčových slov pro úspěch. Akce považována za selhání.")
                return False, cmd_output

        return success, cmd_output
    else:
        return False, "Proces selhal nebo byl zastaven uživatelem."



# def execute_action(action, parameters):
#     #global stop_scenario
#     command = action["command"]
#     command = replace_placeholders(command, parameters)
    
#     print(f"Executing command: {command}")

#     if command.startswith("ssh"):
#         output = []

#         def ssh_task():
#             success, ssh_output = interact_with_ssh(parameters, command)
#             output.append((success, ssh_output))  # Uložení výsledku do seznamu (kvůli uzávěře)

#         ssh_thread = threading.Thread(target=ssh_task, daemon=True)
#         ssh_thread.start()

#         # Čekáme na dokončení vlákna nebo přerušení scénáře
#         while ssh_thread.is_alive():
#             if check_scenario_status():
#                 print("Scénář byl zastaven uživatelem. Ukončuji SSH relaci...")
#                 break

#         # Pokud relace stále běží, ukončíme ji
#         if ssh_thread.is_alive():
#             time.sleep(2)  # Počkáme chvilku, aby se výstup stihl zpracovat
#             ssh_thread.join()  # Počkáme na ukončení

#         # Získáme výstup
#         if output:
#             success, ssh_output = output[0]
#             if not success:
#                 return False, ssh_output
#             return True, ssh_output
#         else:
#             return False, "SSH relace nebyla úspěšná."

#     else:
#         # Spustíme proces v nové procesové skupině
#         process = subprocess.Popen(
#             command, 
#             shell=True, 
#             stdout=subprocess.PIPE, 
#             stderr=subprocess.PIPE, 
#             text=True, 
#             preexec_fn=os.setsid  # Nastaví proces do nové skupiny
#         )
        

#         try:
#             while process.poll() is None:  # Kontroluje, zda proces stále běží
#                 if check_scenario_status():
#                     print("Scénář byl zastaven uživatelem. Ukončuji proces...")
                    
#                     # Ukončíme celou procesovou skupinu
#                     os.killpg(os.getpgid(process.pid), signal.SIGTERM)
#                     try:
#                         process.wait(timeout=3)  # Počká, jestli se proces ukončí
#                     except subprocess.TimeoutExpired:
#                         print("Proces neodpovídá, bude ukončen silou.")
#                         os.killpg(os.getpgid(process.pid), signal.SIGKILL)
#                     stdout, stderr = process.communicate()
#                     combined_output = stdout.strip() + "\n" + stderr.strip()
#                     print(f"Výstup akce: {combined_output}") # Debugging purposes
#                     return True , combined_output


#             # Proces skončil normálně
#             stdout, stderr = process.communicate()
#             combined_output = stdout.strip() + "\n" + stderr.strip()
            
#             print(f"Výstup akce: {combined_output}")  # Debugging purposes

#             # Kontrola úspěšnosti na základě obsahu výstupu
#             if not stdout.strip() and not stderr.strip(): 
#                 print("Výstup akce je prázdný. Akce považována za selhání.")
#                 return False, "Output was empty, action failed."

#             if "success_keywords" in action:
#                 print(f"Klíčová slova pro úspěch: {action['success_keywords']}")  # Debugging purposes
#                 if not all(keyword in combined_output for keyword in action["success_keywords"]):
#                     print("Výstup neobsahuje žádné z klíčových slov pro úspěch. Akce považována za selhání.")
#                     return False, combined_output

#             return True, combined_output  # Úspěšná akce

#         except Exception as e:
#             print(f"Došlo k chybě: {e}")
#             os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # Ukončení celé skupiny při chybě
#             return False, str(e)

def execute_local_command(command):
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid  # Nastaví proces do nové skupiny
        )

        output = ""
        while process.poll() is None:
            if check_scenario_status():
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                return False, "Lokální proces byl zastaven uživatelem."
            time.sleep(0.5)

        stdout, stderr = process.communicate()
        output = stdout.strip() + "\n" + stderr.strip()

        if process.returncode != 0:
            return False, output

        return True, output
    except Exception as e:
        return False, str(e)



def execute_scenario(scenario_name, selected_network):
    reset_scenario_status()

    scenario = load_scenario_from_db(scenario_name)
    if not scenario:
        print(f"Scénář '{scenario_name}' nebyl nalezen v databázi.")
        return

    # Spuštění vlákna pro monitorování uživatelského vstupu
    user_input_thread = threading.Thread(target=monitor_user_input, daemon=True)
    user_input_thread.start()

    context = {"selected_network": selected_network, "target_ip": None}

    for step in scenario["steps"]:
        if check_scenario_status():
            print("Scénář byl zastaven uživatelem.")
            breakfpa

        description = replace_placeholders(step["description"], context)
        print(f"\nProvádím krok {step['step_id']}: {description}")

        # Načtení akce pro tento krok
        action = load_action(step["action"])
        if not action:
            print(f"Akce '{step['action']}' nebyla nalezena v databázi.")
            break

        # Zkontrolujeme, zda jsou splněny podmínky pro tento krok
        if "conditions" in step and not evaluate_conditions(step["conditions"], context):
            print(step.get("failure_message", "Podmínky pro tento krok nejsou splněny. Ukončuji scénář."))
            break

        # Určení parametrů pro akci
        parameters = {key: context.get(value.strip("{{}}"), value) for key, value in step["parameters"].items()} # Získání hodnot z kontextu nebo přímo

        success, output = execute_action(action, parameters)

        if not success and not check_scenario_status():
            print(step.get("failure_message", "Akce selhala. Ukončuji scénář."))
            break  # Ukončí scénář.

        # Aktualizace kontextu na základě výsledku akce
        update_context(context, step, output, success)

        # Výpis zprávy o úspěchu nebo selhání
        if not check_scenario_status():
            message = step.get("success_message" if success else "failure_message", "")
            for key, value in context.items():
                message = message.replace(f"{{{{{key}}}}}", str(value))
            print(message)

    print("\n Dokončeno provádění scénáře. \n")


def evaluate_conditions(conditions, context):
    """Check if all conditions are met based on the current context."""
    for key, expected_value in conditions.items():
        actual_value = context.get(key)

        # Pokud je podmínka ve formě klíč -> hodnota, porovnáme hodnoty
        if isinstance(expected_value, str) and expected_value.startswith("{{") and expected_value.endswith("}}"):
            # Jestliže je `expected_value` výraz ve formátu `{{key}}`, extrahujeme název klíče a kontrolujeme jeho existenci v kontextu
            required_key = expected_value.strip("{{}}")
            if not context.get(required_key):
                print(f"Podmínka pro '{key}' není splněna: očekávaný klíč '{required_key}' chybí nebo je prázdný v kontextu.")
                return False
        elif actual_value != expected_value:
            print(f"Porovnávám hodnoty {key}: {actual_value} a {expected_value} - podmínka není splněna.")
            return False  # Podmínka není splněna

    return True  # Všechny podmínky jsou splněny

def update_context(context, step, output, success):
    """Aktualizuje kontext na základě výsledku akce a definic ve scénáři."""
    context["previous_step_success"] = success
    
    # Uložení specifických hodnot do kontextu na základě nastavení ve scénáři
    if "context_updates" in step and success:  # Uloží jen pokud je krok úspěšný
        for key, expression in step["context_updates"].items():
            if expression == "output":
                # Uložíme výstup bez bílých znaků
                # ozkouset jestli to ma smysl, kdytak jen nechat context[key] = output.strip()
                context[key] = output.strip() if output and output.strip() else None # Pokud je výstup prázdný, uložíme None  
            else:
                context[key] = expression

def replace_placeholders(text, replacements):
    """
    Replace placeholders in the given text with corresponding values from the replacements dictionary.

    Args:
        text (str): The text containing placeholders in the format {{key}}.
        replacements (dict): A dictionary where keys are placeholder names and values are the values to replace them with.

    Returns:
        str: The text with all placeholders replaced by their corresponding values.

    Example:
        text = "Hello, {{name}}!"
        replacements = {"name": "Alice"}
        result = replace_placeholders(text, replacements)
        # result will be "Hello, Alice!"
    """
    for key, value in replacements.items():
        placeholder = f"{{{{{key}}}}}"  # Create placeholder {{key}}
        text = text.replace(placeholder, str(value))
    return text