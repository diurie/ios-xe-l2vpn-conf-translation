"""
Purpose: Convert IOS-XE L2VPN CLI configuration without pseudowire interfaces
to new L2VPN configuration with FAT-PW & pseudowire interfaces
"""


import re
import os
import jinja2


files = []
pwdict = {}


def txtfilesonly(listdir):
    for file in listdir:
        if re.search(r".*.txt", file):
            files.append(file)
    return files


def openfile(pathtofile):
    with open(pathtofile, encoding="utf-8") as file:
        content = file.readlines()
    content = [x.strip() for x in content]
    return content


def p2pparsing(config):
    # Input : A device configuration to work with {config}
    # Output : A Dictionnary with all required information
    l2vpnID = 0
    pseudowireOffsetId = 0

    for line in config:
        # If the line is a starting point for P2P Configuration
        if re.search("l2vpn xconnect", line):
            # Increase of L2VPN ID
            l2vpnID += 1
            # Reset the number of remote PW to 1
            nbPw = 1
            # Increase the pseudowire offset
            pseudowireOffsetId += 1

            # Create new pwdict inside the Main dictionary with empty values
            pwdict[l2vpnID - 1] = {
                "l2vpnContextName": "",
                "l2vpnAC": "",
                "serviceInstance": "",
                "vcId": "",
                "redundancyGroupName": "",
                "priorityNumber": "",
                "pwMember": [],
                "pseudowireID": [],
                "templateJinja": "p2ptemplate.j2",
            }
            pwdict[l2vpnID - 1]["l2vpnContextName"] = re.search(
                r"context.*", line
            ).group(0)[8:]
        elif re.search(r"member.(Gig|Ten|Port)", line):
            """
            For each line that contains "member":
                - Look for the pattern "member Gigabit|TenGigabit" and "member Port-channel" to identify the local AC
                - Look for the service instance number at the end of the line, which is a number
            """
            pwdict[l2vpnID - 1]["l2vpnAC"] = re.search(r"(G|T|P).*ser", line).group(0)[:-4]
            pwdict[l2vpnID - 1]["serviceInstance"] = re.search(r"(\d+)$", line).group(0)
        elif re.search(r"member.(\d+).(\d+).(\d+).(\d+)", line):
            """
            For each line that contains "member" and an IP address:
                - Look for the IP address in this line
                - Look for the VC-ID in this line
                - Look for the redundancy-group name in this line
                - Look for the priority-number in this line
            """
            pwdict[l2vpnID - 1]["vcId"] = re.findall(r"(\d+)", line)[4]

            if re.search("group", line):
                pwdict[l2vpnID - 1]["redundancyGroupName"] = re.findall(r"(\w+)", line)[9]
                if re.search("priority", line):
                    pwdict[l2vpnID - 1]["priorityNumber"] = re.findall(r"(\w+)", line)[-1]
                else:
                    del pwdict[l2vpnID - 1]["priorityNumber"]
            else:
                del pwdict[l2vpnID - 1]["redundancyGroupName"]
                del pwdict[l2vpnID - 1]["priorityNumber"]

            # Create as many remote neighbor as needed
            pwMember = re.search(r"(\d+).(\d+).(\d+).(\d+)", line).group(0)
            if nbPw == 1:
                pwdict[l2vpnID - 1]["pwMember"].append(pwMember)
                pwdict[l2vpnID - 1]["pseudowireID"].append(pseudowireOffsetId)
            else:
                pwdict[l2vpnID - 1]["pwMember"].append(pwMember)
                pwdict[l2vpnID - 1]["pseudowireID"].append(pseudowireOffsetId + 1000)
            # Increase the number of Remote Neighbor
            nbPw += 1

    return pwdict


def vfiexists(config):
    for line in config:
        # If the line is a starting point for VFI Configuration
        if re.search("l2 vfi", line):
            return True


def vfiparsing(config, key):
    # Input : A device configuration to work with {config}
    # Input : The last key used in the previous dictionnary {key}
    # Output : A Dictionnary with all required information
    l2vpnID = key
    vfiOffsetId = 49900

    for line in config:
        # If the line is a starting point for VFI Configuration
        if re.search("l2 vfi", line):
            # Increase of L2VPN ID
            l2vpnID += 1
            # Increase the pseudowire offset
            vfiOffsetId += 100
            vfiOffsetId = vfiOffsetId - abs(vfiOffsetId) % 100

            # Create new dictionnary inside the Main dictionary with empty values
            pwdict[l2vpnID - 1] = {
                "l2vpnVfiName": "",
                "vpnId": "",
                "bridgeDomain": "",
                "mtu": "",
                "pwMember": [],
                "vcId": [],
                "vfiOffsetId": [],
                "templateJinja": "vfitemplate.j2",
            }
            pwdict[l2vpnID - 1]["l2vpnVfiName"] = re.search(r"vfi.*", line).group(0)[4:-7]
        elif re.search(r"vpn id", line) and re.search(r"vfi.*", prevLine):
            # Catch the VPN-ID of the VFI
            pwdict[l2vpnID - 1]["vpnId"] = re.search(r"(\d+)", line).group(0)
        elif re.search(r"bridge-domain", line) and re.search(r"vpn id", prevLine):
            # Catch the BD-ID of the VFI
            pwdict[l2vpnID - 1]["bridgeDomain"] = re.search(r"(\d+)", line).group(0)
        elif re.search(r"mtu", line) and re.search(r"bridge-domain", prevLine):
            # Catch the MTU of the VFI
            pwdict[l2vpnID - 1]["mtu"] = re.search(r"(\d+)", line).group(0)
        elif re.search(r"neighbor.*encapsulation mpls", line):
            # Catch all remote neighbors of the VFI
            vfiOffsetId += 1
            pwdict[l2vpnID - 1]["pwMember"].append(
                re.search(r"(\d+).(\d+).(\d+).(\d+)", line).group(0)
            )
            pwdict[l2vpnID - 1]["vfiOffsetId"].append(vfiOffsetId)

            if len(re.findall(r"(\d+)", line)) < 5:
                """
                The below if statement is to catch somehow a parser error in the configuration
                that allow to configure a neighbor without a VC-ID like below:
                neighbor 1.2.3.4 encapsulation mpls
                """
                pwdict[l2vpnID - 1]["vcId"].append("No VC-ID Configured")
            else:
                pwdict[l2vpnID - 1]["vcId"].append(re.findall(r"(\d+)", line)[4])

        prevLine = line
    return pwdict


def createnewconfig(pwdict, filename):
    # Input : A dictionnary to work with {pwdict}
    # Input : The name of the file {filename}
    # Output : new L2VPN Configuration via Jinja2 Template
    for info in pwdict.values():
        with open(f"templates/{info['templateJinja']}") as file:
            tfile = file.read()
        template = jinja2.Template(tfile)
        templateOutput = template.render(info)
        with open(f"config/L2VPN-NEW_{filename}", "a+") as outfile:
            outfile.write(templateOutput)
        outfile.close()
    print(f"Treatment done, file created is FAT-PW_{filename}")


def main():
    entries = os.listdir("config/")
    files = txtfilesonly(entries)
    for filename in files:
        print(f"Working on : {filename}")
        content = openfile(f"config/{filename}")

        # Parse P2P xconnect configuration
        pwdict = p2pparsing(content)
        # Parse VFI configuration if exists
        if vfiexists(content):
            # Retrieve the last key used in previous parsing
            lastkey = list(pwdict.keys())[-1]
            pwdict.update(vfiparsing(content, lastkey))

        createnewconfig(pwdict, filename)
        pwdict.clear()


if __name__ == "__main__":
    main()
