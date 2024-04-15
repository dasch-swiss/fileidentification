import re
import json
from pathlib import Path
from conf.models import SFoutput, SfInfo, Match, SiegfriedConf, PolicyMsg, LogMsg, CleanUpTable


class SFParser:
    """parser to turn an output of siegfried to an SfInfo dataclass"""
    @staticmethod
    def fetch_puid(sfout: SFoutput) -> tuple[str | None, str | None]:
        """parse the processed_as out of the json returned by siegfried"""
        if sfout['matches'][0]['id'] == 'UNKNOWN':
            # TODO fallback may need to be more elaborate, as it takes the first proposition of siegfried, i.e. fileext
            fmts = re.findall(r"(fmt|x-fmt)/([\d]+)", sfout['matches'][0]['warning'])
            fmts = [f'{el[0]}/{el[1]}' for el in fmts]
            if fmts:
                return fmts[0], PolicyMsg.FALLBACK
            else:
                return None, None
        else:
            return sfout['matches'][0]['id'], None

    @staticmethod
    def to_SfInfo(sfout: SFoutput, file=False) -> SfInfo:
        """turns a single output of siegfried into an SfInfo dataclass object. it can also be used to load
        a protocol.json output for additional processing

        :argument sfout a single output of siegfried (it is an element of sigfriedoutput[files], which is the output
        of wrappers.wrappers.sf_analyse)
        :argument file if set to True, it indicated that the values a re parsed from a protocol and therefore fetch_puid
        does not need to be called again.
        """
        # mapp the siegfried output
        sfinfo = SfInfo(
            filename=Path(sfout['filename']),
            filesize=int(sfout['filesize']),
            modified=sfout['modified'],
            errors=sfout['errors'],
            )
        if SiegfriedConf.ALG in sfout:
            sfinfo.filehash = sfout[SiegfriedConf.ALG]
        for mat in sfout['matches']:
            mat = Match(
                ns=mat['ns'],
                id=mat['id'],
                formatname=mat['format'],
                version=mat['version'],
                mime=mat['mime'],
                formatclass=mat['class'],
                basis=mat['basis'],
                warning=mat['warning']
            )
            sfinfo.matches.append(mat)

        # parse the processed_as
        if not file:
            sfinfo.processed_as, msg = SFParser.fetch_puid(sfout)
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg)) if msg else None
            return sfinfo

        # parse the potential protocol.json values
        if 'processed_as' in sfout:
            sfinfo.processed_as = sfout['processed_as']
        if 'codec_info' in sfout:
            [sfinfo.codec_info.append(LogMsg(name=el['name'],
                                             msg=el['msg'],
                                             timestamp=el['timestamp'])) for el in sfout['codec_info']]
        # set the list of possible logs
        if 'processing_logs' in sfout:
            [sfinfo.processing_logs.append(LogMsg(name=el['name'],
                                                  msg=el['msg'],
                                                  timestamp=el['timestamp'])) for el in sfout['processing_logs']]
        # set tmp values used for processing
        if 'cu_table' in sfout:
            cu_table = CleanUpTable()
            [setattr(cu_table, k, Path(v)) for k, v in sfout['cu_table'].items()]
            sfinfo.cu_table = cu_table

        # do it recursive if there is a parent
        if 'derived_from' in sfout:
            setattr(sfinfo, 'derived_from', SFParser.to_SfInfo(sfout['derived_from']))

        return sfinfo

    @staticmethod
    def read_protocol(path: Path) -> list[SfInfo]:
        sfinfos: list[SfInfo] = []
        with open(path, 'r') as f:
            dump = json.load(f)
            sfinfos.extend([(SFParser.to_SfInfo(el, file=True)) for _, el in dump.items()])
        return sfinfos
