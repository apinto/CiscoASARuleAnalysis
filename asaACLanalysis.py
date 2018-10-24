#!/usr/bin/env python

# Author: Artur Pinto (arturj.ppinto@gmail.com)


import ipcal
import mysql.connector as MS
import datetime
import progressbar
import time
import os
import sys
import getpass
from Exscript.protocols import SSH2
from Exscript import Account
import io


def get_login():
    '''prompts user for accout data and returns accout object'''
    user = raw_input('Please enter your username: ')
    password = getpass.getpass('Please enter your password: ')
    password2 = getpass.getpass('Please enter enable password: ')
    return Account(user, password, password2)

def sshdevice(account,device,cmdlist,fileprefix):
    conn = SSH2()
    conn.connect(device)
    conn.login(account)
    out = ''
    bar = progressbar.ProgressBar(max_value=4)
    i = 0
    for cmd in cmdlist:
        conn.execute(cmd)
        out = conn.response
        if cmd == 'show access-list':
            logfile = fileprefix+'acl_original.txt'
            log = io.open(logfile, 'w', encoding='utf8')
            log.write(out)
            log.close()
        elif cmd == 'show route':
            logfile = fileprefix+'routing.txt'
            log = io.open(logfile, 'w', encoding='utf8')
            log.write(out)
            log.close()
        elif cmd == 'show run access-group':
            logfile = fileprefix+'accessgroup.txt'
            log = io.open(logfile, 'w', encoding='utf8')
            log.write(out)
            log.close()    
        i = i + 1
        bar.update(i)
    conn.send('exit\r')
    conn.close()
    bar.finish()

def fetchdatassh():
    '''fetch data via ssh'''
    deviceip = raw_input("Insert IP of the device: ")
    print
    typeofdata = raw_input("(1)- base data | (2) - acl to compare with db: ")
    print
    if typeofdata == '1':
        cmdlist = ['terminal pager 0','show access-list','show route','show run access-group']
        fileprefix = '1in_'
    elif typeofdata == '2':
        cmdlist = ['terminal pager 0','show access-list']
        fileprefix = '2in_'
    else:
        print('Invalid Option')
        sys.exit()
    print "ACCOUNT TO BE USED: "
    account = get_login()
    print
    sshdevice(account,deviceip,cmdlist,fileprefix)
    print('WARNING: '+fileprefix+'* Files should be cleaned manually')
    print('delete lines: with the used cli cmd, empty, with banners, first ACL entries regarding cached elements, etc...')


def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1


def rulesStat(filein,fileout):
    '''Generates statistics about ACLs'''
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n') 
    fileacl = open(filein,'r')
    totalNumLines = 0
    #Number of ACL lines excluding lines representing remarks, info about elements and summarized rules with objects
    totalNumElements = 0
    #Number of Sumarized rules with object, as observed in the ASDM
    totalNumSumRules = 0
    #Number of sumarized rules without hits ie hitcnt=0
    totalRulesWOhits = 0
    #Number of sumarized rules with hits ie hitcnt!=0
    totalRulesWhits = 0
    #Number of elements without hits ie hitcnt=0
    totalElementsWOhits = 0
    #Number of elements with hits ie hitcnt!=0
    totalElementsWhits = 0
    print('Generating Statistics\n')
    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0
    for line in fileacl:
        totalNumLines = totalNumLines + 1
        if line[0] == 'a':
            if 'remark' not in line and 'elements' not in line:
                totalNumSumRules = totalNumSumRules + 1
                if '(hitcnt=0)' in line:
                    totalRulesWOhits=totalRulesWOhits + 1
                else:
                    totalRulesWhits=totalRulesWhits + 1
        elif line[0] == ' ':
            totalNumElements = totalNumElements + 1
            if '(hitcnt=0)' in line:
                totalElementsWOhits = totalElementsWOhits + 1
            else:
                totalElementsWhits = totalElementsWhits + 1
        i = i + 1
        #time.sleep(0.1)
        bar.update(i)
    now = datetime.datetime.now()
    filestat = open(fileout, 'a')
    filestat.write('############  FW RULES STATISTICS '+str(now)+' ##############\n')
    filestat.write('The total number of ACL lines is {}\n'.format(totalNumLines))
    filestat.write('\n')
    filestat.write('The total number of ACL elements is {}\n'.format(totalNumElements))
    filestat.write('The total number of ACL elements without hits is {}\n'.format(totalElementsWOhits))
    filestat.write('The total number of ACL elements with hits is {}\n'.format(totalElementsWhits))
    filestat.write('\n')
    filestat.write('The total number of ACL summarized rules is {}\n'.format(totalNumSumRules))
    filestat.write('The total number of ACL summarized rules without hits is {}\n'.format(totalRulesWOhits))
    filestat.write('The total number of ACL summarized rules with hits is {}\n'.format(totalRulesWhits))
    filestat.write('\n')
    filestat.write('\nNumber of ACL Elements per Interface:\n')
    fileacl.seek(0)
    for line in fileacl:
        if 'elements' in line:
            linelist = line.split()
            filestat.write(linelist[1]+' '+linelist[2]+'\n')   
    filestat.close()
    fileacl.close()
    bar.finish()


