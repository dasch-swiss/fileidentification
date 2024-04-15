import json
from lxml import etree, objectify
import os
import requests

####
# set the version manually as it is a pain to parse
# -> nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm


def main(version="V116", outpath=""):

    # tmp xml_filname
    xml_filename = f'droid_{version}.xml'

    # get the droid xml content and save it to file (as it is large and to avoid error on etree.parse)
    with open(xml_filename, 'w') as f:
        f.write(requests.get(
            f'https://cdn.nationalarchives.gov.uk/documents/DROID_SignatureFile_{version}.xml').content.decode('utf-8'))

    # open XML file and strip namespaces, delete the xml
    tree = etree.parse(xml_filename)
    os.remove(xml_filename)
    root = tree.getroot()
    for elem in root.getiterator():
        if not hasattr(elem.tag, 'find'):
            continue
        i = elem.tag.find('}')
        if i >= 0:
            elem.tag = elem.tag[i + 1:]
    objectify.deannotate(root, cleanup_namespaces=True)

    # parse XML and write json
    puids: dict = {}

    for target in root.findall('.//FileFormat'):
        format_info: dict = {}
        file_extensions: list = []

        puid = target.attrib['PUID']

        if target.attrib['Name']:
            format_info['name'] = target.attrib['Name']

        for extens in target.findall('.//Extension'):
            file_extensions.append(extens.text)

        format_info['file_extensions'] = file_extensions

        puids[puid] = format_info

    json_path = os.path.join(outpath, 'fmt2ext.json')
    with open(json_path, 'w') as f:
        json.dump(puids, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main()
