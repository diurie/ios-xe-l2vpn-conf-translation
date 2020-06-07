"""
Purpose: Convert IOS-XE L2VPN CLI configuration without pseudowire interfaces
to new L2VPN configuration with FAT-PW & pseudowire interfaces
"""


import re
import os
import jinja2


#pwdict = {}


def txtfilesonly(listdir):
    """Filter only .txt files in a directory.

    Args:
        Take a list of files.
    """
    files = []
    for file in listdir:
        if re.search(r".*.txt", file):
            files.append(file)
    return files


def openfile(pathtofile):
    """Open a file.

    """
    with open(pathtofile, encoding="utf-8") as file:
        content = file.readlines()
    content = [x.strip() for x in content]
    return content


def p2pparsing(config):
    """Parse running-config for L2VPN P2P configuration

    Args:
        A device configuration {config}
    Output:
        A dictionnary with all required information
    """
    pwdict = {}
    l2vpn_id = 0
    pseudowire_offset_id = 0

    for line in config:
        # If the line is a starting point for P2P Configuration
        if re.search("l2vpn xconnect", line):
            # Increase of L2VPN ID
            l2vpn_id += 1
            # Reset the number of remote PW to 1
            nb_pw = 1
            # Increase the pseudowire offset
            pseudowire_offset_id += 1
            # Create new pwdict inside the Main dictionary with empty values
            pwdict[l2vpn_id - 1] = {
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
            pwdict[l2vpn_id - 1]["l2vpnContextName"] = re.search(
                r"context.*", line
            ).group(0)[8:]
        elif re.search(r"member.(Gig|Ten|Port)", line):
            # For each line that contains "member":
            # -> To identify the local AC, look for the pattern:
            # "member Gigabit|TenGigabit"
            # "member Port-channel"
            # -> Look for the service instance number at the end of the line
            # which is a number
            pwdict[l2vpn_id - 1]["l2vpnAC"] = re.search(r"(G|T|P).*ser", line).group(0)[:-4]
            pwdict[l2vpn_id - 1]["serviceInstance"] = re.search(r"(\d+)$", line).group(0)
        elif re.search(r"member.(\d+).(\d+).(\d+).(\d+)", line):
            # For each line that contains "member" and an IP address:
            # -> Look for the IP address in this line
            # -> Look for the VC-ID in this line
            # -> Look for the redundancy-group name in this line
            # -> Look for the priority-number in this line
            pwdict[l2vpn_id - 1]["vcId"] = re.findall(r"(\d+)", line)[4]

            if re.search("group", line):
                pwdict[l2vpn_id - 1]["redundancyGroupName"] = re.findall(r"(\w+)", line)[9]
                if re.search("priority", line):
                    pwdict[l2vpn_id - 1]["priorityNumber"] = re.findall(r"(\w+)", line)[-1]
                else:
                    del pwdict[l2vpn_id - 1]["priorityNumber"]
            else:
                del pwdict[l2vpn_id - 1]["redundancyGroupName"]
                del pwdict[l2vpn_id - 1]["priorityNumber"]

            # Create as many remote neighbor as needed
            pw_member = re.search(r"(\d+).(\d+).(\d+).(\d+)", line).group(0)
            if nb_pw == 1:
                pwdict[l2vpn_id - 1]["pwMember"].append(pw_member)
                pwdict[l2vpn_id - 1]["pseudowireID"].append(pseudowire_offset_id)
            else:
                pwdict[l2vpn_id - 1]["pwMember"].append(pw_member)
                pwdict[l2vpn_id - 1]["pseudowireID"].append(pseudowire_offset_id + 1000)
            # Increase the number of Remote Neighbor
            nb_pw += 1

    return pwdict


def vfiexists(config):
    """Parse running-config to confirm if VFI exists

    Args:
        A device configuration {config}
    """
    nb_vfi = 0
    for line in config:
        # If the line is a starting point for VFI Configuration
        if re.search("l2 vfi", line):
            nb_vfi += 1

    return bool(nb_vfi)


def vfiparsing(config, key):
    """Parse running-config for L2VPN VFI configuration

    Args:
        A device configuration {config}
        The last key used in the previous dictionnary {key}
    Output:
        A dictionnary with all required information
    """
    pwdict = {}
    l2vpn_id = key
    vfi_offset_id = 49900

    for line in config:
        # If the line is a starting point for VFI Configuration
        if re.search("l2 vfi", line):
            # Increase of L2VPN ID
            l2vpn_id += 1
            # Increase the pseudowire offset
            vfi_offset_id += 100
            vfi_offset_id = vfi_offset_id - abs(vfi_offset_id) % 100
            # Create new dictionnary inside the Main dictionary with empty values
            pwdict[l2vpn_id - 1] = {
                "l2vpnVfiName": "",
                "vpnId": "",
                "bridgeDomain": "",
                "mtu": "",
                "pwMember": [],
                "vcId": [],
                "vfiOffsetId": [],
                "templateJinja": "vfitemplate.j2",
            }
            pwdict[l2vpn_id - 1]["l2vpnVfiName"] = re.search(r"vfi.*", line).group(0)[4:-7]
        elif re.search(r"vpn id", line) and re.search(r"vfi.*", prev_line):
            # Catch the VPN-ID of the VFI
            pwdict[l2vpn_id - 1]["vpnId"] = re.search(r"(\d+)", line).group(0)
        elif re.search(r"bridge-domain", line) and re.search(r"vpn id", prev_line):
            # Catch the BD-ID of the VFI
            pwdict[l2vpn_id - 1]["bridgeDomain"] = re.search(r"(\d+)", line).group(0)
        elif re.search(r"mtu", line) and re.search(r"bridge-domain", prev_line):
            # Catch the MTU of the VFI
            pwdict[l2vpn_id - 1]["mtu"] = re.search(r"(\d+)", line).group(0)
        elif re.search(r"neighbor.*encapsulation mpls", line):
            # Catch all remote neighbors of the VFI
            vfi_offset_id += 1
            pwdict[l2vpn_id - 1]["pwMember"].append(
                re.search(r"(\d+).(\d+).(\d+).(\d+)", line).group(0)
            )
            pwdict[l2vpn_id - 1]["vfiOffsetId"].append(vfi_offset_id)

            if len(re.findall(r"(\d+)", line)) < 5:
                # The below if statement is to catch somehow a parser error
                # in the configuration that allow to configure a neighbor
                # without a VC-ID like below:
                # neighbor 1.2.3.4 encapsulation mpls
                pwdict[l2vpn_id - 1]["vcId"].append("No VC-ID Configured")
            else:
                pwdict[l2vpn_id - 1]["vcId"].append(re.findall(r"(\d+)", line)[4])

        prev_line = line
    return pwdict


def createnewconfig(pwdict, filename):
    """Create new configuration with Jinja2 Template

    Args:
        Actual configuration in a dictionnary {pwdict}
        The filename {filename}
    Output:
        Create a new file with the new configuration
    """
    for info in pwdict.values():
        with open(f"templates/{info['templateJinja']}") as file:
            tfile = file.read()
        template = jinja2.Template(tfile)
        template_output = template.render(info)
        with open(f"config/L2VPN-NEW_{filename}", "a+") as outfile:
            outfile.write(template_output)
        outfile.close()
    print(f"Treatment done, file created is FAT-PW_{filename}")


def main():
    """Main

    """
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
