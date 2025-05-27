import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from fileidentification.conf.models import BasicAnalytics
from fileidentification.conf.settings import Bin, JsonOutput

####
# configuration template
# default: a dict of puid of files, first value of list determine whether the format is accepted or not
####

#
systemfiles: list = ['fmt/394']  # .DS_Store etc

default_values: dict = {

    # pattern
    # fmt : [accepted, bin, target file container, args, [expected fmt]]
    # bin is used to test file if accepted, if bin is empty string, no tests of this filetype are made

    # Image
    "x-fmt/392": [True, Bin.MAGICK],  # JP2 (JPEG 2000 part 1)
    "fmt/11": [True, Bin.MAGICK],     # PNG 1.0 / Portable Network Graphics
    "fmt/12": [True, Bin.MAGICK],     # PNG 1.1 / Portable Network Graphics
    "fmt/13": [True, Bin.MAGICK],     # PNG 1.2 / Portable Network Graphics
    "fmt/353": [True, Bin.MAGICK],    # TIFF - Tagged Image File Format
    # sipi converts jpg to jp2 / tif, leave them
    "fmt/42": [True, Bin.MAGICK],     # JPEG File Interchange Format - 1.0
    "fmt/43": [True, Bin.MAGICK],     # JPEG File Interchange Format - 1.01
    "fmt/44": [True, Bin.MAGICK],     # JPEG File Interchange Format - 1.02
    "fmt/1507": [True, Bin.MAGICK],   # Exchangeable Image File Format (Compressed) 2.3.x
    # canon raw
    "fmt/592": [False, Bin.MAGICK, "tif", "", ["fmt/353"]],  # do we reduce the quality on raw files?
    "fmt/593": [False, Bin.MAGICK, "tif", "", ["fmt/353"]],
    # ... TODO there's a lot more, add them step by step
    # svg to tif
    "fmt/91": [False, Bin.MAGICK, "tif", "-density 300", ["fmt/353"]],
    "fmt/92": [False, Bin.MAGICK, "tif", "-density 300", ["fmt/353"]],
    "fmt/413": [False, Bin.MAGICK, "tif", "-density 300", ["fmt/353"]],

    # Audio
    # we currently accept mp3, should we convert them to wav? or m4a (codec aac)
    "fmt/134": [True, Bin.FFMPEG],    # MPEG 1/2 Audio Layer 3 (MP3)
    "fmt/6": [True, Bin.FFMPEG],      # Waveform Audio File Format (WAVE)
    "fmt/141": [True, Bin.FFMPEG],
    "fmt/142": [True, Bin.FFMPEG],
    "fmt/143": [True, Bin.FFMPEG],
    # aif
    "fmt/414": [False, Bin.FFMPEG, "wav", "-codec copy", ["fmt/141", "fmt/142", "fmt/143"]],
    # alac
    "fmt/596": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],
    # aifc
    "x-fmt/136": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],
    # what about flac etc? it's lossless, should we support it or convert to wav?
    # flac
    "fmt/279": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],
    "fmt/947": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],
    # vorbis
    "fmt/203": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],
    # opus
    "fmt/946": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],
    # speex
    "fmt/948": [False, Bin.FFMPEG, "wav", "-c:a pcm_s16le", ["fmt/141", "fmt/142", "fmt/143"]],

    # Video
    # MPEG-4 Media File (Codec: AVC/H.264, Audio: AAC)
    "fmt/199": [True, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # avi
    "fmt/5": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # quicktime
    "x-fmt/384": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # proRes
    "fmt/797": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # MPEG-2 Transport Stream:
    # mostly it contains a h.264 / h.265 videocodec, transcode it anyway or use -codec copy as arg?
    "fmt/585": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # Video Object File (MPEG-2 subset)
    "fmt/425": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # ogg
    "fmt/945": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # ffv1
    # TODO do we archive ffv1 in Matroska Container? use wrappers.Ffmpeg.media_info to determine streams?
    "fmt/569": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # dv
    "x-fmt/152": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # wmv
    "fmt/133": [False, Bin.FFMPEG, "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac", ["fmt/199"]],
    # ... TODO there's a lot more, add them step by step

    # PDF/A recommended as archival format
    "fmt/95": [True, ''],     # Acrobat PDF/A 1a
    "fmt/354": [True, ''],    # Acrobat PDF/A 1b
    "fmt/476": [True, ''],    # Acrobat PDF/A 2a
    "fmt/477": [True, ''],    # Acrobat PDF/A 2b
    "fmt/478": [True, ''],    # Acrobat PDF/A 2u

    # PDF/A other formats TODO do we convert them to recommended format or leave them as they are?
    # there is an implementation to convert to pdf/a 2b:
    # conf.models.LibreOfficePdfSettings / fileidentification.wrappers.wrappers.Converter
    # [False, "soffice", "pdf", "--headless --convert-to", ["fmt/477"]]
    #
    "fmt/479": [True, ''],    # Acrobat PDF/A 3a
    "fmt/480": [True, ''],    # Acrobat PDF/A 3b
    "fmt/481": [True, ''],    # Acrobat PDF/A 3u
    "fmt/1910": [True, ''],   # Acrobat PDF/A 4
    "fmt/1911": [True, ''],   # Acrobat PDF/A 4e
    "fmt/1912": [True, ''],   # Acrobat PDF/A 4f

    # Non PDF/A Pdfs TODO do we convert them to recommended format or leave them as they are?
    "fmt/14": [True, ''],     # Acrobat PDF 1.0
    "fmt/15": [True, ''],     # Acrobat PDF 1.1
    "fmt/16": [True, ''],     # Acrobat PDF 1.2
    "fmt/17": [True, ''],     # Acrobat PDF 1.3
    "fmt/18": [True, ''],     # Acrobat PDF 1.4
    "fmt/19": [True, ''],     # Acrobat PDF 1.5
    "fmt/20": [True, ''],     # Acrobat PDF 1.6
    "fmt/276": [True, ''],    # Acrobat PDF 1.7

    # Office
    "fmt/214": [True, ''],    # Microsoft Excel
    "fmt/189": [True, ''],    # OOXML - Office Open Extensible Markup Language
    "fmt/215": [True, ''],
    "fmt/412": [True, ''],
    "fmt/487": [True, ''],
    "fmt/523": [True, ''],
    "fmt/629": [True, ''],
    "fmt/630": [True, ''],

    # TODO i would recommend to convert them to the x version, as it's then xml based
    # Microsoft Word (doc)
    "fmt/40": [False, Bin.SOFFICE, "docx", "--headless --convert-to", ["fmt/412"]],
    "fmt/609": [False, Bin.SOFFICE, "docx", "--headless --convert-to", ["fmt/412"]],
    "fmt/39": [False, Bin.SOFFICE, "docx", "--headless --convert-to", ["fmt/412"]],
    # Microsoft Powerpoint (ppt)
    "fmt/125": [False, Bin.SOFFICE, "pptx", "--headless --convert-to", ["fmt/215"]],
    "fmt/126": [False, Bin.SOFFICE, "pptx", "--headless --convert-to", ["fmt/215"]],
    "fmt/181": [False, Bin.SOFFICE, "pptx", "--headless --convert-to", ["fmt/215"]],
    # Microsoft Excel (xls)
    "fmt/59": [False, Bin.SOFFICE, "xlsx", "--headless --convert-to", ["fmt/214"]],
    "fmt/61": [False, Bin.SOFFICE, "xlsx", "--headless --convert-to", ["fmt/214"]],
    "fmt/62": [False, Bin.SOFFICE, "xlsx", "--headless --convert-to", ["fmt/214"]],

    # Text
    "x-fmt/14": [True, ''],   # TXT - Plain Text (UTF-8, UTF-16, ISO 8859-1, ISO 8859-15, ASCII)
    "x-fmt/15": [True, ''],
    "x-fmt/16": [True, ''],
    "x-fmt/21": [True, ''],
    "x-fmt/22": [True, ''],
    "x-fmt/111": [True, ''],
    "x-fmt/130": [True, ''],
    "x-fmt/282": [True, ''],
    "x-fmt/62": [True, ''],   # TXT - log file
    "fmt/101": [True, ''],    # XML - eXtensible Markup Language (UTF-8, UTF-16, ISO 8859-1, ISO 8859-15, ASCII)
    "x-fmt/280": [True, ''],  # XML Schema Definition
    "fmt/1474": [True, ''],   # TEI P4 / P5
    "fmt/1475": [True, ''],
    "fmt/1476": [True, ''],
    "fmt/1477": [True, ''],
    "x-fmt/18": [True, ''],   # CSV - Comma Separated Values (UTF-8, UTF-16, ISO 8859-1, ISO 8859-15, ASCII)
    "fmt/817": [True, ''],    # JSON Data Interchange Format

    # Archive
    # we do archive them as they are. should we implement scanning the archives as well and convert files inside?
    "x-fmt/263": [True, ''],   # ZIP Format
    "x-fmt/265": [True, ''],   # Tape Archive Format
    "x-fmt/266": [True, ''],   # GZIP Format
    "fmt/1671": [True, ''],    # Z Compressed Data
    "fmt/484": [True, ''],     # 7Zip format
    # ...
}


