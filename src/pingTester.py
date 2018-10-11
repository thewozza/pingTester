#!/usr/bin/python

import subprocess, platform
from datetime import datetime
import csv
import socket
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException,NetMikoAuthenticationException
import time

def check_ping(hostname):

    # just do a quick ping test to the remote server
    # there's no point going further if we can't ping it
    output = subprocess.Popen(["ping.exe",hostname],stdout = subprocess.PIPE).communicate()[0]

    if ('unreachable' in output):
        return False
    else:
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
    
def ie4kPing(sourceAsset,sourceAddr,repetitions,packetSize,filename):
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
        ospf77 = ""
        ospf88 = ""
        print sourceAddr
        # we get the ospf neighbors
        # and parse out the IPs for forward and reverse neighbors
        time.sleep(1)
        ospfCommand = "show ospf neighbor vlan " + str(77)
        ospf77 = net_connect.send_command(ospfCommand).split('\n')[-1].split(' ')[0]
        time.sleep(1)
        ospfCommand = "show ospf neighbor vlan " + str(88)
        ospf88 = net_connect.send_command(ospfCommand).split('\n')[-1].split(' ')[0]

    except NetMikoTimeoutException,NetMikoAuthenticationException:
        return
    finally:
        # initialize the output dictionary
        pingOutput = {}
        print sourceAddr, ospf77, ospf88
        # if there's no ospf peer we just skip the ping test
        if ospf77:
            # initialize the output dictionary for the ospf77 tests
            pingOutput[ospf77] = {}
            pingCommand = 'ping ' + ospf77 + " repeat " + repetitions + " size " + packetSize
            time.sleep(1)
            line = net_connect.send_command(pingCommand).split('\n')[-1].split(' ')
            
            # break out all the results in to the right variables
            pingOutput[ospf77]['percent'] = line[3]
            (pingOutput[ospf77]['RTTmin'],pingOutput[ospf77]['RTTavg'],pingOutput[ospf77]['RTTmax']) = line[9].split('/')

            # iterate over the consist list to see what assets 
            # our peers are on
            for assetNum in consist:
                if ospf77 in consist[assetNum]['SW0']:
                    pingOutput[ospf77]['asset'] = str(assetNum)
                    break
                elif ospf77 in consist[assetNum]['SW1']:
                    pingOutput[ospf77]['asset'] = str(assetNum)
                    break
                    
        # if there's no ospf peer we just skip the ping test
        if ospf88:
            # initialize the output dictionary for the ospf88 tests
            pingOutput[ospf88] = {}
            pingCommand = 'ping ' + ospf88 + " repeat " + repetitions + " size " + packetSize
            time.sleep(1)
            line = net_connect.send_command(pingCommand).split('\n')[-1].split(' ')
            
            # break out all the results in to the right variables
            pingOutput[ospf88]['percent'] = line[3]
            (pingOutput[ospf88]['RTTmin'],pingOutput[ospf88]['RTTavg'],pingOutput[ospf88]['RTTmax']) = line[9].split('/')

            # iterate over the consist list to see what assets 
            # our peers are on            
            for assetNum in consist:
                if ospf88 in consist[assetNum]['SW0']:
                    pingOutput[ospf88]['asset'] = str(assetNum)
                    break
                elif ospf88 in consist[assetNum]['SW1']:
                    pingOutput[ospf88]['asset'] = str(assetNum)
                    break
                    
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
                csvoutput.writerow([currentTime,sourceAsset,sourceAddr,dictLoop["asset"],peerIP,repetitions,packetSize,dictLoop["percent"],dictLoop["RTTmin"],dictLoop["RTTavg"],dictLoop["RTTmax"]])
        # sanely close the file handler
        csvfile.close()

# these are the systems we're going to test
testFile = csv.DictReader(open("pingTesterTests.csv"))

# initialize the test dictionary
tests = {}

# run through the CSV and push the test setup into the test dictionary
for row in testFile:
    tests[row['sourceAsset']] = {}
    tests[row['sourceAsset']]['SW0'] = row['SW0']
    tests[row['sourceAsset']]['SW1'] = row['SW1']
    tests[row['sourceAsset']]['repeat'] = row['repeat']
    tests[row['sourceAsset']]['size'] = row['size']

# this is the consist switch layout
# we use it to figure out what assets our peers are part of
consistFile = csv.DictReader(open("consistList.csv"))

# initialize the consist dictionary
consist = {}

# run through the CSV and push the consist data into the dictionary
for row in consistFile:
    consist[row['sourceAsset']] = {}
    consist[row['sourceAsset']]['SW0'] = row['SW0']
    consist[row['sourceAsset']]['SW1'] = row['SW1']

try:
    # we use this as the CSV filename for output
    currentDateTime = str((datetime.date(datetime.now())))

    for asset, assetData in tests.items():
        # we make sure we can ping the switch before we do anything else
        #if check_ping(assetData['SW0']):
        #    print "ping " + assetData['SW0']
        #    ie4kPing(asset,assetData['SW0'],assetData['repeat'],assetData['size'],currentDateTime)
        #else:
        #    print "no ping " + assetData['SW0']
        if check_ping(assetData['SW1']):
            print "ping " + assetData['SW1']
            ie4kPing(asset,assetData['SW1'],assetData['repeat'],assetData['size'],currentDateTime)
        else:
            print "no ping " + assetData['SW1']
except IndexError:
    pass