# ace-hunter

`ace-hunter` is primarily a command line tool for performing hunt validation in ACE environments. It's derived directly from the ACE Hunting System and can serve has a drop in replacement with some small changes to the ACE Hunting System.

Splunk hunts are the only hunts currently supported.


## Install

```
pip install ace_hunter
``` 

You could also git clone this repo and `python3 setup.py install` inside whatever python environment you wish. *NOTE*: I've only tested this in python3.9 but it should work for python>=3.6.


## CLI Tool

A tool called `hunt` is made available on the command line after install. For legacy reasons the tool can also be found under `ace-hunt`.

```console
$ hunt -h
usage: hunt [-h] [-d] {list-types,lt,list,l,verify,v,execute,e,config-query,cq,configure,c} ...

A hunting tool for ACE ecosystems.

positional arguments:
  {list-types,lt,list,l,verify,v,execute,e,config-query,cq,configure,c}
    list-types (lt)     List the types of Hunts configured.
    list (l)            List the available hunts. The format of the output is E|D type:name - description E: enabled D: disabled
    verify (v)          Verifies that all configured hunts are able to load.
    execute (e)         Execute a hunt with the given parameters.
    config-query (cq)   Query the Hunter configuration.
    configure (c)       Configure Hunter requirements.

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           Turn on debug logging.
```

## Configure

You will need to configure ace-hunter to work with your Splunk environment, your splunk hunt rules, and optionally your ACE environment.

Configuration items can be overridden on a system and user level. Config items take the following precedence, where items found later override earlier ones:

1. Built in defaults.
2. ACE settings at `/opt/ace/etc/saq.hunting.ini`.
3. System level settings at `/etc/ace/hunting.ini`.
4. User level settings at `~/.config/ace/hunting.ini`.
5. Special Environment Variables

Most of the `ace-hunter` configuration flexibility is so it may be dropped directly into ACE or for later convenience as much lighter ace-hunting docker container.


### Basic CLI Hunting Configuration

Below is an example of the minimum requirements for Splunk hunting with `ace-hunter`.

```
[splunk]
; ex. uri = https://your.splunk.address
uri = 
; timezone of your splunk server. ex: US/Eastern
timezone = 
username = 
password = 
; Can supply path to CA cert, yes for using system certs, no to turn off.
ssl_verification =
 
[SSL]
; SSL section is for submitting results to ACE.
; The ca_chain_path will be attempted if supplied.
; Next, systems certs used unless verify_ssl set to False.
verify_ssl = 
ca_chain_path = 
 
[hunt_type_splunk]
; Optionally specify the base location all rule directories
; will be relative to.
; Example showing that current user references will be expanded:
;detection_dir = ~/detections
; This is for convenience. SAQ_HOME or other settings can also be used.
detection_dir = /Users/sean/detections/
; Comma sep list pointing to your different splunk rule dirs.
rule_dirs = hunts/splunk/hippo,hunts/splunk/cat
```

### Easy User Level Configuration

You can easily override whatever config settings you need with the `hunt configure` API.

Ex: save your rules directories:

```console
➜ hunt configure hunt_type_splunk.rule_dirs -v 'hunts/splunk/hippo,hunts/splunk/cat' 
2022-02-04 14:49:23 MacBook-Pro ace_hunter.config[1141] INFO saving passed value to hunt_type_splunk.rule_dirs to /Users/sean/.config/ace/hunting.ini
2022-02-04 14:49:23 MacBook-Pro ace_hunter.config[1141] INFO saved configuration to: /Users/sean/.config/ace/hunting.ini
```

Ex: save your password:

```console
➜ hunt configure splunk.password
Enter value for splunk.password: 
2022-02-04 14:50:56 MacBook-Pro ace_hunter.config[1565] INFO saving passed value to splunk.password to /Users/sean/.config/ace/hunting.ini
2022-02-04 14:50:56 MacBook-Pro ace_hunter.config[1565] INFO saved configuration to: /Users/sean/.config/ace/hunting.ini
```

If the `hunt` tool creates or edits the user level config at `~/.config/ace/hunting.ini` the file will be made RW for the current user only.


## TODO

  -  [ ] Allow proxy settings to be configurable for flexibility. Use use environment variables as needed for now.