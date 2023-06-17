#!/usr/bin/env python3

import argparse
import os
import json
import base64
from string import Template

parser=argparse.ArgumentParser(description="Create configuration management packages for the Toradex Labs Simple Configuration Manager")
parser.add_argument(
	"--add", 
	nargs=2, 
	action="append",
	metavar=("destination_path","config_file"),
	help="Adds a file to the config management package. <destination_path> is the \
	fully-qualified location on the device of the file that will be managed. \
	<config_file> is the file you want to put there. May be specified multiple times."
	)
parser.add_argument(
	"--delete", 
	action="append", 
	metavar="destination_path",
	help="Adds a file to the configuration package that should be deleted. May be specified multiple times."
	)
parser.add_argument(
	"output_file",
	help="The name of the package to be written. This is the file you can upload to the Torizon platform."
	)

args = parser.parse_args()

def build_config_package():
	firmware_dict = {}
	if args.add is not None:
		for file in args.add:
			device_path = file[0]
			local_path = file[1]
			firmware_dict[device_path] = {}
			file_bytes = open(local_path,"rb").read()
			if os.path.exists(local_path):
				firmware_dict[device_path]['content'] = base64.b64encode(file_bytes).decode()
				firmware_dict[device_path]['exists'] = True
				# check for template strings (i.e. ${variable} in the content of the file)
				if Template(file_bytes.decode()).get_identifiers():
					print(Template(file_bytes.decode()).get_identifiers())
					firmware_dict[device_path]['variables'] = Template(file_bytes.decode()).get_identifiers()
			else:
				print("Error: local file " + local_path + "does not exist.")
	if args.delete is not None:
		for file in args.delete:
			device_path = file
			firmware_dict[device_path] = {}
			firmware_dict[device_path]['exists'] = False
	fw_string = dumps_json_canonical(firmware_dict)
	with open(args.output_file,"w") as f:
		f.write(fw_string)

def dumps_json_canonical(mydict):
	return json.dumps(mydict,separators=(',',':'),sort_keys=True,ensure_ascii=False,allow_nan=False)

build_config_package()