def sumrulesWOhits(filein,fileout):
    '''generates a file with all rules with hits = 0'''
    print('Generating file with ACL summary rules with hitcount=0\n')
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')
 
    fileacl = open(filein,'r')
    filerulestoclear = open(fileout,'w')

    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0
    for line in fileacl:
        if line[0] == 'a':
            if 'remark' not in line and 'elements' not in line:
                if '(hitcnt=0)' in line:
                    if 'remark' in previous:
                        filerulestoclear.write(previous)
                    filerulestoclear.write(line)
        previous = line
        i = i + 1
        #time.sleep(0.1)
        bar.update(i)
    fileacl.close()
    filerulestoclear.close()
    bar.finish()


def readrouting(filein):
    '''read routing table from file
    returns a dic with all routes where interface names are the keys'''
    print('Reading Routing Information from '+filein+'\n')
    filerouting = open(filein,'r')
    listofinterface = []
    routesdic = {}
    for line in filerouting:
        #for routes with LB ignore, we are not interested in the GW
        if line[0] != ' ':
            linelist = line.split()
            if linelist[6] not in listofinterface:
                listofinterface.append(linelist[6])
                routesdic[linelist[6]] = [linelist[1]+' '+linelist[2]]
            else:
                routesdic[linelist[6]].append(linelist[1]+' '+linelist[2])
    filerouting.close()
    return routesdic


def readaccessgroup(filein):
   '''read access-g table from file
   returns a dic with the association of interfaces with access-list'''
   print('Reading association between ACL and Interfaces from '+filein+'\n')
   fileaccessg = open(filein,'r')
   acldic = {}
   for line in fileaccessg:
       linelist = line.split()
       acldic[linelist[1]] = linelist[4]
   fileaccessg.close()
   return acldic


def wrongacl(dicroute,dicaccessg,filein,fileout):
    '''generates a file with wrong ACLs based on routing
    and ACL source ip or network'''
    print('Gerating file with wrong entries based on routing info\n')
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')

    fileacl = open(filein,'r')
    filewrongrules = open(fileout,'w')

    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0
    for line in fileacl:
        match = '0'
        if 'remark' not in line and 'elements' not in line and 'object' not in line:
        #if line[0] != 'a':
            linelist = line.split()
            if linelist[7] == 'host':
                address = linelist[8]
                netmask = '255.255.255.255'
            elif linelist[7] == 'any' or linelist[7] == 'any4':
                address = '0.0.0.0'
                netmask = '0.0.0.0'
            else:
                address = linelist[7]
                netmask = linelist[8]
            #print(address,netmask)
            netacl = ipcal.Network(address, netmask)
            #print('IP address: {0}'.format(netacl))
            aclname = linelist[1]
            #print(aclname)
            try:
                #there are ACLs not associated with interfaces (NAT,etc...)
                interface = dicaccessg[aclname]
                listofroutes = dicroute[interface]
                for route in listofroutes:
                    route = route.split()
                    netroute = ipcal.Network(route[0], route[1])
                    #print(netroute)
                    #print(netacl, netroute)
                    #print('{0} in network {1}: {2}'.format(netacl, netroute, netacl in netroute))
                    if netacl in netroute:
                        match = '1'
                #if netacl does not match any of the routes int the routing table
                if match == '0':
                    filewrongrules.write(line)

            except:
                pass
        i = i + 1 
        #time.sleep(0.1)
        bar.update(i)
    fileacl.close()
    filewrongrules.close()
    bar.finish()

