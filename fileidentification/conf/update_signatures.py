import json
import os
from pathlib import Path
from lxml import etree, objectify
import requests
import typer
from typer import secho, colors
from bs4 import BeautifulSoup
from fileidentification.conf.settings import PathsConfig, DroidSigURL


def write_fmt2ext(link=None, outpath=""):

    if not link:
        version = "V119.xml"
        link = f'{DroidSigURL.cdnNA}{version}'

    # outpath
    json_path = Path('fmt2ext.json') if not outpath else Path(outpath)

    # tmp xml_filname
    xml_filename = Path(f'droid_{link[-8:]}')

    # get the droid xml content and save it to file (as it is large and to avoid error on etree.parse)
    res = requests.get(link)
    if res.status_code != 200:
        secho(f'could not fetch {link}', fg=colors.RED)
        raise typer.Exit(1)
    xml_filename.write_text(res.content.decode('utf-8'))

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

    with open(json_path, 'w') as f:
        json.dump(puids, f, indent=4, ensure_ascii=False)

    if json_path.is_file():
        secho(f"extensions and names updated to {link[-8:-4]} in {json_path}", fg=colors.GREEN)


def update_signatures():
    # get the latest signaturefile link
    secho(f'... updating {PathsConfig.FMT2EXT}')
    url = DroidSigURL.NALIST
    res = requests.get(url)
    if res.status_code != 200:
        secho(f'could not fetch {url}', fg=colors.RED)
        raise typer.Exit(1)

    soup = BeautifulSoup(res.content, 'html.parser')
    versions = [el.get("href") for el in soup.find_all("a") if el.get("href") and
                el.get("href").startswith(DroidSigURL.cdnNA)]
    link = (sorted(versions)[-1])
    if not link:
        secho(f'could not parse links out of {url}', fg=colors.RED)
        raise typer.Exit(1)

    # update fm
    write_fmt2ext(link=link, outpath=PathsConfig.FMT2EXT)


if __name__ == '__main__':
    typer.run(write_fmt2ext)
