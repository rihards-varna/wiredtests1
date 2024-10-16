#!/usr/bin/env python3

from settings import cytec_stand_ip_address,dut_port,ping_count,all_stands,interactive_mode

import pexpect
import sys
import time
import paramiko
import re
import socket
import json
import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


from colorama import Fore,Back,Style,init
init(autoreset=True)
print(Back.YELLOW + '[0]SIMPLE PING TEST                                                                       ')

test_result = None
all_test_results = []

#? INTERACTIVE MODE = True
def pause_test():
    if interactive_mode == True:
        while True:
            resume_test = input('Test paused. Enter "y" to continue: ').strip().lower()
            if resume_test == 'y':
                break
            else:
                print("Invalid input! Please enter 'y' to continue.")

def wait_link_ok_and_ping(ping):
    global test_result
    
    print(f"Waiting for neighbor on {stand_port}..")
    failure_count = 0
    while True:
        try:
            stdin, stdout, stderr = ssh.exec_command("/ip/neighbor/print")
            stand_link_status = stdout.read().decode()
            
            if stand_port + ' ' in stand_link_status:
                time.sleep(2.0)
                print("Neighbor found")
                print('Pinging DUT..')
                
                ping_success = False
                for attempt in range(0, 3):
                    try:
                        stdin, stdout, stderr = ssh.exec_command(f'ping 192.168.1.2 count={ping}')
                        ping_output = stdout.read().decode()
                        
                        if f'received={ping}' in ping_output or "packet-loss=0%" in ping_output:
                            print(Fore.GREEN + f'Ping attempt {attempt + 1} successful {ping}/{ping}')
                            ping_success = True
                            break
                        else:
                            packet_loss_match = re.search(r'packet-loss=(\d+)%', ping_output)
                            if packet_loss_match:
                                packet_loss = int(packet_loss_match.group(1))
                            else:
                                print(Fore.RED + "Could not determine packet loss from ping output.")
                                test_result = False
                                pause_test()
                    
                    except paramiko.SSHException as e:
                        print(Fore.RED + f"SSH command error on ping attempt {attempt + 1}: {e}")
                        break
                    except Exception as e:
                        print(Fore.RED + f"Unexpected error on ping attempt {attempt + 1}: {e}")
                        break
                    
                    if attempt < 2:
                        print(Fore.RED + f"Ping attempt {attempt + 1} failed with a packet loss of {packet_loss}%. Retrying in 20 seconds...")
                        time.sleep(20)
                    else:
                        print(Fore.RED + f"Ping attempt {attempt + 1} failed with a packet loss of {packet_loss}%.")
                        break
                
                if not ping_success:
                    test_result = False
                    pause_test()
                else:
                    test_result = True
                break
            else:
                failure_count += 1
                if failure_count >= 30:
                    print(Fore.RED + "Neighbor not found! Timeout 60sec")
                    test_result = False
                    pause_test()
                    break
                else:
                    time.sleep(2)
        
        except paramiko.SSHException as e:
            print(Fore.RED + f"SSH command error while checking neighbor: {e}")
            test_result = False
            pause_test()
            break
        except Exception as e:
            print(Fore.RED + f"Unexpected error while checking neighbor: {e}")
            test_result = False
            pause_test()
            break

