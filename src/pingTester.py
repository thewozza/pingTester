#!/usr/bin/python

import subprocess, platform
from datetime import datetime
import csv
import socket
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException,NetMikoAuthenticationException

def check_ping(hostname):

    # just do a quick ping test to the remote server
    # there's no point going further if we can't ping it
    try:
        response  = subprocess.check_output("ping -{} 1 {}".format('n' if platform.system().lower()=="windows" else 'c', hostname), shell=True)
    
    except Exception:
        return False
    return True


def get_ip():
    # I blindly copied this from the internet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 0))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
    
def ie4kPing(sourceAddr,repetitions,packetSize,filename):
    switch = {
        'device_type': 'cisco_ios',
        'ip': sourceAddr,
        'username': 'cisco',
        'password': 'cisco',
        'secret': 'cisco',
        'port' : 22,          # optional, defaults to 22
        'verbose': False,       # optional, defaults to False
        'global_delay_factor': 2 # for remote systems when the network is slow
    }
    try:
        # the minimum packet size is 36
        # so if someone puts in a smaller value we assume they mean "smallest possible"
        if packetSize < 36:
            packetSize = 36
            
        # this is what we connect to
        net_connect = ConnectHandler(**switch)
        
        # we get the ospf neighbors
        # and parse out the IPs for forward and reverse neighbors
        ospfCommand = "show ospf neighbor vlan " + str(77)
        ospf77 = net_connect.send_command(ospfCommand).split('\n')[-1].split(' ')[0]
        ospfCommand = "show ospf neighbor vlan " + str(88)
        ospf88 = net_connect.send_command(ospfCommand).split('\n')[-1].split(' ')[0]

    except NetMikoTimeoutException,NetMikoAuthenticationException:
        print "Not able to connect to " + sourceAddr
    finally:
        # initialize the output dictionary
        pingOutput = {}
        
        # if there's no ospf peer we just skip the ping test
        if ospf77:
            # initialize the output dictionary for the ospf77 tests
            pingOutput[ospf77] = {}
            pingCommand = 'ping ' + ospf77 + " repeat " + repetitions + " size " + packetSize
            line = net_connect.send_command(pingCommand).split('\n')[-1].split(' ')
            
            # break out all the results in to the right variables
            pingOutput[ospf77]['percent'] = line[3]
            (pingOutput[ospf77]['RTTmin'],pingOutput[ospf77]['RTTavg'],pingOutput[ospf77]['RTTmax']) = line[9].split('/')
        
        # if there's no ospf peer we just skip the ping test
        if ospf88:
            # initialize the output dictionary for the ospf88 tests
            pingOutput[ospf88] = {}
            pingCommand = 'ping ' + ospf88 + " repeat " + repetitions + " size " + packetSize
            line = net_connect.send_command(pingCommand).split('\n')[-1].split(' ')
            
            # break out all the results in to the right variables
            pingOutput[ospf88]['percent'] = line[3]
            (pingOutput[ospf88]['RTTmin'],pingOutput[ospf88]['RTTavg'],pingOutput[ospf88]['RTTmax']) = line[9].split('/')
        
        # we always sanely disconnect
        net_connect.disconnect()
        # we use this as row data in the output
        currentTime = str(datetime.time(datetime.now()))
        

        # append to master CSV
        # this creates a single CSV for this host for all tests
        with open(filename + ".csv", "ab") as csvfile:
            csvoutput = csv.writer(csvfile, delimiter=',')
            # iterate through the dictionary and
            # drop the value, key pairs as variables that we can reference
            # peerIP is IP of the neighbor (for either vlan 77 or 88)
            # dictLoop is a dictionary containing the results of the tests
            for peerIP, dictLoop in pingOutput.items():
                csvoutput.writerow([currentTime,sourceAddr,peerIP,repetitions,packetSize,dictLoop["percent"],dictLoop["RTTmin"],dictLoop["RTTavg"],dictLoop["RTTmax"]])
        # sanely close the file handler
        csvfile.close()
    
testFile = csv.DictReader(open("pingTesterTests.csv"))

try:
    # we use this as the CSV filename for output
    currentDateTime = str((datetime.date(datetime.now()))) + "." + str(datetime.time(datetime.now())).split(".")[0].replace(':','.')

    for row in testFile:
        # we make sure we can ping the switch before we do anything else
        if check_ping(row['SourceIP']):
            ie4kPing(row['SourceIP'],row['repeat'],row['size'],currentDateTime)
        else:
            "Not pingable no tests possible"
except IndexError:
    pass