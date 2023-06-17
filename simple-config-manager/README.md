# Toradex Labs Simple Configuration Manager

This is an intentionally simple, not-very-flexible, feature-limited, purely declarative configuration manager, written as a zero-dependency python script.

It's designed for use as a generic secondary action handler.

This secondary accepts JSON files representing a desired configuration state as its package. There's a specific format these packages need to be in; you can read the Package Format section below for details, but there are python scripts to generate the packages, so you don't have to worry about doing it manually.

## Setup/installation

There are three steps you'll need to follow to get the configuration manager up and running:

1. Create a base configuration
2. Put the `config-manager-handler.py` and the base configuration on your device
3. Add a `generic-secondary` to aktualizr's config, using the handler script as its action handler

### 1. Create a base configuration

The configuration manager's base configuration has two functions: it defines the list of files that the configuration manager will manage, and it acts as a "last-resort" rollback.

Your base configuration should be a configuration manager package. You can create a package using `build-config-package.py`.

### 2. Copy the action handler script and base config to your device

You can do this manually via SSH. If you put it in `/etc`, you can also use TorizonCore Builder to create a custom image that includes the configuration manager secondary.

For the purposes of the examples here, we'll assume you put it in `/etc/sota/secondary-action-handlers/`.

### 3. Configure aktualizr to use the configuration manager

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
            "ecu_hardware_id": "toradexlabs-configuration-manager", 
            "full_client_dir": "/var/sota/storage/toradexlabs-config-manager",
            "ecu_private_key": "sec.private",
            "ecu_public_key": "sec.public",
            "firmware_path": "/var/sota/storage/toradexlabs-config-manager/current-config.json",
            "target_name_path": "/var/sota/storage/toradexlabs-config-manager/target_name",
            "metadata_path": "/var/sota/storage/toradexlabs-config-manager/metadata",
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

The action handler script can also create a config package. `config-manager-handler.py dump-current-config` will print the currently-running config (for the files listed in your base configuration) to stdout. You can specify `-o / --outfile <filename>` to save the result to a file.

## Updating configs

Just upload your config package to the platform, giving it the same hardware_id as you specified in your secondary config above, and initiate updates as normal.

## TODOs and WONT-DOs

TODO:

* Add some kind of versioning to the package format
* More robust error handling
* Maybe: Add the capability to specify a command to run after writing the config to make it take effect, per file (e.g. doing a `systemctl reload` on the service whose config you just changed)
* Maybe: manage permissions on files
* Maybe: Save current config at start of install routine to allow rollback to original state, even if it's not saved in `SECONDARY_FIRMWARE_PATH_PREV`


WONT-DOs:

* Anything relating to managing parts of files. That includes using variables, doing partial modifications, patch/diff-based changes, or any kind of rule-based replacement. This is called the Simple Configuration Manager for a reason.

## Appendix: Package format

This configuration manager accepts packages in JSON format. The format is designed to be as simple as possible, so it's easy to understand.

Each top-level property is a file path that will be managed by the configuration manager. The value of each key is a JSON object with two properties: `exists`, which is a boolean saying whether the file should exist or not, and `content`, which is the base64-encoded content of the file (if it exists). If `exists` is false, there will be no `content` property. Here's an example, pretty-printed:

```json
{
    "/etc/fluent-bit/fluent-bit.conf":
    {
        "exists": true,
        "content": "W1NFUlZJQ0VdCiAgICBmbHVzaCAgICAgICAgMQogICAgZGFlbW9uICAgICAgIE9mZgogICAgbG9nX2xldmVsICAgIGluZm8KICAgIHBhcnNlcnNfZmlsZSBwYXJzZXJzLmNvbmYKICAgIHBsdWdpbnNfZmlsZSBwbHVnaW5zLmNvbmYKCltJTlBVVF0KICAgIG5hbWUgICAgICAgICBjcHUKICAgIHRhZyAgICAgICAgICBjcHUKICAgIGludGVydmFsX3NlYyAzMDAKCltGSUxURVJdCiAgICBOYW1lICAgICAgIG5lc3QKICAgIE1hdGNoICAgICAgY3B1CiAgICBPcGVyYXRpb24gIG5lc3QKICAgIFdpbGRjYXJkICAgKgogICAgTmVzdF91bmRlciBjcHUKCltJTlBVVF0KICAgIG5hbWUgICAgICAgICBtZW0KICAgIHRhZyAgICAgICAgICBtZW1vcnkKICAgIGludGVydmFsX3NlYyAzMDAKCltGSUxURVJdCiAgICBOYW1lICAgICAgIG5lc3QKICAgIE1hdGNoICAgICAgbWVtb3J5CiAgICBPcGVyYXRpb24gIG5lc3QKICAgIFdpbGRjYXJkICAgKgogICAgTmVzdF91bmRlciBtZW1vcnkKCltJTlBVVF0KICAgIG5hbWUgICAgICAgICB0aGVybWFsCiAgICB0YWcgICAgICAgICAgdGVtcGVyYXR1cmUKICAgIG5hbWVfcmVnZXggICB0aGVybWFsX3pvbmUwCiAgICBpbnRlcnZhbF9zZWMgMzAwCgpbRklMVEVSXQogICAgTmFtZSAgICAgICBuZXN0CiAgICBNYXRjaCAgICAgIHRlbXBlcmF0dXJlCiAgICBPcGVyYXRpb24gIG5lc3QKICAgIFdpbGRjYXJkICAgKgogICAgTmVzdF91bmRlciB0ZW1wZXJhdHVyZQoKW0lOUFVUXQogICAgbmFtZSAgICAgICAgIHByb2MKICAgIHByb2NfbmFtZSAgICBkb2NrZXJkCiAgICB0YWcgICAgICAgICAgcHJvY19kb2NrZXIKICAgIGZkICAgICAgICAgICBmYWxzZQogICAgbWVtICAgICAgICAgIGZhbHNlCiAgICBpbnRlcnZhbF9zZWMgMzAwCgpbRklMVEVSXQogICAgTmFtZSAgICAgICBuZXN0CiAgICBNYXRjaCAgICAgIHByb2NfZG9ja2VyCiAgICBPcGVyYXRpb24gIG5lc3QKICAgIFdpbGRjYXJkICAgKgogICAgTmVzdF91bmRlciBkb2NrZXIKCltJTlBVVF0KICAgIE5hbWUgICAgICAgICAgZXhlYwogICAgVGFnICAgICAgICAgICBkaXNrc2l6ZQogICAgQ29tbWFuZCAgICAgICBkZiAtayB8IGdyZXAgb3Rhcm9vdCB8IGpxIC1SIC1jIC1zICdnc3ViKCIgKyI7ICIgIikgfCBzcGxpdCgiICIpIHwgeyAib3Rhcm9vdF90b3RhbCI6IC5bMV0sICJvdGFyb290X3VzZWQiOiAuWzJdLCAib3Rhcm9vdF9hdmFpbCI6IC5bM119JwogICAgUGFyc2VyICAgICAgICBqc29uCiAgICBJbnRlcnZhbF9TZWMgIDEwMAoKW0ZJTFRFUl0KICAgIE5hbWUgICAgICAgbmVzdAogICAgTWF0Y2ggICAgICBkaXNrc2l6ZQogICAgT3BlcmF0aW9uICBuZXN0CiAgICBXaWxkY2FyZCAgICoKICAgIE5lc3RfdW5kZXIgY3VzdG9tCgpbT1VUUFVUXQogICAgbmFtZSAgIHRjcAogICAgcG9ydCAgIDg4NTAKICAgIGZvcm1hdCBqc29uX2xpbmVzCiAgICBtYXRjaCAgKgo="
    },
    "/etc/sota/conf.d/99.custom-loglevel.toml":
    {
    	"exists": false
    }
}
```

The package JSON file MUST be canonicalized. That means all non-meaningful whitespace must be removed, keys must be sorted in lexical order, and it must use utf-8 encoding.

