from database.mongodb import get_mongo_client
import subprocess

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


# Spusteni akce


   

# def execute_action(action, parameters):
#     command = action["command"]
#     for key, value in parameters.items():
#         placeholder = f"{{{{{key}}}}}"
#         command = command.replace(placeholder, str(value))
    
#     print(f"Executing command: {command}")
#     # print(f"Parameters passed to command: {parameters}")  # Debugging purposes


#     try:
#         result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
#         return True, result.stdout  # Úspěch, pokud příkaz proběhl bez chyby

#     except subprocess.CalledProcessError as e:
#         print(f"Command failed with error: {e}")
#         return False, e.output


# def execute_action(action, parameters):
#     command = action["command"]
#     command = replace_placeholders(command, parameters)
#     # for key, value in parameters.items():
#     #     placeholder = f"{{{{{key}}}}}"
#     #     command = command.replace(placeholder, str(value))
    
#     print(f"Executing command: {command}")

#     try:
#         result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
#         output = result.stdout.strip()
#         print(f"Výstup akce: {output}")  # Debugging purposes

#         # Kontrola úspěšnosti na základě obsahu výstupu
#         if not output:
#             print("Výstup akce je prázdný. Akce považována za selhání.")
#             return False, "Output was empty, action failed."

#         # Dodatečná kontrola klíčových slov ve výstupu
#         if "success_keywords" in action:
#             print(f"Klíčová slova pro úspěch: {action['success_keywords']}")  # Debugging purposes
            
#             # Pokud žádné klíčové slovo není ve výstupu, akce je neúspěšná
#             if not all(keyword in output for keyword in action["success_keywords"]):
#                 print("Výstup neobsahuje žádné z klíčových slov pro úspěch. Akce považována za selhání.")
#                 return False, output  # Vrací False, protože klíčová slova nebyla nalezena

#         return True, output  # Úspěch, pokud výstup není prázdný a/nebo obsahuje klíčová slova

#     except subprocess.CalledProcessError as e:
#         print(f"Command failed with error: {e}")
#         return False, e.output

import subprocess
import threading

# Globální proměnná pro zastavení scénáře
stop_scenario = False

def monitor_user_input():
    """Sleduje uživatelský vstup a zastaví scénář při stisknutí Enter."""
    global stop_scenario
    input("Stiskněte Enter pro ukončení scénáře...\n")
    stop_scenario = True
    #print("Scénář byl ukončen uživatelem.")

import os
import signal
import subprocess

def execute_action(action, parameters):
    global stop_scenario
    command = action["command"]
    command = replace_placeholders(command, parameters)
    
    print(f"Executing command: {command}")

    # Spustíme proces v nové procesové skupině
    process = subprocess.Popen(
        command, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        preexec_fn=os.setsid  # Nastaví proces do nové skupiny
    )
    
    try:
        while process.poll() is None:  # Kontroluje, zda proces stále běží
            if stop_scenario:
                print("Scénář byl zastaven uživatelem. Ukončuji proces...")
                
                # Ukončíme celou procesovou skupinu
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=3)  # Počká, jestli se proces ukončí
                except subprocess.TimeoutExpired:
                    print("Proces neodpovídá, bude ukončen silou.")
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                stdout, stderr = process.communicate()
                combined_output = stdout.strip() + "\n" + stderr.strip()
                print(f"Výstup akce: {combined_output}") # Debugging purposes
                return True , combined_output


        # Proces skončil normálně
        stdout, stderr = process.communicate()
        combined_output = stdout.strip() + "\n" + stderr.strip()
        
        print(f"Výstup akce: {combined_output}")  # Debugging purposes

        # Kontrola úspěšnosti na základě obsahu výstupu
        if not stdout.strip() and not stderr.strip():
            print("Výstup akce je prázdný. Akce považována za selhání.")
            return False, "Output was empty, action failed."

        if "success_keywords" in action:
            print(f"Klíčová slova pro úspěch: {action['success_keywords']}")  # Debugging purposes
            if not all(keyword in combined_output for keyword in action["success_keywords"]):
                print("Výstup neobsahuje žádné z klíčových slov pro úspěch. Akce považována za selhání.")
                return False, combined_output

        return True, combined_output  # Úspěšná akce

    except Exception as e:
        print(f"Došlo k chybě: {e}")
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # Ukončení celé skupiny při chybě
        return False, str(e)