@dataclass
class PolicyParams:
    format_name: str = field(default_factory=str)
    bin: str = field(default_factory=str)
    accepted: bool = True
    remove_original: bool = False
    target_container: str = field(default_factory=str)
    processing_args: str = field(default_factory=str)
    expected: list = field(default_factory=list)



class Policies:

    @staticmethod
    def generate(outpath: Path, ba: BasicAnalytics, fmt2ext: dict, strict: bool = False, remove_original: bool = False,
                 blank: bool = False, extend: dict[str, PolicyParams] = None) -> tuple[dict, BasicAnalytics]:

        policies: dict = {}
        jsonfile = f'{outpath}{JsonOutput.POLICIES}'

        # blank caveat
        if blank:
            for puid in ba.puid_unique:
                policies[puid] = asdict(PolicyParams(format_name=fmt2ext[puid]['name']))
            # write out policies with name of the folder, return policies and BasicAnalytics
            with open(jsonfile, 'w') as f:
                json.dump(policies, f, indent=4, ensure_ascii=False)
            return policies, ba

        # default values
        ba.blank = []
        for puid in ba.puid_unique:
            # if it is run in extend mode, add the existing policy if there is any
            if extend and puid in extend:
                policy = extend[puid]
                policies[puid] = policy
            # if there are no default values of this filetype
            elif puid not in default_values:
                if strict:
                    pass  # don't create a blank policies -> files of this type are moved to FAILED
                else:
                    policies[puid] = asdict(PolicyParams(format_name=fmt2ext[puid]['name']))
                    ba.blank.append(puid)
            else:
                # if the filetype is accepted:
                if default_values[puid][0]:
                    policy = {'format_name': fmt2ext[puid]['name'],
                              'bin': default_values[puid][1],
                              'accepted': True}
                    # update policy if it's mp4 -> depends on streams if it's converted
                    if puid in ['fmt/199']:
                        policy.update({'remove_original': remove_original,
                              'target_container': default_values[puid][2],
                              'processing_args': default_values[puid][3],
                              'expected': default_values[puid][4]})
                # if the filety is not accepted
                else:
                    policy = {'format_name': fmt2ext[puid]['name'],
                              'bin': default_values[puid][1],
                              'accepted': False,
                              'remove_original': remove_original,
                              'target_container': default_values[puid][2],
                              'processing_args': default_values[puid][3],
                              'expected': default_values[puid][4]}

                policies[puid] = policy

        # write out the policies with name of the folder, return policies and updated BasicAnalytics
        with open(jsonfile, 'w') as f:
            json.dump(policies, f, indent=4, ensure_ascii=False)
        return policies, ba
