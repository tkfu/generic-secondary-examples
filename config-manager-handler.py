#!/usr/bin/env python3

import argparse
import hashlib
import os
import json
import base64
from string import Template


parser=argparse.ArgumentParser()
parser.add_argument("action")
parser.add_argument("-b", "--baseconfig")
parser.add_argument("-o", "--outfile")


# you can set your base config here, or pass it in with an argument
baseconfig_string='''
{
    "/home/torizon/test.txt":
    {
        "exists": true,
        "content": "ZXhhbXBsZSAxCg=="
    }
}
'''
baseconfig=json.loads(baseconfig_string)

args = parser.parse_args()
if args.baseconfig is not None:
	with open(baseconfig,"r") as f:
		baseconfig = json.load(f)
action = args.action

def get_firmware_info():
	current_custom_meta = json.load(open(os.environ.get('SECONDARY_FIRMWARE_PATH'),'r')) # TODO use pathlib to get the real file
	current_custom_meta = {}
	firmware_dict = {}
	firmware_info = {}
	# load current firmware file into a dict
	current_firmware_dict = json.load(open(os.environ.get('SECONDARY_FIRMWARE_PATH'),'r'))
	# loop through all the config files under management, and see if they match
	for filepath in current_firmware_dict.keys():
		firmware_dict[filepath] = {}
		if os.path.exists(filepath):
			# First, let's handle the case that the file has substitutions
			if 'substitutions' in current_firmware_dict[filepath]:
				# load the raw file contents, i.e. before replacements are done
				content = base64.b64decode(current_firmware_dict[filepath]['content'])
				# do the template subs
				subs = current_custom_meta['configmanager']['substitutions'][filepath]
				content_after_subs = Template(content).substitute(subs)
				real_file_contents = open(filepath,'r').read()
				# compare to file on disk
				if content_after_subs == real_file_contents:
					# if file on disk is byte-identical to template-subbed file, we use the template content
				  firmware_dict[filepath]['content'] = current_firmware_dict[filepath]['content']
				else:
				  # otherwise, we use the real content of the file on disk
					firmware_dict[filepath]['content'] = base64.b64encode((open(filepath,"rb").read())).decode()
				# finally, we add in the existing other keys from the dict on disk
				firmware_dict[filepath]['substitutions'] = current_firmware_dict[filepath]['substitutions']
				if "reload_command" in current_firmware_dict:
					firmware_dict[filepath]['reload_command'] = current_firmware_dict[filepath]['reload_command']
			else:
				firmware_dict[filepath]['content'] = base64.b64encode((open(filepath,"rb").read())).decode()
			firmware_dict[filepath]['exists'] = True
		else:
			firmware_dict[filepath]['exists'] = False
	fw_string = dumps_json_canonical(firmware_dict)
	firmware_info['sha256'] = hashlib.sha256(fw_string.encode('utf-8')).hexdigest()
	firmware_info['length'] = len(fw_string)
	firmware_info['status'] = 'ok'
	# TODO make the message list a useful error
	firmware_info['message'] = 'Configmanager: Reported config for files: ' + ', '.join(current_firmware_dict.keys())
	return firmware_info

def install():
	install_report = {}
	newfile = os.environ.get('SECONDARY_FIRMWARE_PATH')
	oldfile = os.environ.get('SECONDARY_FIRMWARE_PATH_PREV')

	with open(newfile,"r") as f:
		configfile_string = f.read()
		newconfig = json.loads(configfile_string)
	# Check that the supplied file is canonicalized
	if not dumps_json_canonical(newconfig) == configfile_string:
		raise RuntimeError('Bad package supplied: package must be canonicalized JSON')
	try:
		apply_configurations(newconfig)
	except Exception as ex:
		try:
			with open(oldfile,"r") as f:
				oldconfig = json.load(f)
			apply_configurations(oldconfig)
		except Exception as rollback_ex:
			install_report['status'] = 'failed'
			install_report['message'] = f"Configmanager: failed to apply config with error: {repr(ex)}. \
			  Rollback to previous config also failed, with error: {repr(rollback_ex)}."
			return install_report
		else:
			install_report['status'] = 'failed'
			install_report['message'] = f"Configmanager: failed to apply config with error: {repr(ex)}, \
			  but rollback to previous config was successful."
			return install_report
	else:
		install_report['status'] = 'ok'
		install_report['message'] = 'Configmanager: Applied config for files: ' + ', '.join(baseconfig.keys())
		return install_report

def apply_configurations(myconfig):
	new_custom_meta = os.environ.get('SECONDARY_CUSTOM_METADATA')
	current_custom_meta = os.environ.get('SECONDARY_FIRMWARE_PATH') # todo pathlib to get enclosing dir
	# check if list of files in the config file we want to apply exactly matches the list in the configmanager config
	for filepath in myconfig:
		if myconfig[filepath]['exists']:
			if 'substitutions' in myconfig[filepath]:
				# verify that all variables to sub are present
				for sub in myconfig[filepath]['substitutions']:
					if sub not in new_custom_meta['substitutions'][filepath]:
						raise RuntimeError(f"Config to apply for file {filepath} requires variable {sub} to be defined, \
							but it was not present in the custom metadata.")
				# do the template replacement
				template = base64.b64decode(myconfig[filepath]['content'])
				filecontent = Template(template).substitute(new_custom_meta['substitutions'][filepath])
			else:
				filecontent = base64.b64decode(myconfig[filepath]['content'])
			with open(filepath,"wb") as f:
				f.write(filecontent)
				if 'reload_command' in myconfig[filepath]:
					os.system(" ".join(myconfig[filepath]['reload_command']))
		else:
			if os.path.exists(filepath):
				os.remove(filepath)


def dumps_json_canonical(mydict):
	return json.dumps(mydict,separators=(',',':'),sort_keys=True,ensure_ascii=False,allow_nan=False)

# TODO update this function to work with substitutions
def dump_current_firmware():
	firmware_dict = {}
	for filepath in baseconfig.keys():
		firmware_dict[filepath] = {}
		if os.path.exists(filepath):
			firmware_dict[filepath]['content'] = base64.b64encode((open(filepath,"rb").read())).decode()
			firmware_dict[filepath]['exists'] = True
		else:
			firmware_dict[filepath]['exists'] = False
	fw_string = dumps_json_canonical(firmware_dict)
	if args.outfile is not None:
		with open(args.outfile,"w") as f:
			f.write(fw_string)
	else:
		print(fw_string,end="")

def save_custom_meta:
	pass

	# create temp file if not exists
	# copy existing to $.rollback
	# write custom meta if any


if action == 'get-firmware-info':
	output = {}
	try:
		output = get_firmware_info()
	except Exception as ex:
		print(f"Could not get firmware info: {repr(ex)}")
		quit(65)
	else:
		print(json.dumps(output))
		quit()
elif action == 'install':
	output = {}
	try:
		output = install()
	except Exception as ex:
		print(f"Install action failure: {repr(ex)}")
		quit(65)
	else:
		print(json.dumps(output))
		quit()
elif action == 'dump-current-config':
	dump_current_firmware()



else:
	print("Unsupported action: " + action)
	quit(65)