def mysqlAction(description, sql, DB='none'):
    '''performs a mysql command in DB'''
    print(description)
    if DB == 'none':
        db1 = MS.connect(host=listauth[0],user=listauth[1],passwd=listauth[2])
    else:
        db1 = MS.connect(host=listauth[0],user=listauth[1],passwd=listauth[2], database=DB)
    cursor = db1.cursor()
    cursor.execute(sql)
    cursor.close()
    db1.close()


def populateTable(description, DB, table, filein):
    '''read data from table an insert in DB'''
    print(description)
    print('in file -> '+filein+'\n')

    db1 = MS.connect(host=listauth[0],user=listauth[1],passwd=listauth[2], database=DB)
    cursor = db1.cursor()

    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0
    filetable = open(filein, 'r')
    for line in filetable:
        linelist = line.split()
        if table == 'servicos':
            sql = "INSERT INTO servicos (name,protocol,portNumber) VALUES ('{}','{}','{}')".format(linelist[1],linelist[2],linelist[3])
        elif table == 'accesslist':
            sql = "INSERT INTO accesslist (name,linenum,action,protocol,LsrcIP,HsrcIP,LdstIP,HdstIP,Lport,Hport,Hcount)\
              VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(linelist[0],linelist[1],linelist[2],linelist[3],linelist[4],linelist[5],linelist[6],linelist[7],linelist[8],linelist[9],linelist[10])
        cursor.execute(sql)
        db1.commit()

        i = i + 1
        bar.update(i)
    cursor.close()
    db1.close()
    bar.finish()

def querydb(sql, DB):
    '''query db table and returns result'''

    db1 = MS.connect(host=listauth[0],user=listauth[1],passwd=listauth[2], database=DB)
    cursor = db1.cursor()

    cursor.execute(sql)

    results = cursor.fetchall()
    cursor.close()
    db1.close()
    return(results)

