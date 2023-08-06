import json
import hashlib
import os
import sys
import zipfile
import urllib.request
from pathlib import Path

def fail(msg):
	print(f'Could not add mod to index: {msg}')
	sys.exit(-1)


index_path = Path(sys.argv[1])
issue_author = sys.argv[2]
if len(sys.argv) == 3:
	issue_body = os.environ['ISSUE_BODY']
else:
	# not passing issue body as a system argument for injection reasons
	# but its still here for testing
	issue_body = sys.argv[3]



if 'Your mod link' not in issue_body:
	print('Not a valid index entry')
	sys.exit(0)

# Download the geode file
try:
	mod_url = issue_body.replace('### Your mod link\n\n', '')

	urllib.request.urlretrieve(mod_url, 'mod.geode')

except Exception as inst:
	fail(f'Could not download the geode file: {inst}')

# Validate the geode file
try:
	archive = zipfile.ZipFile('mod.geode', 'r')
	mod_json = json.loads(archive.read('mod.json'))
	mod_id = mod_json['id']
	mod_version = mod_json['version'].replace('v', '')

	file_list = archive.namelist()	

except Exception as inst:
	fail(f'Not a valid geode file: {inst}')


# Populate entry.json
try:
	mod_platforms = []
	if f"{mod_id}.dylib" in file_list:
		mod_platforms.append("macos")
	if f"{mod_id}.dll" in file_list:
		mod_platforms.append("windows")
	if f"{mod_id}.so" in file_list:
		mod_platforms.append("android")
	if f"{mod_id}.ios.dylib" in file_list:
		mod_platforms.append("ios")

	mod_tags = mod_json.get("tags", [])
	mod_data = open("mod.geode", "rb").read()
	mod_hash = hashlib.sha256(mod_data).hexdigest()

	# for backwards compatibility
	old_mod_hash = hashlib.sha3_256(mod_data).hexdigest()

	entry_json = {
		"commit-author": issue_author,
		"platforms": mod_platforms,
		"mod": {
			"download": mod_url,
			"hash": old_mod_hash,
			"hash256": mod_hash
		},
		"tags": mod_tags
	}
except Exception as inst:
	fail(f'Could not populate entry.json: {inst}')



def write_general_files(general_path):
	if "logo.png" in file_list:
		archive.extract("logo.png", path=general_path)
	if "about.md" in file_list:
		archive.extract("about.md", path=general_path)
	if "changelog.md" in file_list:
		archive.extract("changelog.md", path=general_path)


def write_version_files(version_path):
	json.dump(entry_json, open(version_path / "entry.json", "w"), indent=4)
	archive.extract("mod.json", path=version_path)


# Fill the old directory / for backwards compatibility
try:
	old_mod_version = mod_version.split('.')[0]
	old_mod_directory = index_path / 'mods' / (mod_id + '@' + old_mod_version)
	old_mod_directory.mkdir(exist_ok=True)

	write_general_files(old_mod_directory)
	write_version_files(old_mod_directory)

except Exception as inst:
	fail(f'Could not populate old mod folder {old_mod_directory}: {inst}')


# Very sad code i know
def compare_versions(version1, version2):
	if '-' not in version1:
		version1 += '?'
	if '-' not in version2:
		version2 += '?'

	return version1 > version2


# Fill the directory
try:
	mod_directory = index_path / 'mods-v2' / mod_id
	version_mod_directory = mod_directory / mod_version
	version_mod_directory.mkdir(parents=True, exist_ok=True)

	write_version_files(version_mod_directory)

	latest_version = mod_version
	for path in mod_directory.iterdir():
		if compare_versions(path.name, latest_version):
			latest_version = path.name

	if mod_version == latest_version:
		write_general_files(mod_directory)

except Exception as inst:
	fail(f'Could not populate mod folder {version_mod_directory}: {inst}')

print(f'Successfully added {mod_id}')