# ArchSDN Central Manager

[![CircleCI](https://circleci.com/gh/ClaymorePT/ArchSDN-Central-Manager.svg?style=svg)](https://circleci.com/gh/ClaymorePT/ArchSDN-Central-Manager)

### Introduction

This is the source code for the ArchSDN Central Manager.

The ArchSDN Central Manager is the central registry for the ArchSDN control network architecture.

It is used by the ArchSDN controllers to register themselves and to register the network clients which requested IP address using DHCP requests.

### Requirements
* Minimum Python 3.6 is required.
* Required Python modules (installed automatically when installing this program).
    * pyzmq==17.0.0
    * netaddr==0.7.19
    * networkx==2.1
    * blosc==1.5.1


### Installation procedure
Inside the folder to where the repository was cloned, simply execute: `$ pip install .`

The name of the package is `archsdn_central`

### Usage
When installed, the ArchSDN Central Manager can be executed by calling the executable in the terminal.

Example: `$ archsdn_central -l INFO`


#### ArchSDN options
    $ archsdn_central -h
    usage: archsdn_central [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-i IP]
                           [-p PORT] [-s STORAGE] [-4net IPV4NETWORK]
                           [-6net IPV6NETWORK]

    optional arguments:
      -h, --help            show this help message and exit
      -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --logLevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                            Logging Level (default: INFO)
      -i IP, --ip IP        Central Server interface IP to bind (default: 0.0.0.0)
      -p PORT, --port PORT  Central Server Port (default: 12345)
      -s STORAGE, --storage STORAGE
                            SQLite3 Database Location (default: ./:memory:)
      -4net IPV4NETWORK, --ipv4network IPV4NETWORK
                            IPv4 Network for Hosts (default: ./10.0.0.0/8)
      -6net IPV6NETWORK, --ipv6network IPV6NETWORK
                            IPv6 Network for Hosts (default (archsdn in hex):
                            ./fd61:7263:6873:646e::0/64)


| Flag   | Type        | Details | Example |
| ------ | ----------- | ------- | ------- |
| `-l --logLevel`| ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | Set the log Level. | `$ archsdn_central -l DEBUG` |
| `-i --ip`| string (IPv4 Address) | Network interface address in which the program will listen for requests. | `$ archsdn_central -i 192.168.123.1` |
| `-p --port` | int [1:65535] | Port to which the program will bind to. | `$ archsdn_central -p 12345` |
| `-s --storage` | string (Path) | Location where the database file will be stored. | `$ archsdn_central -s ./storage.db` |
| `-4net --ipv4network` | string (IPv4 Network Address) | IPv4 Network Address Pool with network mask from which addresses will be served. | `$ archsdn_central -4net 192.168.0.0:24` |
| `-6net --ipv6network` | string (IPv6 Network Address) | IPv6 Network Address Pool with network mask from which addresses will be served. | `$ archsdn_central -6net fd61:7263:6873:646e::0/64` |



### Warning
   
   The ArchSDN Central Manager __**needs to be executing**__ for the ArchSDN controllers to work properly.

   First, start the ArchSDN Central Manager service, then start the ArchSDN controllers.

   ArchSDN Controllers will only serve OpenFlow Switch requests after connecting and register themselves successfully in an ArchSDN central manager.

   If the ArchSDN controller is processing OpenFlow messages comming from the Openflow Switches, there's a change that the ArchSDN controller was not able to connect to the ArchSDN central manager.

  