def convertaclfile(filein,fileout):
    ''' parce ACL File and convert ips/networks to range of integers
    to be imported to DB, translate tcp/udp port names to range of ports'''
    print('Converting IPs and networks to ranges of integers and port names to port ranges\n')
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')

    fileaclin = open(filein,'r')
    fileaclout = open(fileout,'w')
    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0

    for line in fileaclin:
        #index for normal for most ACL entries
        protocolidx = 6
        srcidx = 7  
        dstidx = 9
        portidx = 11
        hitcountidx = 13
        #ignores sumarization rule because of named objects
        #ignores inactive line
        if 'remark' not in line and 'object' not in line  and 'inactive' not in line and 'elements' not in line:
            linelist = line.split()
            #converts src file
            if linelist[srcidx] == 'range':
                #offset indx by one
                srcidx = srcidx + 1
                dstidx = dstidx + 1
                portidx = portidx + 1
		hitcountidx = hitcountidx + 1
                #calculate srcIP range
                ip = linelist[srcidx]
                net = ipcal.IP(ip)
	        LsrcIPint = int(net)

                ip = linelist[srcidx+1]
                net = ipcal.IP(ip)
                HsrcIPint = int(net)
            elif linelist[srcidx] == 'host':
                ip = linelist[srcidx+1]
                net = ipcal.IP(ip)
                LsrcIPint = int(net)
                HsrcIPint = int(net)
            elif linelist[srcidx] == 'any' or linelist[srcidx] == 'any4':
                dstidx = dstidx - 1
                portidx = portidx - 1
                hitcountidx = hitcountidx - 1
                ip = '0.0.0.0'
                netmask = '0.0.0.0'
                net = ipcal.Network(ip,netmask)
                network = net.network()
                broadcast = net.broadcast()
                netip = ipcal.IP(network)
                broadip = ipcal.IP(broadcast)
                LsrcIPint = int(netip)
                HsrcIPint = int(broadip)
            else:
                ip = linelist[srcidx]
                netmask = linelist[srcidx+1]
                #print(ip,netmask)
               
                net = ipcal.Network(ip,netmask)
                network = net.network()
                broadcast = net.broadcast()
                netip = ipcal.IP(network)
                broadip = ipcal.IP(broadcast)
                LsrcIPint = int(netip)
                HsrcIPint = int(broadip)
            #converts dst fields	
            if linelist[dstidx] == 'range':
                #offset indx by one
                dstidx = dstidx + 1
                portidx = portidx + 1
                hitcountidx = hitcountidx + 1

                #calculate dstIP range
                ip = linelist[dstidx]
                net = ipcal.IP(ip)
                LdstIPint = int(net)
                
                ip = linelist[dstidx+1]
                net = ipcal.IP(ip)
                HdstIPint = int(net)
            elif linelist[dstidx] == 'any' or linelist[dstidx] == 'any4':
                dstidx = dstidx - 1
                portidx = portidx - 1
                hitcountidx = hitcountidx - 1
                ip = '0.0.0.0'
                netmask = '0.0.0.0'
                net = ipcal.Network(ip,netmask)
                network = net.network()
                broadcast = net.broadcast()
                netip = ipcal.IP(network)
                broadip = ipcal.IP(broadcast)
                LdstIPint = int(netip)
                HdstIPint = int(broadip)
            elif linelist[dstidx] == 'host':
                ip = linelist[dstidx+1]
                net = ipcal.IP(ip)
                LdstIPint = int(net)
                HdstIPint = int(net)
            else:
                ip = linelist[dstidx]
                netmask = linelist[dstidx+1]
                net = ipcal.Network(ip,netmask)
                network = net.network()
                broadcast = net.broadcast()
                netip = ipcal.IP(network)
                broadip = ipcal.IP(broadcast)
                LdstIPint = int(netip)
                HdstIPint = int(broadip)
            #translate ports	
            if linelist[protocolidx] == 'icmp':
                lowport = '0'
                highport = '0'
                hitcountidx = hitcountidx - 2
            elif linelist[protocolidx] == 'ip':
                lowport = '0'
                highport = '65535'
                hitcountidx = hitcountidx - 2
            else:
                if linelist[portidx] == 'range':
                    lowport = linelist[portidx+1]
                    highport = linelist[portidx+2]
                    hitcountidx = hitcountidx + 1
                elif linelist[portidx] == 'eq':
                    lowport = linelist[portidx+1]
                    highport = linelist[portidx+1]
                #tcp or udp with all ports
                else:
                    lowport = '0'
                    highport = '65535'
                    hitcountidx = hitcountidx - 2
                if not lowport.isdigit():
                    sql = "SELECT portNumber FROM servicos WHERE protocol='{}' and name='{}'".format(linelist[protocolidx],lowport)
                    lport = querydb(sql,'ASA')
                    lowport = lport[0][0]
                if not highport.isdigit():
                    sql = "SELECT portNumber FROM servicos WHERE protocol='{}' and name='{}'".format(linelist[protocolidx],highport)
                    hport = querydb(sql,'ASA')
                    highport = hport[0][0]			
	
            #removes (hitcnt= and )
            hitcount = linelist[hitcountidx]
            hitcount = hitcount.replace('(hitcnt=','')
            hitcount = hitcount.replace(')','')
	
            fileaclout.write(linelist[1]+' '+linelist[3]+' '+linelist[5]+' '+linelist[6]+' '+\
            str(LsrcIPint)+' '+str(HsrcIPint)+' '+str(LdstIPint)+' '+str(HdstIPint)+' '+str(lowport)+' '+str(highport)+' '+str(hitcount)+'\n')
        i = i + 1
        bar.update(i)
    fileaclin.close()
    fileaclout.close()
    bar.finish()


