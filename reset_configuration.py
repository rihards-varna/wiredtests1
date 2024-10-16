from settings import cytec_stand_ip_address,dut_port,all_stands,interactive_mode

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
print(Back.YELLOW + '[8]CONFIGURATION RESET                                                                    ')

test_result = None

#? INTERACTIVE MODE = True
def pause_test():
    if interactive_mode == True:
        while True:
            resume_test = input('Test paused. Enter "y" to continue: ').strip().lower()
            if resume_test == 'y':
                break
            else:
                print("Invalid input! Please enter 'y' to continue.")

#SETTING CYTEC SWITCH AND IP ADDRESS 
for i, current_stand in enumerate(all_stands[:1]):
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
        
        #LOGIN TO DUT
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
            print(f"DONE")
        elif c==1:
            a.sendcontrol('c')
            a.expect_exact('>')
            print(f"DONE")
        elif c==2:
            print('DONE')
        # Adding IP address on DUT
        print("Executing command '/system/reset-configuration skip-backup=yes no-defaults=yes'")
        a.send(f'/system/reset-configuration skip-backup=yes no-defaults=yes\r\n')
        a.expect_exact('Dangerous! Reset anyway? [y/N]: ')
        a.send('y')
        f = a.expect_exact(['system configuration will be reset','Connection closed'])
        time.sleep(1.0)
        print(f"DONE")
        a.close()
        
    else:
    #! DUT RESET CONFIGURATION
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
        
        print("Executing command '/system/reset-configuration skip-backup=yes no-defaults=yes'")
        ssh.exec_command('/system/reset-configuration skip-backup=yes no-defaults=yes')
        ssh.exec_command(f'y')
        ssh.close()
        print(f"DONE")
        
    if test_result == False:
        pass
    else:
        test_result = True
        
print("------------------------------------------------------------------------------------------")

if test_result == False:
    print(Back.RED + 'RESET FAILED                                                                              ')
    sys.exit(1)
if test_result == True:
    print(Back.GREEN + 'RESET SUCCESSFUL                                                                          ')
    sys.exit(0)