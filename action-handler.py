import argparse
import hashlib
import os
import json

parser=argparse.ArgumentParser()
parser.add_argument("handler")

args = parser.parse_args
action = args.handler

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
		print('Install handler failure: ' + repr(ex))
		quit(65)
	else:
		print json.dumps(output)
		quit()
elif action == 'complete-install':
	output = {}
	try:
		output = complete_install()
	except Exception as ex:
		print('Complete_install handler failed: ' + repr(ex))
		quit(65)
	else:
		print(json.dumps(output))
		quit()
else:
	print("Unsupported action:" + action)
	quit(65)

def get_firmware_info():
	firmware_info = {}
	firmware_info['sha256'] = calculate_firmware_hash
	firmware_info['length'] = calculate_firmware_size
	firmware_info['status'] = 'ok'
	firmware_info['message'] = 'Default action handler debug message: get_firmware_info'
	return firmware_info

def install():
	install_report = {}
	try:
		# insert installation logic here
		pass
	except Exception as ex:
		install_report['status'] = 'failed'
		install_report['message'] = 'Default action handler install failed:' + repr(ex)
	else:
		install_report['status'] = 'ok'
		install_report['message'] = 'Default action handler install succeeded'
	return install_report

def complete_install():
	complete_install_report = {}
	complete_install_report['status'] = 'ok'
	complete_install_report['message'] = 'Default action handler debug message: complete_install'
	return complete_install_report

def calculate_firmware_hash():
	filepath = os.environ.get('SECONDARY_FIRMWARE_PATH')
	sha256_hash = hashlib.sha256()
	with open(filepath,"rb") as f:
		for byte_block in iter(lambda: f.read(4096),b""):
			sha256_hash.update(byte_block)
	return sha256_hash.hexdigest()

def calculate_firmware_size():
	filepath = os.environ.get('SECONDARY_FIRMWARE_PATH')
	return os.stat(filepath).st_size


    