def execute_scenario(scenario_name, selected_network):
    global stop_scenario
    stop_scenario = False  # Resetujeme globální proměnnou při každém spuštění scénáře

    scenario = load_scenario_from_db(scenario_name)
    if not scenario:
        print(f"Scénář '{scenario_name}' nebyl nalezen v databázi.")
        return

    # Spuštění vlákna pro monitorování uživatelského vstupu
    user_input_thread = threading.Thread(target=monitor_user_input, daemon=True)
    user_input_thread.start()

    context = {"selected_network": selected_network, "target_ip": None}

    for step in scenario["steps"]:
        if stop_scenario:
            print("Scénář byl zastaven uživatelem.")
            break

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
        parameters = {key: context.get(value.strip("{{}}"), value) for key, value in step["parameters"].items()}

        # Provedení akce
        success, output = execute_action(action, parameters)

        # Aktualizace kontextu na základě výsledku akce
        update_context(context, step, output, success)

        # Výpis zprávy o úspěchu nebo selhání
        message = step.get("success_message" if success else "failure_message", "")
        for key, value in context.items():
            message = message.replace(f"{{{{{key}}}}}", str(value))
        print(message)

    print("Dokončeno provádění scénáře.")


# def execute_scenario(scenario_name, selected_network):
#     """Provádí kroky scénáře na základě definovaných podmínek a zpráv."""
#     scenario = load_scenario_from_db(scenario_name)
#     if not scenario:
#         print(f"Scénář '{scenario_name}' nebyl nalezen v databázi.")
#         return

#     context = {"selected_network": selected_network, "target_ip": None}

#     for step in scenario["steps"]:
#         description = replace_placeholders(step["description"], context)
#         print(f"\nProvádím krok {step['step_id']}: {description}")

#         # Načtení akce pro tento krok
#         action = load_action(step["action"])
#         if not action:
#             print(f"Akce '{step['action']}' nebyla nalezena v databázi.")
#             break

#         # Zkontrolujeme, zda jsou splněny podmínky pro tento krok
#         if "conditions" in step and not evaluate_conditions(step["conditions"], context):
#             print(step.get("failure_message", "Podmínky pro tento krok nejsou splněny. Ukončuji scénář."))
#             break

#         # Určení parametrů pro akci
#         parameters = {key: context.get(value.strip("{{}}"), value) for key, value in step["parameters"].items()}

#         # Provedení akce
#         success, output = execute_action(action, parameters)

#         # Aktualizace kontextu na základě výsledku akce
#         update_context(context, step, output, success)

#         # Získání zprávy pro úspěch a chybu
#         success_message = step.get("success_message", "")
#         failure_message = step.get("failure_message", "")

#         # Provádíme nahrazení pro každý klíč v `context`
#         for key, value in context.items():
#             placeholder = f"{{{{{key}}}}}"  # Vytvoříme správný formát `{{target_ip}}`
#             success_message = success_message.replace(placeholder, str(value))
#             failure_message = failure_message.replace(placeholder, str(value))

#         # Výpis úspěšné nebo chybové zprávy
#         if success:
#             print("Generovaná úspěšná zpráva:", success_message)  # Kontrolní výpis
#             print(success_message)
#         else:
#             print("Generovaná chybová zpráva:", failure_message)  # Kontrolní výpis
#             print(failure_message)
#             break  # Ukončení scénáře v případě chyby

#     print("Dokončeno provádění scénáře.")


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

    #print("Aktualizovaný kontext po kroku:", context)  # Debugging  Výpis kontextu
    



# ZBYTECNE - smazat po otestovani
# def execute_step(step, network):
#     print(f"Provádím krok: {step['description']}")
#     # Placeholder for execution logic
#     # For example, depending on the step type, it might call scan_network_with_nmap or other functions

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