def detectOverlaping(filein,fileout):
    '''detect overlaping rules in the DB
    at this stage is not comparing ip with tcp or ip with UDP
    only dupps inside same protocol are detected'''
    print('Detecting Overlapping entries\n')
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')

    fileaclconverted = open(filein,'r')
    filedup = open(fileout,'w')
    filedup.write('ANALYSIS OF OVERLAPPING ENTRIES:\n')
    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0
    for line in fileaclconverted:
        linelist = line.split()
        #If protocol is ip then you dont need to look to protocol or ports
        if linelist[3] == 'ip':
            sql =  '''SELECT * FROM accesslist WHERE
name='{}' and action='{}' and LsrcIP>={} and HsrcIP<={} and LdstIP>={} and HdstIP<={}'''.format(linelist[0],linelist[2],linelist[4],linelist[5],linelist[6],linelist[7])
        else:
            sql =  '''SELECT * FROM accesslist WHERE
name='{}' and action='{}' and protocol='{}' and LsrcIP>={} and HsrcIP<={} and LdstIP>={} and HdstIP<={} and Lport>={} and Hport<={}'''.format(linelist[0],linelist[2],linelist[3],linelist[4],linelist[5],linelist[6],linelist[7],linelist[8],linelist[9])
        queryresult = querydb(sql,'ASA')
        if len(queryresult) > 1:
            filedup.write('\nACLName cliLineNumb action protocol LsrcIP HsrcIP LdstIP HdstIP LportNum HporNum Hitcounts\n')
            for lmember in queryresult:
                LsrcIP = str(ipcal.IP(lmember[5]))
                HsrcIP = str(ipcal.IP(lmember[6]))
                LdstIP = str(ipcal.IP(lmember[7]))
                HdstIP = str(ipcal.IP(lmember[8]))
                lineresult = str(lmember[1])+' '+str(lmember[2])+' '+str(lmember[3])+' '+str(lmember[4])+' '+LsrcIP+' '+HsrcIP+' '+LdstIP+' '+HdstIP+' '+str(lmember[9])+' '+str(lmember[10])+' '+str(lmember[11])+'\n'
                #print(lineresult)
                filedup.write(lineresult)
        i = i + 1
        #time.sleep(0.1)
        bar.update(i)
    filedup.close()
    fileaclconverted.close()
    bar.finish()

def inactiverules(filein,fileout):
    '''generates a file with all inactive rules
    format to delete in the firewall and'''
    print('Generating file with inactive rules to delete\n')
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')

    fileacl = open(filein,'r')
    fileinactiverules = open(fileout,'w')
    fileinactiverules.write('################ ALL LINES WITH INACTIVE #################\n\n')
    bar = progressbar.ProgressBar(max_value=2*file_len(filein))
    i = 0
    for line in fileacl:
        if 'inactive' in line:
            if 'remark' in  previous:
                fileinactiverules.write(previous)
            fileinactiverules.write(line)
        previous = line
        i = i + 1
        #time.sleep(0.1)
        bar.update(i)   
    fileacl.seek(0) 
    fileinactiverules.write('\n\n################ SUMMARY LINES WITH INACTIVE #################\n\n')
    for line in fileacl:
        if line[0] == 'a' and 'inactive' in line:
            if 'remark' in  previous:
                fileinactiverules.write(previous)
            fileinactiverules.write(line)
        previous = line
        i = i + 1
        #time.sleep(0.1)
        bar.update(i)
    fileacl.close()
    fileinactiverules.close()
    bar.finish()

def comparerules(filein,fileconverted,fileout):
    '''Compare rules from a file with database
    list rules in file and not in DB'''
    print('Compare rules from a file with database\n')

    #converts ip/subnets in int and port names to port numbers
    convertaclfile(filein,fileconverted)


    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')

    fileacl = open(fileconverted,'r')
    fileout = open(fileout,'w')
    bar = progressbar.ProgressBar(max_value=file_len(fileconverted))
    i = 0
    for line in fileacl:
        linelist = line.split()
        #print(linelist)
        sql =  '''SELECT * FROM accesslist WHERE
name='{}' and action='{}' and protocol='{}' and LsrcIP={} and HsrcIP={} and LdstIP={} and HdstIP={} and Lport={} and Hport={}'''.format(linelist[0],linelist[2],linelist[3],linelist[4],linelist[5],linelist[6],linelist[7],linelist[8],linelist[9])
        queryresult = querydb(sql,'ASA')
        if len(queryresult) == 0:
            for lmember in queryresult:
                LsrcIP = str(ipcal.IP(lmember[5]))
                HsrcIP = str(ipcal.IP(lmember[6]))
                LdstIP = str(ipcal.IP(lmember[7]))
                HdstIP = str(ipcal.IP(lmember[8]))
                lineresult = str(lmember[1])+' '+str(lmember[2])+' '+str(lmember[3])+' '+str(lmember[4])+' '+LsrcIP+' '+HsrcIP+' '+LdstIP+' '+HdstIP+' '+str(lmember[9])+' '+str(lmember[10])+' '+str(lmember[11])+'\n'
                #print(lineresult)
                fileout.write(lineresult)
        elif len(queryresult) >= 1:
            #print('rule match') 
            pass       
        i = i + 1
        #time.sleep(0.1)
        bar.update(i)
    fileacl.close()
    fileout.close()
    bar.finish()

