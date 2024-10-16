
#! GLOBAL PROPERTIES
cytec_stand_ip_address = '10.155.113.70'

all_stands = [
"10.155.113.230", #? CRS112-8G-4S
"10.155.113.231", #? RB960PGS
"10.155.113.232", #? L009UiGS-2HaxD
"10.155.113.233", #? RB5009UG+S+
"10.155.113.234", #? RB4011iGS+
"10.155.113.235", #? CRS304-4XG
"10.155.113.236", #? RB952Ui-5ac2nD
"10.155.113.237", #? CRS326-24G-2S+
"10.155.113.238", #? CRS326-4C+20G+2Q+
"10.155.113.239", #? CRS312-4C+8XG
"10.155.113.240", #? C53UiG+5HPaxD2HPaxD
"10.155.113.241"  #? RB750r2
]

run_all_test_list = [ 
    'simple_ping.py',
    'interface_disable_enable.py',
    'tester_interface_disable_enable.py',
    'interface_disable_enable_while_sending_traffic.py',
    'reboot.py',
    'max_mtu.py',
    'send_traffic.py',
    'advertisement.py',
]

dut_port = 'ether1' 
interactive_mode = False
details = True

#! TEST PROPERTIES
#? [0] Simple ping test
ping_count = 10

#? [1] DUT interface disable/enable test

#? [2] Tester (stand) interface disable/enable test

#? [3] Interface disable/enable while sending traffic test'

#? [4] DUT reboot test
loop_count = 2

#? [5] Maximum MTU test

#? [6] Traffic test
duration_min = 1 # 1440 minutes in 1 day
mbps = 500
#? [7] Advertisement test
advertisements = ["10M-baseT-full", "100M-baseT-full", "1G-baseT-full"]
#? [8] Reset Configuration


