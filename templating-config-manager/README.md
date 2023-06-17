# Toradex Labs Templating Configuration Manager

This is an somehat simple, somewhat-flexible, feature-limited, purely declarative templating configuration manager, written as a zero-dependency python script.

It's designed for use as a generic secondary action handler.

This secondary accepts JSON files representing a desired configuration state as its package. There's a specific format these packages need to be in; you can read the Package Format section below for details, but there are python scripts to help generate the packages, so you don't have to do it all manually.

## Setup/installation

There are two steps you'll need to follow to get the configuration manager up and running:

1. Put the `config-manager-handler.py` and the base configuration on your device
2. Add a `generic-secondary` to aktualizr's config, using the handler script as its action handler


### 1. Copy the action handler script and base config to your device

You can do this manually via SSH. If you put it in `/etc`, you can also use TorizonCore Builder to create a custom image that includes the configuration manager secondary.

For the purposes of the examples here, we'll assume you put it in `/etc/sota/secondary-action-handlers/`.

### 2. Configure aktualizr to use the configuration manager

For this step, you will need to [modify aktualizr's config](https://developer.toradex.com/torizon/torizon-platform/torizon-updates/aktualizr-modifying-the-settings-of-torizon-ota-client).

For example, you can create a file with the following content at `/etc/sota/conf.d/51-custom-secondaries.toml`:

```
[uptane]
secondary_config_file = "/etc/sota/custom_secondaries.json"
```

...and then create `/etc/sota/custom_secondaries.json` with the following content:

```json
{
    "docker-compose": [
        {
            "partial_verifying": false,
            "ecu_hardware_id": "docker-compose",
            "full_client_dir": "/var/sota/storage/docker-compose",
            "ecu_private_key": "sec.private",
            "ecu_public_key": "sec.public",
            "firmware_path": "/var/sota/storage/docker-compose/docker-compose.yml",
            "target_name_path": "/var/sota/storage/docker-compose/target_name",
            "metadata_path": "/var/sota/storage/docker-compose/metadata"
        }
    ],
    "torizon-generic": [
        {
            "partial_verifying": false,
            "ecu_hardware_id": "toradexlabs-templating-config-manager", 
            "full_client_dir": "/var/sota/storage/toradexlabs-templating-config-manager",
            "ecu_private_key": "sec.private",
            "ecu_public_key": "sec.public",
            "firmware_path": "/var/sota/storage/toradexlabs-templating-config-manager/current-config.json",
            "target_name_path": "/var/sota/storage/toradexlabs-templating-config-manager/target_name",
            "metadata_path": "/var/sota/storage/toradexlabs-templating-config-manager/metadata",
            "action_handler_path": "/etc/sota/secondary-action-handlers/config-manager-handler.py"
        }
    ]
}
```

## Creating config packages

The easiest way to create a config package is to use the `build-config-package.py` script in this repository.

```
$ ./build-config-package.py -h
usage: build-config-package.py [-h] [--add destination_path config_file] [--delete destination_path] output_file

Create configuration management packages for the Toradex Labs Simple Configuration Manager

positional arguments:
  output_file           The name of the package to be written. This is the file you can 
                        upload to the Torizon platform.

options:
  -h, --help            show this help message and exit
  --add destination_path config_file
                        Adds a file to the config management package. <destination_path>
                        is the fully-qualified location on the device of the file that 
                        will be managed. <config_file> is the file you want to put there.
                        May be specified multiple times.
  --delete destination_path
                        Adds a file to the configuration package that should be deleted.
                        May be specified multiple times.
```

However, this script does not yet support adding the service reload command; you'll have to do that manually and then canonicalize the json file again.

### Using variable substitution in config files

This secondary will execute variable substitution before it writes the config files. Anything of the form `${var_name}` found inside config file content will be used for templating. All instances of `$` inside the config file MUST be escaped by replacing them with `$$`. See the [python documentation on template strings](https://docs.python.org/3.4/library/string.html#template-strings) for more detail.

## Updating configs

Just upload your config package to the platform, giving it the same hardware_id as you specified in your secondary config above, and initiate updates as normal.

For variable substitution, you have to pass in some custom metadata. If you wish to define defaults for any of the variables, you may do so in the custom metadata of the package you upload to the platform. All variables without defaults must be specified in custom metadata when you launch the update. See `sample-custom-metadata.json` in the fixtures directory for an example.

There is no help or hinting in the web UI about this; it is the operator's responsibility to know what variables are required for each file. If you miss one, the update will fail.

## TODO

* Add some kind of versioning to the package format
* More robust error handling
* Maybe: manage permissions on files
* Maybe: Save current config at start of install routine to allow rollback to original state, even if it's not saved in `SECONDARY_FIRMWARE_PATH_PREV`


## Appendix: Package format

This configuration manager accepts packages in JSON format. The format is designed to be as simple as possible, so it's easy to understand.

Each top-level property is a file path that will be managed by the configuration manager. The value of each key is a JSON object with up to four properties:
* `exists`: a boolean saying whether the file should exist or not. If `exists` is true, it must be the only property/
* `content`: the base64-encoded content of the file (if it exists).
* `variables`: a list of the variables available for replacement in the config file encoded in `content`. If there are any variable identifiers in the config file, they MUST be listed here.
* `reload_command`: An optional parameter specifying a command to be run when this config file is changed. Should be an array ready to be passed to python's `subprocess.run()`.

Here's an example, pretty-printed:

```json
{
    "/etc/fluent-bit/fluent-bit.conf":
    {
        "exists": true,
        "content": "W1NFUlZJQ0VdCiAgICBmbHVzaCAgICAgICAgMQogICAgZGFlbW9uICAgICAgIE9mZgogICAgbG9nX2xldmVsICAgIGluZm8KICAgIHBhcnNlcnNfZmlsZSBwYXJzZXJzLmNvbmYKICAgIHBsdWdpbnNfZmlsZSBwbHVnaW5zLmNvbmYKCltJTlBVVF0KICAgIG5hbWUgICAgICAgICBjcHUKICAgIHRhZyAgICAgICAgICBjcHUKICAgIGludGVydmFsX3NlYyAke2ludGVydmFsfQoKW0ZJTFRFUl0KICAgIE5hbWUgICAgICAgbmVzdAogICAgTWF0Y2ggICAgICBjcHUKICAgIE9wZXJhdGlvbiAgbmVzdAogICAgV2lsZGNhcmQgICAqCiAgICBOZXN0X3VuZGVyIGNwdQoKW0lOUFVUXQogICAgbmFtZSAgICAgICAgIG1lbQogICAgdGFnICAgICAgICAgIG1lbW9yeQogICAgaW50ZXJ2YWxfc2VjICR7aW50ZXJ2YWx9CgpbRklMVEVSXQogICAgTmFtZSAgICAgICBuZXN0CiAgICBNYXRjaCAgICAgIG1lbW9yeQogICAgT3BlcmF0aW9uICBuZXN0CiAgICBXaWxkY2FyZCAgICoKICAgIE5lc3RfdW5kZXIgbWVtb3J5CgpbSU5QVVRdCiAgICBuYW1lICAgICAgICAgdGhlcm1hbAogICAgdGFnICAgICAgICAgIHRlbXBlcmF0dXJlCiAgICBuYW1lX3JlZ2V4ICAgdGhlcm1hbF96b25lMAogICAgaW50ZXJ2YWxfc2VjICR7aW50ZXJ2YWx9CgpbRklMVEVSXQogICAgTmFtZSAgICAgICBuZXN0CiAgICBNYXRjaCAgICAgIHRlbXBlcmF0dXJlCiAgICBPcGVyYXRpb24gIG5lc3QKICAgIFdpbGRjYXJkICAgKgogICAgTmVzdF91bmRlciB0ZW1wZXJhdHVyZQoKW0lOUFVUXQogICAgbmFtZSAgICAgICAgIHByb2MKICAgIHByb2NfbmFtZSAgICBkb2NrZXJkCiAgICB0YWcgICAgICAgICAgcHJvY19kb2NrZXIKICAgIGZkICAgICAgICAgICBmYWxzZQogICAgbWVtICAgICAgICAgIGZhbHNlCiAgICBpbnRlcnZhbF9zZWMgJHtpbnRlcnZhbH0KCltGSUxURVJdCiAgICBOYW1lICAgICAgIG5lc3QKICAgIE1hdGNoICAgICAgcHJvY19kb2NrZXIKICAgIE9wZXJhdGlvbiAgbmVzdAogICAgV2lsZGNhcmQgICAqCiAgICBOZXN0X3VuZGVyIGRvY2tlcgoKW0lOUFVUXQogICAgTmFtZSAgICAgICAgICBleGVjCiAgICBUYWcgICAgICAgICAgIGRpc2tzaXplCiAgICBDb21tYW5kICAgICAgIGRmIC1rIHwgZ3JlcCBvdGFyb290IHwganEgLVIgLWMgLXMgJ2dzdWIoIiArIjsgIiAiKSB8IHNwbGl0KCIgIikgfCB7ICJvdGFyb290X3RvdGFsIjogLlsxXSwgIm90YXJvb3RfdXNlZCI6IC5bMl0sICJvdGFyb290X2F2YWlsIjogLlszXX0nCiAgICBQYXJzZXIgICAgICAgIGpzb24KICAgIGludGVydmFsX3NlYyAgJHtpbnRlcnZhbH0KCltGSUxURVJdCiAgICBOYW1lICAgICAgIG5lc3QKICAgIE1hdGNoICAgICAgZGlza3NpemUKICAgIE9wZXJhdGlvbiAgbmVzdAogICAgV2lsZGNhcmQgICAqCiAgICBOZXN0X3VuZGVyIGN1c3RvbQoKW09VVFBVVF0KICAgIG5hbWUgICB0Y3AKICAgIHBvcnQgICA4ODUwCiAgICBmb3JtYXQganNvbl9saW5lcwogICAgbWF0Y2ggICo=",
        "variables": ["interval"],
        "reload_command": ["/usr/bin/systemctl", "reload", "fluent-bit"]
    },
    "/etc/sota/conf.d/99.custom-loglevel.toml":
    {
        "exists": false
    }
}
```

The package JSON file MUST be canonicalized. That means all non-meaningful whitespace must be removed, keys must be sorted in lexical order, and it must use utf-8 encoding. You can canonicalize a JSON string using the following python function:

```python
json.dumps(mydict,separators=(',',':'),sort_keys=True,ensure_ascii=False,allow_nan=False)
```