def checkIfSingleRule():
    '''check if rule already exists or covered by a more generic rule'''
    print('when network convert with range of IPs\n')
    print('when host then LOWIP = HIGHIP\n\n')
     
    action = raw_input("'permit'/'deny' ->: ")
    if action != 'permit' and action !='deny':
        print('ERROR Action not valid')
        sys.exit()
    
    protocol = raw_input("'ip'/'icmp'/'tcp'/'udp' ->: ")
    
    lsrcip = raw_input("LOW SRC IP ->: ")
    hsrcip = raw_input("HIGH SRC IP ->: ") 
    ldstip = raw_input("LOW DST IP ->: ")
    hdstip = raw_input("HIGH DST IP ->: ")

    if protocol == 'tcp' or protocol=='udp':
        lport = raw_input("LOW PORT NUMBER ->: ")
        hport = raw_input("HIGH PORT NUMBER ->: ")
    elif protocol=='icmp':
        lport = 0
        hport = 0
    elif protocol=='ip':
        lport = 0
        hport = 65535
    else:
        print('ERROR Protocol not valid')
        sys.exit()

    #convert ips
    LsrcIP = int(ipcal.IP(lsrcip))
    HsrcIP = int(ipcal.IP(hsrcip))
    LdstIP = int(ipcal.IP(ldstip))
    HdstIP = int(ipcal.IP(hdstip))
    if linelist[3] == 'ip':
        sql =  '''SELECT * FROM accesslist WHERE
action='{}' and  and LsrcIP<={} and HsrcIP>={} and LdstIP<={} and HdstIP>={} and Lport<={} and Hport>={}'''.format(action,str(LsrcIP),str(HsrcIP),str(LdstIP),str(HdstIP),lport,hport)
    else:
        sql =  '''SELECT * FROM accesslist WHERE
action='{}' and protocol='{}' and LsrcIP<={} and HsrcIP>={} and LdstIP<={} and HdstIP>={} and Lport<={} and Hport>={}'''.format(action,protocol,str(LsrcIP),str(HsrcIP),str(LdstIP),str(HdstIP),lport,hport)

    queryresult = querydb(sql,'ASA')
    if len(queryresult) > 0:
        for lmember in queryresult:
            LsrcIP = str(ipcal.IP(lmember[5]))
            HsrcIP = str(ipcal.IP(lmember[6]))
            LdstIP = str(ipcal.IP(lmember[7]))
            HdstIP = str(ipcal.IP(lmember[8]))
            lineresult = str(lmember[1])+' '+str(lmember[2])+' '+str(lmember[3])+' '+str(lmember[4])+' '+LsrcIP+' '+HsrcIP+' '+LdstIP+' '+HdstIP+' '+str(lmember[9])+' '+str(lmember[10])+' '+str(lmember[11])+'\n'        
            print(lineresult)
   
    else:
        print('\nRule does not exists\n')

