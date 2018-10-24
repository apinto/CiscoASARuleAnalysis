# CiscoASARuleAnalysis (asaACLanalysis.py)
Cisco ASA Firewall access list analysis tool 

Should you have a Cisco ASA Firewall with thousand of ACL lines accumulated over the years and you need a tool to help you to clean up useless rules, this scrip may help you.

Tasks that the scrip may perform (menu presented):

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

(10) - Check if rules already (from file) exists in the DB

