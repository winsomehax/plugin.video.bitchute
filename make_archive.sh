#!/bin/sh
set -eu

addon_id=$(python3 -c "import xml.etree.ElementTree as ET; print(ET.parse('addon.xml').getroot().get('id'))")
version=$(python3 -c "import xml.etree.ElementTree as ET; print(ET.parse('addon.xml').getroot().get('version'))")

git archive --prefix="${addon_id}-${version}/" --format=zip "${version}" -o "${addon_id}-${version}.zip"
