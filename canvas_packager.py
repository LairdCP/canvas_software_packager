#!/usr/bin/python

"""
Canvas software package creation tool

Example execution:

    canvas_packager.py --version 1.0.0 xbit_mg100_ble_to_mqtt
"""

import os
import zipfile
import argparse
import textwrap
import hashlib
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

# Compute the SHA256 hash of the given file
def sha256sum(filename):
    hasher = hashes.Hash(hashes.SHA256())
    with open(filename, 'rb') as f:
        while chunk := f.read(4096):
            hasher.update(chunk)
    return hasher.finalize()

# Sign a file using our private key
def sign(filename, key):
    hash = sha256sum(filename)
    return key.sign(hash, ec.ECDSA(utils.Prehashed(hashes.SHA256())))

# Parse the command line arguments
parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
                Tool to create a software update package for devices running
                Canvas firmware. The software update package is a ZIP file
                containing a JSON manifest. This tool, givem a directory of
                files comprising the update, will generate the manifest file
                and create the ZIP file. The resulting ZIP file will be
                suitable for use in updating the application software of a
                supoported Canvas device.
                '''))
parser.add_argument("directory", help="directory to package, also used as package name")
parser.add_argument("--version", "-v", help="Version number to use", required=True)
parser.add_argument("--sign", "-s", help="Sign the source files with the provided private key")
args = parser.parse_args()

# Gather the file list
if os.path.isdir(args.directory) is False:
    print("Directory argument must be a subdirectory of the current directory")
    exit(1)
files = [f for f in os.listdir(args.directory) if os.path.isfile(os.path.join(args.directory, f))]
if "manifest.json" in files:
    files.remove("manifest.json")

# Open the key file if we were asked to sign
if args.sign is not None:
    with open(args.sign, "rb") as key_file:
        key = serialization.load_pem_private_key(key_file.read(), password=None)

# Build the manifest
manifest = {}
manifest["name"] = args.directory
manifest["version"] = args.version
if args.sign is not None:
    manifest["verify"] = "ecdsa-sha256"
    manifest["files"] = {}
    for f in sorted(files):
        manifest["files"][f] = sign(os.path.join(args.directory, f), key).hex()
else:
    manifest["verify"] = "sha256"
    manifest["files"] = {}
    for f in sorted(files):
        manifest["files"][f] = sha256sum(os.path.join(args.directory, f)).hex()

# Write the manifest file
with open(os.path.join(args.directory, "manifest.json"), "w") as f:
    f.write(json.dumps(manifest, indent=4))

# Create the ZIP file
with zipfile.ZipFile(args.directory + "_" + args.version + ".zip", "w", compression=zipfile.ZIP_STORED) as zip:
    for f in sorted(files):
        zip.write(os.path.join(args.directory, f), arcname=f)
    zip.write(os.path.join(args.directory, "manifest.json"), arcname="manifest.json")
