import json
from pathlib import Path

import requests  # type: ignore
import typer
from bs4 import BeautifulSoup
from lxml import etree, objectify  # type: ignore
from typer import colors, secho

from fileidentification.definitions.constants import FMT2EXT, DroidSigURL


def write_fmt2ext(link: str, outpath: str = "") -> None:
    # outpath
    json_path = Path(FMT2EXT) if not outpath else Path(outpath)

    # tmp xml_filname
    xml_filename = Path(f"droid_{link[-8:]}")

    # get the droid xml content and save it to file (as it is large and to avoid error on etree.parse)
    res = requests.get(link)
    if res.status_code != 200:  # noqa PLR2004
        secho(f"could not fetch {link}", fg=colors.RED)
        raise typer.Exit(1)
    xml_filename.write_text(res.content.decode("utf-8"))

    # open XML file and strip namespaces, delete the xml
    tree = etree.parse(xml_filename)
    xml_filename.unlink()
    root = tree.getroot()
    for elem in root.getiterator():
        if not hasattr(elem.tag, "find"):
            continue
        i = elem.tag.find("}")
        if i >= 0:
            elem.tag = elem.tag[i + 1 :]
    objectify.deannotate(root, cleanup_namespaces=True)

    # parse XML and write json
    puids: dict = {}  # type: ignore

    for target in root.findall(".//FileFormat"):
        format_info: dict = {}  # type: ignore
        file_extensions: list = []  # type: ignore

        puid = target.attrib["PUID"]

        if target.attrib["Name"]:
            format_info["name"] = target.attrib["Name"]

        for extens in target.findall(".//Extension"):
            file_extensions.append(extens.text)

        format_info["file_extensions"] = file_extensions

        puids[puid] = format_info

    json_path.write_text(json.dumps(puids, indent=4, ensure_ascii=False))
    secho(
        f"extensions and names updated to {link[-8:-4]} in {json_path}",
        fg=colors.GREEN,
    )


def update_signatures() -> None:
    # get the latest signaturefile link
    secho(f"... updating {FMT2EXT}")
    url = DroidSigURL.NALIST
    res = requests.get(url)
    if res.status_code != 200:  # noqa PLR2004
        secho(f"could not fetch {url}", fg=colors.RED)
        raise typer.Exit(1)

    soup = BeautifulSoup(res.content, "html.parser")
    versions = [
        el.get("href")
        for el in soup.find_all("a")
        if el.get("href") and el.get("href").startswith(DroidSigURL.cdnNA)  # type: ignore
    ]
    link = sorted(versions)[-1]  # type: ignore
    if not link:
        secho(f"could not parse links out of {url}", fg=colors.RED)
        raise typer.Exit(1)
    # update fm
    write_fmt2ext(link=link, outpath=FMT2EXT)  # type: ignore


if __name__ == "__main__":
    typer.run(update_signatures)