def checkIfRules(filein,fileout):
    '''check if rules already exists
    reads rule from file and ceck with DB'''
    
    print('in file -> '+filein+'\n')
    print('out file -> '+fileout+'\n')

    fileacl = open(filein, 'r')
    fileout = open(fileout,'w')
    bar = progressbar.ProgressBar(max_value=file_len(filein))
    i = 0
	
    for line in fileacl:
        linelist = line.split()
        action = linelist[4]
        protocol = linelist[5]
        lport = linelist[6]
        hport = linelist[7]		
		
        srcip = linelist[0]
        srcmask = linelist[1]
        net = ipcal.Network(srcip, srcmask)
        network = net.network()
        broadcast = net.broadcast()
        netip = ipcal.IP(network)
        broadip = ipcal.IP(broadcast)
        LsrcIP = int(netip)
        HsrcIP = int(broadip)

        dstip = linelist[2]
        dstmask = linelist[3]
        net = ipcal.Network(dstip, dstmask)
        network = net.network()
        broadcast = net.broadcast()
        netip = ipcal.IP(network)
        broadip = ipcal.IP(broadcast)
        LdstIP = int(netip)
        HdstIP = int(broadip)		

        if linelist[3] == 'ip':
            sql =  '''SELECT * FROM accesslist WHERE
action='{}' and  and LsrcIP<={} and HsrcIP>={} and LdstIP<={} and HdstIP>={} and Lport<={} and Hport>={}'''.format(action,str(LsrcIP),str(HsrcIP),str(LdstIP),str(HdstIP),lport,hport)
        else:
            sql =  '''SELECT * FROM accesslist WHERE
action='{}' and protocol='{}' and LsrcIP<={} and HsrcIP>={} and LdstIP<={} and HdstIP>={} and Lport<={} and Hport>={}'''.format(action,protocol,str(LsrcIP),str(HsrcIP),str(LdstIP),str(HdstIP),lport,hport)

        queryresult = querydb(sql,'ASA')
        if len(queryresult) > 0:
            fileout.write(line)
            for lmember in queryresult:
                LsrcIP = str(ipcal.IP(lmember[5]))
                HsrcIP = str(ipcal.IP(lmember[6]))
                LdstIP = str(ipcal.IP(lmember[7]))
                HdstIP = str(ipcal.IP(lmember[8]))
                lineresult = str(lmember[1])+' '+str(lmember[2])+' '+str(lmember[3])+' '+str(lmember[4])+' '+LsrcIP+' '+HsrcIP+' '+LdstIP+' '+HdstIP+' '+str(lmember[9])+' '+str(lmember[10])+' '+str(lmember[11])+'\n'        
                fileout.write(lineresult)
            fileout.write('\n')

        else:
            fileout.write(line+' Rule does not exists\n\n')
        i = i + 1
        bar.update(i)		
    fileacl.close()
    fileout.close()
    bar.finish()

