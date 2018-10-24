# CiscoASARuleAnalysis (asaACLanalysis.py)
### Cisco ASA Firewall access list analysis tool 

Should you have a Cisco ASA Firewall with thousand of ACL lines accumulated over the years and you need a tool to help you to clean up useless rules, this scrip may help you.

## Tasks that the scrip can currently do for you (tools' menu):

(F) - Fetch data from device via ssh

(H) - HELP Info about required files with input data


(1) - Generate statistics file

(2) - Generate file with inactive rules

(3) - Generate file with wrong rule elements (based in routing)

(4) - Generate file with rules with hitcount=0

(5) - Import file to DB (required for duplicated analysys and compare ACLs)

(6) - Generate file with duplication analysis

(7) - Generate file with compare results (checks if any rule was deleted, done between file and DB)

(8) - (1)+(2)+(3)+(4)+(5)+(6)+(7)

(9) - Check if single rule (interactive) already exists in the DB

(10) - Check if rules (from file) already exists in the DB

#This Tool requires input data that may be fetched via ssh (manual clean up is required) or provided offline (see options F and H). 

## A Mysql DB or Maria DB is required 

This script has been written by a Network Engineer (not a programmer) and therefore most likely is not following all the best coding practices and lots of improvements can me made. 
All types of positive contributions and/or constructive comments are welcomed 
