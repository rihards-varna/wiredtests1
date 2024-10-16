#!/usr/bin/env python3

from settings import cytec_stand_ip_address,dut_port,all_stands,duration_min,mbps,interactive_mode

import pexpect
import sys
import time
import paramiko
import socket
import json
import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


from colorama import Fore,Back,Style,init
init(autoreset=True)
print(Back.YELLOW + '[6]TRAFFIC TEST                                                                           ')

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

def stats_result(a,b):
    global test_result
    
    errors_found = []
    result=int((b/a)*100)
    
    # if result >= 95 and int_stand_rx_fcs_error == 0 and int_dut_rx_fcs_error == 0 and int_dut_tx_fcs_error == 0 and int_dut_rx_code_error == 0 and int_dut_rx_carrier_error == 0 and int_dut_rx_length_error == 0 and dut_tx_carrier_sense_error == 0 and dut_rx_align_error == 0:
    #     print('NO ERRORS FOUND')
    if result < 95:
        errors_found.append('RECEIVED:'+ Fore.RED + f'{result}%')
    if int_stand_rx_fcs_error > 0:
        errors_found.append(f'stand rx-fcs-error:{int_stand_rx_fcs_error}')
    if int_dut_rx_fcs_error > 0:
        errors_found.append(f'rx-fcs-error:{int_dut_rx_fcs_error}')
    if int_dut_tx_fcs_error > 0:
        errors_found.append(f'tx-fcs-error:{int_dut_tx_fcs_error}')
    if int_dut_rx_code_error > 0:
        errors_found.append(f'rx-code-error:{int_dut_rx_code_error}')
    if int_dut_rx_carrier_error > 0:
        errors_found.append(f'rx-carrier-error:{int_dut_rx_carrier_error}')
    if int_dut_rx_length_error > 0:
        errors_found.append(f'rx-length-error:{int_dut_rx_length_error}')
    if dut_tx_carrier_sense_error > 0:
        errors_found.append(f'tx-carrier-sense-error:{dut_tx_carrier_sense_error}')
    if dut_rx_align_error > 0:
        errors_found.append(f'rx-align-error:{dut_rx_align_error}')
    
    if errors_found:
        print(Fore.RED + "ERRORS FOUND:")
        for statement in errors_found:
            print(statement)
        test_result = False
    else:
        print(Fore.GREEN + 'NO ERRORS FOUND')
        if test_result == False:
            pass
        else:
            test_result = True
        
def bytes_to_megabytes(bytes):
    megabytes = bytes / (1024 * 1024)
    int_megabytes = int(megabytes)
    return int_megabytes