for i, current_stand in enumerate(all_stands):
    
    #! FIND STAND MODEL NAME
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(current_stand, username="admin", password="")
    stdin, stdout, stderr = ssh.exec_command(f'{{:local model [/system routerboard get model];:put $model}}')
    model = stdout.read().decode()
    ssh.close()
    
    #! DEFINING EXCEPTIONS
    if 'RB5009UG+S+' in model or 'CRS304-4XG' in model or 'C53UiG+5HPaxD2HPaxD' in model or 'CRS326-4C+20G+2Q+' in model or 'CRS312-4C+8XG' in model:
        stand_port = 'ether1'
    else:
        stand_port = 'ether2'
        
    print(Style.BRIGHT + "==========================================================================================")
    print(Style.BRIGHT + f'STAND{i+1}: {model.strip()} ({current_stand})')
    print(Style.BRIGHT + "==========================================================================================")
    
    #! OPEN CYTEC PORT
    ssh.connect(cytec_stand_ip_address, username="admin", password="")
    ssh.exec_command('/system ssh-exec address=127.0.0.1 user=devel command="echo C > /dev/console"')
    time.sleep(1.0)
    ssh.exec_command(f'/system ssh-exec address=127.0.0.1 user=devel command="echo L 0 {i} > /dev/console"')
    time.sleep(1.0)
    ssh.exec_command(f'/system ssh-exec address=127.0.0.1 user=devel command="echo L 0 {i} > /dev/console"')
    time.sleep(1.0)
    print(f"Cytec Module 0, Switch {i} ENABLED")
    ssh.close()
    
    #! CHECK LINK ESTABLISHMENT
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(current_stand, username="admin", password="")
    failure_count1 = 0
    skip_to_next_stand = False
    while True:
        stdin, stdout, stderr = ssh.exec_command("/ip/neighbor/print")
        stand_link_status = stdout.read().decode()
        if stand_port + ' ' in stand_link_status:
            time.sleep(1.0)
            print("Neighbor found")
            break
        else:
            failure_count1 += 1
            if failure_count1 >= 30:
                print(Fore.RED + "Neighbor not found! Timeout 60sec")
                ssh.close()
                test_result = False
                pause_test()
                skip_to_next_stand = True
                break
            time.sleep(2)
    if skip_to_next_stand:
        print('Skipping to the next stand')
        all_test_results.append('FAILED')  
        continue
            
    #! FIND DUT MAC
    stdin, stdout, stderr = ssh.exec_command(f':put [/ip neighbor/get [find interface="{stand_port}"] value-name=mac-address]')
    dut_mac = stdout.read().decode()
    
    #! SET UP STAND CONFIG
    #? DISCOVERY INTERVAL
    stdin, stdout, stderr = ssh.exec_command('/ip neighbor/discovery-settings/set discover-interval=5')
    #? CREATE IP ADDRESS(IF NEEDED)
    stdin, stdout, stderr = ssh.exec_command('ip address print')
    address_print = stdout.read().decode()
    if 'address=192.168.1.1' in address_print and f'interface={stand_port}' in address_print and 'network=192.168.1.0' in address_print:
        pass
    else:
        ssh.exec_command(f'/ip add add address=192.168.1.1/24 interface={stand_port}')
    
    #! PING DUT
    stdin, stdout, stderr = ssh.exec_command(f"ping 192.168.1.2 count=2")
    check_if_alive = stdout.read().decode()
    
    #! SET UP IP IF NEEDED
    if "packet-loss=100%" in check_if_alive:
        ssh.close()
        print('[TELNET]')
        print("Logging into STAND..")
        a = pexpect.spawn(f'telnet {current_stand}')
        # a.logfile = sys.stdout.buffer
        a.expect_exact('Login:')
        a.send('admin\n')
        a.expect_exact('Password:')
        a.send('\n')
        
        g = a.expect_exact(['new password>','>'])
        if g==0:
            a.sendcontrol('c')
            a.expect_exact('>')
        print(f"DONE")
        
            #LOGIN TO DUT
        print(f"Logging into DUT..")
        a.send(f'tool mac-telnet host={dut_mac}\r\n') 
        a.expect_exact('Login:')
        a.send('admin\n')
        a.expect_exact('Password:')
        a.send('\n')
        c = a.expect_exact(['Do you want to see the software license? [Y/n]:', 'new password>','>'])
        if c==0:
            a.send('n\n\n')
            a.expect_exact('new password>')
            a.sendcontrol('c')
            a.expect_exact('>')
            print("DONE")
        elif c==1:
            a.sendcontrol('c')
            a.expect_exact('>')
            print("DONE")
        elif c==2:
            print('DONE')
        
        # Adding IP address on DUT
        print(f"Setting up IP address on DUT..")
        a.send(f'/ip address add address=192.168.1.2/24 interface={dut_port}\r\n')
        d = a.expect_exact(['>','failure: already have such address'])
        a.send('/ip route remove 0\r\n')
        f = a.expect_exact(['>','no such item (4)','no such item'])
        a.send('/ip route add gateway=192.168.1.1\r\n')
        a.expect_exact('>')
        time.sleep(2.0)
        print(f"DONE")
        a.close()
        
    #? LOGIN INTO STAND
    print('[SECURE SHELL]')
    print("Logging into DUT..")
    
    ssh = paramiko.SSHClient() 
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    stand_ssh_link_established = False
    for attempt in range(3): 
        try:
            ssh.connect(current_stand, username="admin", password="")
            stand_ssh_link_established = True
            if attempt > 0:
                print(Fore.GREEN + f'Connection attempt {attempt + 1} successful.')
            else:
                print("DONE")
            break  
        except paramiko.SSHException as e:
            print(Fore.RED + f'SSH-paramiko error: {e}')
            if attempt < 2: 
                print(Fore.RED + f"Connection attempt {attempt + 1} failed. Retrying in 20 seconds...")
                time.sleep(20)
            else:
                print(Fore.RED + f"Connection attempt {attempt + 1} failed.")
                break
                
        except socket.timeout as e:
            print(Fore.RED + f"Connection timed out: {e}")
            if attempt < 2: 
                print(Fore.RED + f"Connection attempt {attempt + 1} failed due to timeout. Retrying in 20 seconds...")
                time.sleep(20)
            else:
                print(Fore.RED + f"Connection attempt {attempt + 1} failed due to timeout.")
                break
                
        except Exception as e:
            print(Fore.RED + f'General SSH error: {e}')
            if attempt < 2: 
                print(Fore.RED + f"Connection attempt {attempt + 1} failed. Retrying in 20 seconds...")
                time.sleep(20)
            else:
                print(Fore.RED + f"Connection attempt {attempt + 1} failed.")
                break
            
    if not stand_ssh_link_established:
        print(Fore.RED + 'Failed to connect to DUT after 3 attempts.')
        test_result = False
        pause_test()
        pass
        
        wait_link_ok_and_ping(ping_count)
    else:
        print('IP address found')
        wait_link_ok_and_ping(ping_count)
        
    #! SAVE TEST RESULTS IN ARRAY
    if test_result:
        all_test_results.append('+')  
    else:
        all_test_results.append('FAILED')  
print("------------------------------------------------------------------------------------------")
    
#! SAVE TEST RESULTS IN JSON
def return_results():
    return all_test_results
results_0 = return_results()
#?SAVE IN JSON
with open("results_0.json", "w") as f:
    json.dump(results_0, f)

if test_result == False:
    print(Back.RED + 'TEST FAILED                                                                               ')
    sys.exit(1)
if test_result == True:
    print(Back.GREEN + 'TEST PASSED                                                                               ')
    sys.exit(0)
    

