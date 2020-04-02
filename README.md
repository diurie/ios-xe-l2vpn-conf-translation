# IOS-XE L2VPN Configuration Translation

The goal of this script is to convert L2VPN P2P configuration without pseudowire interfaces to L2VPN P2P configuration with pseudowire interfaces on IOS-XE devices.

It allows the introduction of pseudowire template via the `source template type pseudiwire <PW-NAME>` command.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Jinja2 library needs to be installed

### Example

The code can take a full configuration of a device. It will filter out only L2VPN P2P section like below:
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

In the example above, it assumes that `source template type pseudiwire <PW-NAME>` exists like the example below. But it's not mandatory.
```
template type pseudowire PW-TEMPLATE
 encapsulation mpls
 control-word include
 load-balance flow ip src-dst-ip
 load-balance flow-label both
```

## Running the code

All devices configuration can be pushed in the "config" folder. The script:
* Will iterate on all devices configuration
* Will extract only `l2vpn xconnec context <L2VPN_NAME>` section and convert it

A configuration example completly sanitized is available in the "config" folder.

## Installation

Copy this repository to your local computer with `git clone`.

After that, you need to install the required packages in a virtual environment:
```
python3 -m venv virtualenv
source virtualenv/bin/activate
pip3 install -r requirements.txt
```