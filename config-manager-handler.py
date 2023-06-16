#!/usr/bin/env python3

import argparse
import hashlib
import os
import json
import base64

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
	firmware_dict = {}
	firmware_info = {}
	for filepath in baseconfig.keys():
		firmware_dict[filepath] = {}
		if os.path.exists(filepath):
			if filepath['template']:
				pass
				# load the raw file
				# do the template subs in memory
				# compare to file on disk
				  # if file on disk is byte-identical to template-subbed file, base64-encode content of template file
				  # otherwise, b64-enc file on disk
			else:
				firmware_dict[filepath]['content'] = base64.b64encode((open(filepath,"rb").read())).decode()
			firmware_dict[filepath]['exists'] = True
		else:
			firmware_dict[filepath]['exists'] = False
	fw_string = dumps_json_canonical(firmware_dict)
	firmware_info['sha256'] = hashlib.sha256(fw_string.encode('utf-8')).hexdigest()
	firmware_info['length'] = len(fw_string)
	firmware_info['status'] = 'ok'
	firmware_info['message'] = 'Configmanager: Reported config for files: ' + ', '.join(baseconfig.keys())
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
			try:
				apply_configurations(baseconfig)
			except Exception as baseconfig_ex:
				install_report['status'] = 'failed'
				install_report['message'] = 'Configmanager: failed to apply config with error: ' + repr(ex) \
				  + '. Rollback to previous config also failed, with error: ' + repr(rollback_ex) \
				  + '. Rollback to base config also failed, with error: ' + repr(rollback_ex)
				return install_report
			else:
				install_report['status'] = 'failed'
				install_report['message'] = 'Configmanager: failed to apply config with error: ' + repr(ex) \
				  + '. Rollback to previous config also failed, with error: ' + repr(rollback_ex) \
				  + ', but rollback to base config was successful.'
				return install_report
		else:
			install_report['status'] = 'failed'
			install_report['message'] = 'Configmanager: failed to apply config with error: ' + repr(ex) \
			  + ', but rollback to previous config was successful.'
			return install_report
	else:
		install_report['status'] = 'ok'
		install_report['message'] = 'Configmanager: Applied config for files: ' + ', '.join(baseconfig.keys())
		return install_report

def apply_configurations(myconfig):
	# check if list of files in the config file we want to apply exactly matches the list in the configmanager config
	if not myconfig.keys() == baseconfig.keys():
		raise RuntimeError('Mismatched file list: attempted to apply configs for files ' + ', '.join(myconfig.keys()) \
			  + ', but this device requires configs for files ' + ', '.join(baseconfig.keys()))
	for filepath in myconfig:
		if myconfig[filepath]['exists']:
			if myconfig[filepath]['template']:
				pass
				# do the template replacement
			else:
				filecontent = base64.b64decode(myconfig[filepath]['content'])
			with open(filepath,"wb") as f:
				f.write(filecontent)
				if myconfig[filepath]['reload_command']:
					os.system(" ".join(myconfig[filepath]['reload_command']))
		else:
			if os.path.exists(filepath):
				os.remove(filepath)


def dumps_json_canonical(mydict):
	return json.dumps(mydict,separators=(',',':'),sort_keys=True,ensure_ascii=False,allow_nan=False)

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
		print('Could not get firmware info: ' + repr(ex))
		quit(65)
	else:
		print(json.dumps(output))
		quit()
elif action == 'install':
	output = {}
	try:
		output = install()
	except Exception as ex:
		print('Install action failure: ' + repr(ex))
		quit(65)
	else:
		print(json.dumps(output))
		quit()
elif action == 'dump-current-config':
	dump_current_firmware()



else:
	print("Unsupported action: " + action)
	quit(65)