def option1():
    '''Option1 from Menu'''
    print("\n Generate statistics file: \n")
    #creates statistics based on access-lists in file, ouput appended to a file
    rulesStat('1in_acl_original.txt','1out_acl_statistics.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option2():
    '''Option2 from Menu'''
    print("\n Generate file with inactive rules: \n")
    #creates file with inactive rules
    inactiverules('1in_acl_original.txt','1out_acls_inactive.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option3():
    '''Option3 from Menu'''
    print("\n Generate file with wrong rule elements: \n")
    #read routing
    dicroute = readrouting('1in_routing.txt')
    #read acl name and interface association
    dicaccessg = readaccessgroup('1in_accessgroup.txt')
    #creates file with acl elements not associated with correct interface
    wrongacl(dicroute,dicaccessg,'1in_acl_original.txt','1out_acl_wrong.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option4():
    '''Option4 from Menu'''
    print("\n Generate file with rules with hitcount=0: \n")
    #creates file with all summary rules without hitcounts
    sumrulesWOhits('1in_acl_original.txt','1out_aclrules_without_hits.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option5():
    '''Option5 from Menu'''
    print("\n Import file to DB: \n")
    #deletes and create db to start fresh
    sql = "DROP DATABASE ASA"
    description = 'Deleting DB ASA\n'
    mysqlAction(description, sql)
    sql = 'CREATE DATABASE IF NOT EXISTS ASA'
    description = 'Creating MariaDB for analysis of duplicated entries\n'
    mysqlAction(description, sql)
    #creates table servicos for translation of portnames to numbers
    description='Creating table servicos for analysis of duplicated entries\n'
    sql = '''CREATE TABLE IF NOT EXISTS servicos (
             lineid INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
             name VARCHAR(30) NOT NULL,
             protocol VARCHAR(30) NOT NULL,
             portNumber INT(6) NOT NULL
             )
             '''
    mysqlAction(description, sql, 'ASA')
    description='Populating table servicos for translation from port names to numbers\n'
    populateTable(description, 'ASA', 'servicos', 'in_servicos.txt')
    #converts ip/subnets in int and port names to port numbers
    convertaclfile('1in_acl_original.txt','1out_acl_coverted_ips.txt')
    description = 'Creating table ACL for analysis of duplicated entries\n'    
    sql = '''CREATE TABLE IF NOT EXISTS accesslist (
           lineid INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
           name VARCHAR(30) NOT NULL,
           linenum INT(6) NOT NULL,
           action VARCHAR(10) NOT NULL,
           protocol VARCHAR(30) NOT NULL,
           LsrcIP INT(30) UNSIGNED NOT NULL,
           HsrcIP INT(30) UNSIGNED NOT NULL,
           LdstIP INT(30) UNSIGNED NOT NULL,
           HdstIP INT(30) UNSIGNED NOT NULL,
           Lport INT(30) UNSIGNED NOT NULL,
           Hport INT(30) UNSIGNED NOT NULL,
           Hcount INT(30) UNSIGNED NOT NULL
           )
           '''
    mysqlAction(description, sql, 'ASA')
    description = 'populating table ACL for analysis of duplicated entries\n'
    populateTable(description, 'ASA', 'accesslist', '1out_acl_coverted_ips.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option6():
    '''Option6 from Menu'''
    print("\n Generate file with duplication analysis \n")
    #detect overlapping rule elements
    detectOverlaping('1out_acl_coverted_ips.txt','1out_acls_overlapping.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option7():
    '''Option7 from Menu'''
    print("\n Generate file with compare results \n")
    #check if all rules exist, does not consider order of rules
    comparerules('2in_acl_original.txt','2out_acl_coverted_ips.txt','21_out_diff_file_and_DB.txt')
    raw_input('\nPlease press ENTER to return to menu')

def option8():
    '''Option8 from Menu'''
    option1()
    option2()
    option3()
    option4()
    option5()
    option6()
    option7()

def option9():
    '''Option9 from Menu'''
    print("\n Check if rule already exists in DB: \n")
    #check if all rules exist, does not consider order of rules
    checkIfSingleRule()
    raw_input('\nPlease press ENTER to return to menu')

def option10():
    '''Option10 from Menu'''
    print("\n Check if rules (read from file) already exists in DB: \n")
    #check if all rules exist, does not consider order of rules
    checkIfRules('1in_check_open.txt', '1out_check_open.txt')
    raw_input('\nPlease press ENTER to return to menu')


def main():
    while '1':
        os.system('clear')
        print("###### CISCO ASA ACL ANALYSIS TOOL #######\n\n")
        
        print("(F) - Fetch data from device via ssh \n")
        print("(H) - HELP Info about required files with input data \n\n")

        print("(1) - Generate statistics file\n")
        print("(2) - Generate file with inactive rules\n")
        print("(3) - Generate file with wrong rule elements (based in routing)\n")
        print("(4) - Generate file with rules with hitcount=0 \n")
        print("(5) - Import file to DB (required for duplicated analysys and compare ACLs)\n")
        print("(6) - Generate file with duplication analysis\n")
        print("(7) - Generate file with compare results (checks if any rule was deleted, done between file and DB)\n")
        print("(8) - (1)+(2)+(3)+(4)+(5)+(6)+(7)\n")
        print("(9) - Check if single rule (interactive) already exists in the DB\n")
        print("(10) - Check if rules (from file) already exists in the DB\n\n")

        print("(E) - Exit\n\n\n")
        
        option = raw_input('SELECT OPTION ->:  ')
        if option == 'f' or option == 'F':
            print("\n Fetching Data from Device... \n")
            fetchdatassh()
            raw_input('\nPlease press ENTER to return to menu')           

        elif option == 'h' or option == 'H':
            print("\n in 'in_acl_original.txt' put the 'show access-list' data.\n")
            print("\n in '1in_routing.txt' put the 'show route' data.\n")
            print("\n in '1in_accessgroup.txt' put the 'show run access-group' data.\n")
            print("\n in 'in_servicos.txt' put the data required to translate port names.\n")
            print("\n in '1in_check_open.txt put data in the same format as example to check if accesses are opened according the DB.\n")
            print("\n in '2in_acl_original.txt' put the 'show access-list' data to be compared with DB.\n\n")
            raw_input('\nPlease press ENTER to return to menu')
	
        elif option == '1':
            option1()
        elif option == '2':
            option2()
        elif option == '3':
            option3()
        elif option == '4':
            option4()
        elif option == '5':
            option5()
        elif option == '6':
            option6()
        elif option == '7':
            option7()
        elif option == '8':
            option8()
        elif option == '9':
            option9()
        elif option == '10':
            option10()

        elif option == 'e' or option == 'E':
            sys.exit()
        else:
            print "\nERROR - Please select a valid option\n"


if __name__ == '__main__':
    #global variable with DB login data
    listauth = ["localhost","root","mai123!!"]
    main()