for i, current_stand in enumerate(all_stands):
    #! FIND STAND MODEL NAME AND ARCHITECTURE
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(current_stand, username="admin", password="")
    stdin, stdout, stderr = ssh.exec_command(f'{{:local model [/system routerboard get model];:put $model}}')
    model = stdout.read().decode()
    
    stdin, stdout, stderr = ssh.exec_command(f'{{:local architecture [/system resource/ get architecture-name ];:put $architecture}}')
    architecture = stdout.read().decode()
    ssh.close()
    
    #! DEFINING EXCEPTIONS
    if 'RB5009UG+S+' in model or 'CRS304-4XG' in model or 'C53UiG+5HPaxD2HPaxD' in model or 'CRS326-4C+20G+2Q+' in model or 'CRS312-4C+8XG' in model:
        stand_port = 'ether1'
    else:
        stand_port = 'ether2'
    
    if 'mipsbe' in architecture:
        mbps = '100'
    else:
        from settings import mbps
        
    print(Style.BRIGHT + "==========================================================================================")
    print(Style.BRIGHT + f'STAND{i+1}: {model.strip()} ({current_stand})')
    print(Style.BRIGHT + "==========================================================================================")
    
    #! OPEN CYTEC PORT
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(cytec_stand_ip_address, username="admin", password="")
    ssh.exec_command('/system ssh-exec address=127.0.0.1 user=devel command="echo C > /dev/console"')
    time.sleep(1.0)
    ssh.exec_command(f'/system ssh-exec address=127.0.0.1 user=devel command="echo L 0 {i} > /dev/console"')
    time.sleep(1.0)
    ssh.exec_command(f'/system ssh-exec address=127.0.0.1 user=devel command="echo L 0 {i} > /dev/console"')
    time.sleep(1.0)
    print(f"Cytec Module 0, Switch {i} ENABLED")
    
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
    #? CREATE NAT RULE
    stdin, stdout, stderr = ssh.exec_command('ip firewall/nat/print')
    nat_print = stdout.read().decode()
    if f"dst-address={current_stand}" in nat_print and 'to-addresses=192.168.1.2' in nat_print and 'to-ports=22' in nat_print:
        pass
    else:
        ssh.exec_command(f'/ip firewall nat add action=dst-nat chain=dstnat dst-address={current_stand} dst-port=1111 protocol=tcp to-addresses=192.168.1.2 to-ports=22')
    #? CREATE TG & STREAM
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(current_stand, username="admin", password="")
    # print(f"Creating packet template and stream..")
    ssh.exec_command('tool traffic-generator packet-template/remove [f]')
    time.sleep(0.5)
    ssh.exec_command('tool traffic-generator stream/remove [f]')
    time.sleep(0.5)
    ssh.exec_command(f'/tool traffic-generator packet-template add header-stack=mac,ip,udp interface={stand_port} ip-dst=192.168.1.1 ip-src=192.168.1.1 ip-gateway=192.168.1.2 name=send_traffic')
    time.sleep(0.5)
    ssh.exec_command(f'/tool traffic-gene stream add name=send_traffic id=0 tx-template=send_traffic packet-size=64-1500 mbps={mbps}')
    
    #! PING DUT
    stdin, stdout, stderr = ssh.exec_command(f"ping 192.168.1.2 count=2")
    check_if_alive = stdout.read().decode()
    
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
        
        #LOGIN INTO DUT
        print("Logging into DUT..")
        a.send(f'tool mac-telnet host={dut_mac}\r\n') #pie ip neighbor drīkst parādīties tikai viena pieslēgtā iekārta 
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
            print("DONE..")
        elif c==1:
            a.sendcontrol('c')
            a.expect_exact('>')
            print("DONE..")
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
        print("DONE")
        print(f"Resetting stats..")
        a.send('/interface/ethernet/reset-counters [f]\r\n')
        a.expect_exact('>')
        time.sleep(1.0)
        print("DONE")
        a.close()
    else:
        print('IP address found')
        
    # ! START TRAFFIC TEST
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
        
    print(f"Resetting stats..")
    ssh.exec_command('/interface/ethernet/reset-counters [f]')
    print("DONE")
    print(f"Sending traffic for {duration_min } min..")
    ssh.exec_command('/tool traffic-generator stop')
    ssh.exec_command('/tool traffic-gene packet-template/set [f]')
    time.sleep(1.0)
    ssh.exec_command('/tool traffic-generator start')
    
    time_countdown = 0
    while True:
        stdin, stdout, stderr = ssh.exec_command("/ip/neighbor/print")
        stand_link_status = stdout.read().decode()
        if stand_port + ' ' not in stand_link_status:
            time.sleep(1.0)
            print(Fore.RED + 'Link-down detected')
            test_result = False
            pause_test()
            break
        else:
            time_countdown += 1
            if time_countdown >= (duration_min * 60) / 2:             # APSTADINA TG 
                ssh.exec_command('/tool traffic-generator stop')
                print("DONE")
                if test_result == False:
                    pass
                else:
                    test_result = True
                break
            time.sleep(2)
            
    stdin, stdout, stderr = ssh.exec_command(f"ping 192.168.1.2 count=2")
    check_if_alive = stdout.read().decode()
    
    # ! COLLECTING STAND STATS
    # RX/TX BYTES ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{stand_port}";:local tx [/int eth get $interface tx-bytes];:put $tx}}')
    stand_tx_bytes = stdout.read().decode()
    int_stand_tx_bytes = int(stand_tx_bytes)
    
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{stand_port}";:local rx [/int eth get $interface rx-bytes];:put $rx}}')
    stand_rx_bytes = stdout.read().decode()
    int_stand_rx_bytes = int(stand_rx_bytes)
    
    # RX/TX FCS ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{stand_port}";:local rxfcs [/int eth get $interface rx-fcs-error];:put $rxfcs}}')
    stand_rx_fcs_error = stdout.read().decode()
    if "\r\n" or "" in stand_rx_fcs_error:
        stand_rx_fcs_error = 0
    int_stand_rx_fcs_error = int(stand_rx_fcs_error)
    
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{stand_port}";:local txfcs [/int eth get $interface tx-fcs-error];:put $txfcs}}')
    stand_tx_fcs_error = stdout.read().decode()
    if "\r\n" or "" in stand_tx_fcs_error:
        stand_tx_fcs_error = 0
    int_stand_tx_fcs_error = int(stand_tx_fcs_error)
    
    ssh.close()
    
    # ! COLLECTING DUT STATS
    #? LOGIN INTO DUT
    print('[SECURE SHELL]')
    print("Logging into DUT..")
    
    ssh = paramiko.SSHClient() 
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    dut_ssh_link_established = False
    for attempt in range(3): 
        try:
            ssh.connect(current_stand, username="admin", password="", port=1111)
            dut_ssh_link_established = True
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
            
    if not dut_ssh_link_established:
        print(Fore.RED + 'Failed to connect to DUT after 3 attempts.')
        test_result = False
        pause_test()
        pass
    
    # RX/TX FCS ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local rxfcs [/int eth get $interface rx-fcs-error];:put $rxfcs}}')
    dut_rx_fcs_error = stdout.read().decode()
    if "\r\n" or "" in dut_rx_fcs_error:
        dut_rx_fcs_error = 0
    int_dut_rx_fcs_error = int(dut_rx_fcs_error)
    
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local txfcs [/int eth get $interface tx-fcs-error];:put $txfcs}}')
    dut_tx_fcs_error = stdout.read().decode()
    if "\r\n" or "" in dut_tx_fcs_error:
        dut_tx_fcs_error = 0
    int_dut_tx_fcs_error = int(dut_tx_fcs_error)
    
    # RX CODE ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local rxcode [/int eth get $interface rx-code-error];:put $rxcode}}')
    dut_rx_code_error = stdout.read().decode()
    if "\r\n" or "" in dut_rx_code_error:
        dut_rx_code_error = 0
    int_dut_rx_code_error = int(dut_rx_code_error)
    
    # RX-CARRIER-ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local rxcarrier [/int eth get $interface rx-carrier-error];:put $rxcarrier}}')
    dut_rx_carrier_error = stdout.read().decode()
    if "\r\n" or "" in dut_rx_carrier_error:
        dut_rx_carrier_error = 0
    int_dut_rx_carrier_error = int(dut_rx_carrier_error)
    
    # RX-LENGTH-ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local rxlength [/int eth get $interface rx-carrier-error];:put $rxlength}}')
    dut_rx_length_error = stdout.read().decode()
    if "\r\n" or "" in dut_rx_length_error:
        dut_rx_length_error = 0
    int_dut_rx_length_error = int(dut_rx_length_error)
    
    # TX-CARRIER-SENSE-ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local txcarrriersense [/int eth get $interface tx-carrier-sense-error];:put $txcarriersense}}')
    dut_tx_carrier_sense_error = stdout.read().decode()
    if "\r\n" or "" in dut_tx_carrier_sense_error:
        dut_tx_carrier_sense_error = 0
    int_dut_tx_carrier_sense_error = int(dut_tx_carrier_sense_error)
    
    # RX-ALIGN-ERROR
    stdin, stdout, stderr = ssh.exec_command(f'{{:local interface "{dut_port}";:local rxalign [/int eth get $interface rx-align-error];:put $rxalign}}')
    dut_rx_align_error = stdout.read().decode()
    if "\r\n" or "" in dut_rx_align_error:
        dut_rx_align_error = 0
    int_dut_rx_align_error = int(dut_rx_align_error)
    
    
    ssh.close()
    print("------------------------------------------------------------------------------------------")
    print(f'TX {bytes_to_megabytes(int_stand_tx_bytes)} MB')
    print(f'RX {bytes_to_megabytes(int_stand_rx_bytes)} MB')
    stats_result(int_stand_tx_bytes,int_stand_rx_bytes)
    
    #! SAVE TEST RESULTS IN ARRAY
    if test_result:
        all_test_results.append('+')  
    else:
        all_test_results.append('FAILED')  
print("------------------------------------------------------------------------------------------")

#! SAVE TEST RESULTS IN JSON
def return_results():
    return all_test_results
results_6 = return_results()
#?SAVE IN JSON
with open("results_6.json", "w") as f:
    json.dump(results_6, f)

if test_result == False:
    print(Back.RED + 'TEST FAILED                                                                               ')
    sys.exit(1)
if test_result == True:
    print(Back.GREEN + 'TEST PASSED                                                                               ')
    sys.exit(0)
    