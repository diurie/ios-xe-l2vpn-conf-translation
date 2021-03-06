# IOS-XE L2VPN Configuration Translation

The goal of this script is to convert L2VPN P2P/VFI configuration without pseudowire interfaces to L2VPN P2P/VFI configuration with pseudowire interfaces on IOS-XE devices.

It allows the introduction of pseudowire template via the `source template type pseudowire <PW-NAME>` command.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Jinja2 library needs to be installed

### Example

The code can take a full configuration of a device. It will filter out L2VPN P2P and VFI section.

For P2P:
```
l2vpn xconnect context <L2VPN_NAME>
 member <AC> service-instance <SI>
 member <PW-1> <VC-ID> encapsulation mpls group <L2VPN_GROUP_NAME>
 member <PW-2> <VC-ID> encapsulation mpls group <L2VPN_GROUP_NAME> priority <L2VPN_PRIORITY>
 redundancy predictive enabled
 redundancy delay 0 30 group <L2VPN_GROUP_NAME>
```

The output that will be generated is as below:
```
interface pseudowire<ID-1>
  source template type pseudowire PW-TEMPLATE
  neighbor <PW-1> <VC-ID>
interface pseudowire<ID-2>
  source template type pseudowire PW-TEMPLATE
  neighbor <PW-2> <VC-ID>
l2vpn xconnect context <L2VPN_NAME>
 member <AC> service-instance <SI>
 member pseudowire<ID-1> encapsulation mpls group <L2VPN_GROUP_NAME>
 member pseudowire<ID-2> encapsulation mpls group <L2VPN_GROUP_NAME> priority <L2VPN_PRIORITY>
 redundancy predictive enabled
 redundancy delay 0 30 group <L2VPN_GROUP_NAME>
```

For VFI in manual mode:
```
l2 vfi <VFI_NAME> manual
 vpn id <VPN_ID>
 bridge-domain <BD_ID>
 mtu <MTU>
 neighbor <PW-1> <VC-ID> encapsulation mpls
 neighbor <PW-2> <VC-ID> encapsulation mpls
 neighbor <PW-3> <VC-ID> encapsulation mpls
 <...>
```

The output that will be generated is as below:
```
interface pseudowire<ID-1>
  source template type pseudowire PW-TEMPLATE
  neighbor <PW-1> <VC-ID>
interface pseudowire<ID-2>
  source template type pseudowire PW-TEMPLATE
  neighbor <PW-2> <VC-ID>
<...>

bridge-domain <BD_ID>
 member vfi <VFI_NAME>

l2vpn vfi context <VFI_NAME>
 vpn id <VPN_ID>
 mtu <MTU>
 member pseudowire<ID-1>
 member pseudowire<ID-2>
 member pseudowire<ID-3>
 <...>
```

In the example above, it assumes that `source template type pseudiwire <PW-NAME>` exists like the example below. But it's not mandatory.
```
template type pseudowire PW-TEMPLATE
 encapsulation mpls
 control-word include
 load-balance flow ip src-dst-ip
 load-balance flow-label both
```

## Installation

Copy this repository to your local computer with `git clone`.

After that, you need to install the required packages in a virtual environment:
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Running the code

All devices configuration can be pushed in the "config" folder. The script:
* Will iterate on all devices configuration
* Will extract only `l2vpn xconnect context <L2VPN_NAME>` section and convert it
* Will extract only `l2 vfi <VFI_NAME> manual` section and convert it

A configuration example completly sanitized is available in the "config" folder.

When the devices configuration are placed in the "config" folder, just run the script as below:
```
python main.py
```