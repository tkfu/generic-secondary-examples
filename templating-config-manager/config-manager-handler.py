#!/usr/bin/env python3

import argparse
import hashlib
import os
import json
import base64
from string import Template
from pathlib import Path
import subprocess


parser=argparse.ArgumentParser()
parser.add_argument("action")
parser.add_argument("-o", "--outfile")

action = args.action

def get_firmware_info():
	# load current firmware file into a dict
	current_configmap = json.loads(current_firmware)
	current_custom_meta = {}
	if os.path.isfile(firmware_dir + '/custom-metadata.json'):
		current_custom_meta = json.loads(Path(firmware_dir + '/custom-metadata.json').read_text())
	output_firmware_dict = {}
	firmware_info = {}

	# loop through all the config files under management
	for filepath in current_configmap.keys():
		output_firmware_dict[filepath] = {}
		if os.path.exists(filepath):
			# First, let's handle the case that the file has substitutions
			if 'variables' in current_configmap[filepath]:
				# load the raw file contents, i.e. before replacements are done
				content = base64.b64decode(current_configmap[filepath]['content']).decode()
				# do the template subs
				subs = current_custom_meta['configmanager']['substitutions'][filepath]
				content_after_subs = Template(content).substitute(subs)
				real_file_contents = Path(filepath).read_text()
				# compare to file on disk
				if content_after_subs == real_file_contents:
					# if file on disk is identical to template-subbed file, we use the template content
					output_firmware_dict[filepath]['content'] = current_configmap[filepath]['content']
				else:
					# otherwise, we use the real content of the file on disk
					output_firmware_dict[filepath]['content'] = base64.b64encode(Path(filepath).read_bytes()).decode()
				# finally, we add back in the existing variables object from the dict on disk
				output_firmware_dict[filepath]['variables'] = current_configmap[filepath]['variables']
			# if there aren't any substitutions, we can just put the raw file in the content field (b64-encoded)
			else:
				output_firmware_dict[filepath]['content'] = base64.b64encode(Path(filepath).read_bytes()).decode()
			output_firmware_dict[filepath]['exists'] = True

			if "reload_command" in current_configmap:
				output_firmware_dict[filepath]['reload_command'] = current_configmap[filepath]['reload_command']

		else:
			output_firmware_dict[filepath]['exists'] = False
	fw_string = dumps_json_canonical(output_firmware_dict)
	firmware_info['sha256'] = hashlib.sha256(fw_string.encode('utf-8')).hexdigest()
	firmware_info['length'] = len(fw_string)
	firmware_info['status'] = 'ok'
	# TODO make the message list a useful error
	firmware_info['message'] = 'Configmanager: Files being managed: ' + ', '.join(current_configmap.keys())
	return firmware_info

def install():
	install_report = {}
	new_file = Path(os.environ.get('SECONDARY_FIRMWARE_PATH')).read_text()
	old_file = Path(os.environ.get('SECONDARY_FIRMWARE_PATH_PREV')).read_text()
	new_configmap = json.loads(new_file)
	old_configmap = json.loads(old_file)

	new_custom_meta = os.environ.get('SECONDARY_CUSTOM_METADATA')
	if os.path.isfile(firmware_dir + '/custom-metadata.json'):
		old_custom_meta = json.loads(Path(firmware_dir + '/custom-metadata.json').read_text())
	else:
		old_custom_meta = {}

	# apply the configmap
	try:
		# Check that the supplied file is canonicalized
		if not dumps_json_canonical(new_configmap) == new_file:
			raise RuntimeError('Bad package supplied: package must be canonicalized JSON')
		apply_configurations(new_configmap, new_custom_meta)
	except Exception as ex:
		try:
			apply_configurations(old_configmap, old_custom_meta)
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
		with open(firmware_dir + '/custom-metadata.json',"w") as f:
			f.write(new_custom_meta)
		return install_report

def apply_configurations(configmap, custom_meta):
	for filepath in configmap:
		if configmap[filepath]['exists']:
			if os.path.isfile(filepath):
				old_filecontent = Path(filepath).read_text()
			# do the templating case
			if 'substitutions' in configmap[filepath]:
				# verify that all variables to sub are present
				for sub in configmap[filepath]['substitutions']:
					if sub not in custom_meta['substitutions'][filepath]:
						raise RuntimeError(f"Config to apply for file {filepath} requires variable {sub} to be defined, \
							but it was not present in the custom metadata.")
				# do the template replacement
				template = base64.b64decode(configmap[filepath]['content']).decode()
				filecontent = Template(template).substitute(custom_meta['substitutions'][filepath])
			else:
				filecontent = base64.b64decode(configmap[filepath]['content'])
			with open(filepath,"wb") as f:
				f.write(filecontent)
			if 'reload_command' in configmap[filepath] and old_filecontent != filecontent:
				proc = subprocess.run(configmap[filepath]['reload_command'], shell=True, check=True, capture_output=True)
				(out, err) = proc.communicate()
				if proc.returncode != 0:
					raise RuntimeError(f"Command '{' '.join(configmap[filepath]['reload_command'])}' failed after replacing {filepath}.")

		else:
			if os.path.isfile(filepath):
				os.remove(filepath)

def dumps_json_canonical(mydict):
	return json.dumps(mydict,separators=(',',':'),sort_keys=True,ensure_ascii=False,allow_nan=False)

try:
	with open(os.environ['SECONDARY_FIRMWARE_PATH'],"r") as f:
		current_firmware = f.read()
		firmware_dir = Path(os.environ['SECONDARY_FIRMWARE_PATH']).absolute().parent
	except KeyError as ex:
		print("Error: SECONDARY_FIRMWARE_PATH environment variable not set.")
		quit(65)
	except Exception as ex:
		print(f"Failed to open file specified by SECONDARY_FIRMWARE_PATH: {repr(ex)}")
		quit(65)

if action == 'get-firmware-info':
	output = {}
	try:
		output = get_firmware_info()
	except Exception as ex:
		output['sha256'] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
		output['length'] = 0
		output['status'] = "failed"
		output['message'] = f"Failed to get firmware info with error {repr(ex)}"
		print(json.dumps(output))
		quit()
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

else:
	print("Unsupported action: " + action)
	quit(65)