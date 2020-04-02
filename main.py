"""
Purpose: Convert IOS-XE L2VPN CLI configuration without pseudowire interfaces
to new L2VPN configuration with FAT-PW & pseudowire interfaces
"""


import re
import os
import jinja2

files = []
jinjaTemplate = 'l2vpnTemplate.j2'
pwDict = {}


def txtfilesonly(listdir):
    for file in listdir:
        if re.search(r'.*.txt', file):
            files.append(file)
    return files


def openfile(pathtofile):
    with open(pathtofile) as file:
        content = file.readlines()
    content = [x.strip() for x in content]
    return content


def l2vpnparsing(config):
    """
    Parse the configuration and put the useful
    variable in a Dictionary
    """
    l2vpnID = 0
    pseudowireOffsetId1 = 0
    pseudowireOffsetId2 = 10000

    for line in config:
        if re.search('l2vpn xconnect', line):
            # Increase of L2VPN ID
            l2vpnID += 1

            # Reset the number of remote PW to 1
            nbPw = 1

            # Increase the pseudowire offset
            pseudowireOffsetId1 += 1
            pseudowireOffsetId2 += 1

            # Create new Dict inside the Main Dictionary with empty values
            pwDict[l2vpnID - 1] = {
                'l2vpnContextName': '',
                'l2vpnAC': '',
                'serviceInstance': '',
                'vcId': '',
                'redundancyGroupName': '',
                'priorityNumber': '',
                'pwMember': [],
                'pseudowireID': [],
            }
            pwDict[l2vpnID - 1]['l2vpnContextName'] = re.search(r'context.*', line).group(0)[8:]

        elif re.search(r'member.(Gig|Ten|Port)', line):
            """
            For each line that contains "member":
                - Look for the pattern "member Gigabit|TenGigabit" and "member Port-channel" to identify the local AC
                - Look for the service instance number at the end of the line, which is a number
            """
            pwDict[l2vpnID - 1]['l2vpnAC'] = re.search(r'(G|T|P).*ser', line).group(0)[:-4]
            pwDict[l2vpnID - 1]['serviceInstance'] = re.search(r'(\d+)$', line).group(0)

        elif re.search(r'member.(\d+).(\d+).(\d+).(\d+)', line):
            """
            For each line that contains "member" and an IP address:
                - Look for the IP address in this line
                - Look for the VC-ID in this line
                - Look for the redundancy-group name in this line
                - Look for the priority-number in this line
            """
            pwDict[l2vpnID - 1]['vcId'] = re.findall(r'(\d+)', line)[4]

            if re.search('group', line):
                pwDict[l2vpnID - 1]['redundancyGroupName'] = re.findall(r'(\w+)', line)[9]
                if re.search('priority', line):
                    pwDict[l2vpnID - 1]['priorityNumber'] = re.findall(r'(\w+)', line)[-1]
                else:
                    del pwDict[l2vpnID - 1]['priorityNumber']
            else:
                del pwDict[l2vpnID - 1]['redundancyGroupName']
                del pwDict[l2vpnID - 1]['priorityNumber']

            # Create as many remote neighbor as needed
            pwMember = re.search(r'(\d+).(\d+).(\d+).(\d+)', line).group(0)
            if nbPw == 1:
                pwDict[l2vpnID - 1]['pwMember'].append(pwMember)
                pwDict[l2vpnID - 1]['pseudowireID'].append(pseudowireOffsetId1)
            else:
                pwDict[l2vpnID - 1]['pwMember'].append(pwMember)
                pwDict[l2vpnID - 1]['pseudowireID'].append(pseudowireOffsetId2)
            # Increase the number of Remote Neighbor
            nbPw += 1
    return pwDict


def createnewconfig(dict, filename):
    """
    Take a dict in input and create new L2VPN Configuration
    via Jinja2 Template
    """
    for id, info in dict.items():
        with open(jinjaTemplate) as file:
            tfile = file.read()
        template = jinja2.Template(tfile)
        templateOutput = template.render(info)
        with open(f'config/FAT-PW_{filename}', 'a+') as outfile:
            outfile.write(templateOutput)
        outfile.close()
    print(f'Treatment done, file created is FAT-PW_{filename}')


def main():
    entries = os.listdir("config/")
    files = txtfilesonly(entries)

    for filename in files:
        print(f'Working on : {filename}')
        content = openfile(f'config/{filename}')
        pwDict = l2vpnparsing(content)
        createnewconfig(pwDict, filename)


if __name__ == '__main__':
    main()