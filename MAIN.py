#!/usr/bin/env python3

from prettytable import PrettyTable, ALL
from settings import run_all_test_list,details
import subprocess
import json
import os

from colorama import Fore,Back,Style,init
init(autoreset=True)

#! 3 PANEM ADVERTISEMENTS NO ABAM PUSEM UN MATCHO AR TIEM KO GRIBAM TESTET, JA GAN VIENA, GAN OTRA PUSE IR X ADVERT TAD TEST

#! RESET OLD JSONS
def reset_json_files():
    for filename in os.listdir('.'):
        if filename.startswith('results_') and filename.endswith('.json'):
            with open(filename, 'w') as f:
                json.dump(["None", "None", "None", "None", "None", "None", "None", "None", "None", "None", "None", "None"], f)

#! RUN SUBPROCESS
def function(test):
    try:
        result = subprocess.run(["python3", test], check=True)
        return (test, Fore.GREEN + "TEST PASSED")
    
    except subprocess.CalledProcessError as e:
        return (test,Fore.RED + "FAILED")

#! TABLE
#? JSON RESULT DOWNLOAD
def download_results():
    # Load each JSON file into its own variable
    with open("results_0.json", "r") as f:
        results_0 = json.load(f)
    
    with open("results_1.json", "r") as f:
        results_1 = json.load(f)
        
    with open("results_2.json", "r") as f:
        results_2 = json.load(f)
        
    with open("results_3.json", "r") as f:
        results_3 = json.load(f)
        
    with open("results_4.json", "r") as f:
        results_4 = json.load(f)
        
    with open("results_5.json", "r") as f:
        results_5 = json.load(f)
        
    with open("results_6.json", "r") as f:
        results_6 = json.load(f)
        
    with open("results_7.json", "r") as f:
        results_7 = json.load(f)
        
    return results_0, results_1, results_2, results_3, results_4, results_5, results_6, results_7

#? TABLE CREATION
from prettytable import PrettyTable

def create_table(results_0, results_1, results_2, results_3, results_4, results_5, results_6, results_7):
    
    table = PrettyTable()
    
    headers = ["TEST"] + ["CRS112-8G-4S", "RB960PGS", "L009UiGS-2HaxD", "RB5009UG+S+",
    "RB4011iGS+", "CRS304-4XG", "RB952Ui-5ac2nD", "CRS326-24G-2S+",
    "CRS326-4C+20G+2Q+", "CRS312-4C+8XG", "C53UiG+5HPaxD2HPaxD", "RB750r2"]
    
    table.field_names = headers
    
    for header in headers:
        table.align[header] = "l" #align text to left
    
    max_length = len(headers) - 1 
    
    rows = [
        ["[0] Simple ping test"] + results_0 + ["None"] * (max_length - len(results_0)),
        ["[1] Interface disable/enable test"] + results_1 + ["None"] * (max_length - len(results_1)),
        ["[2] Tester (stand) interface disable/enable test"] + results_2 + ["None"] * (max_length - len(results_2)),
        ["[3] Interface disable/enable while sending traffic test"] + results_3 + ["None"] * (max_length - len(results_3)),
        ["[4] Reboot test"] + results_4 + ["None"] * (max_length - len(results_4)),
        ["[5] Maximum MTU test"] + results_5 + ["None"] * (max_length - len(results_5)),
        ["[6] Traffic test"] + results_6 + ["None"] * (max_length - len(results_6)),
        ["[7] Advertisement test"] + results_7 + ["None"] * (max_length - len(results_7))
    ]

    for row in rows:
        table.add_row(row)
    
    table.border = True  # border around tables
    table.hrules = ALL  # horizontal lines between rows

    return table


#! LISTS
user_option_list = [
    '[0] Simple ping test',
    '[1] Interface disable/enable test',
    '[2] Tester (stand) interface disable/enable test',
    '[3] Interface disable/enable while sending traffic test',
    '[4] Reboot test',
    '[5] Maximum MTU test',
    '[6] Traffic test',
    '[7] Advertisement test',
    '[8] Reset Configuration',
    '[9] Run all tests'
]

python_file_list = [ 
    'simple_ping.py',
    'interface_disable_enable.py',
    'tester_interface_disable_enable.py',
    'interface_disable_enable_while_sending_traffic.py',
    'reboot.py',
    'max_mtu.py',
    'send_traffic.py',
    'advertisement.py',
    'reset_configuration.py'
]

print('loko')


if __name__ == "__main__":
    
    #! DELETE OLD JSONS
    reset_json_files()
    
    for test in user_option_list:
        print(test)
    print("------------------------------------------------------------------------------------------") 

    while True:
        try:
            results = []
            user_input = int(input("Test number: "))
            
            # ! RUN ALL TESTS
            if user_input == 9:
                for element in (run_all_test_list):
                    print('\n\n')
                    results.append(function(element))
                    
                #? SUMMARY:
                print('\n\n' + Back.CYAN + "TEST SUMMARY:                                                                             ")
                for test, status in results:
                    print(f"{test}: {status}")
                break
            #! RUN SIGNLE TEST
            else:
                print('\n\n')
                function(python_file_list[user_input])
                break
        except ValueError:
            print("Invalid input! Please enter a valid number.")
        except IndexError:
            print("Invalid input! Please select a test from the list.")

    if details == True:
        print('\n')
        #! TABLE
        results_0, results_1, results_2, results_3, results_4, results_5, results_6, results_7 = download_results()
        results_table = create_table(results_0, results_1, results_2, results_3, results_4, results_5, results_6, results_7)

        print(results_table)
