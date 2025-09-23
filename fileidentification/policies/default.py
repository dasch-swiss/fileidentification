from fileidentification.conf.settings import Bin

###
# puids of system files like .DS_STORE etc.
systemfiles: list[str] = ["fmt/394"]


###
# default policies
default_policies = {
    ####
    # IMAGES PIXELBASED
    "x-fmt/392": {
        "format_name": "JP2 (JPEG 2000 part 1)",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/11": {
        "format_name": "Portable Network Graphics",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/12": {
        "format_name": "Portable Network Graphics",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/13": {
        "format_name": "Portable Network Graphics",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/353": {
        "format_name": "Tagged Image File Format",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    ### lossy compressed
    # sipi converts jpg to jp2 / tif, leave them
    "fmt/42": {
        "format_name": "JPEG File Interchange Format",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/43": {
        "format_name": "JPEG File Interchange Format",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/44": {
        "format_name": "JPEG File Interchange Format",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    "fmt/1507": {
        "format_name": "Exchangeable Image File Format (Compressed)",
        "bin": Bin.MAGICK,
        "accepted": True,
    },
    ###
    # camera raw files
    "fmt/592": {
        "format_name": "Canon RAW",
        "bin": Bin.MAGICK,
        "accepted": False,
        "target_container": "tif",
        "processing_args": Bin.EMPTY,
        "expected": ["fmt/353"],
    },
    "fmt/593": {
        "format_name": "Canon RAW",
        "bin": Bin.MAGICK,
        "accepted": False,
        "target_container": "tif",
        "processing_args": Bin.EMPTY,
        "expected": ["fmt/353"],
    },
    ###
    # SVG
    "fmt/91": {
        "format_name": "Scalable Vector Graphics",
        "bin": Bin.MAGICK,
        "accepted": False,
        "target_container": "tif",
        "processing_args": "-density 300",
        "expected": ["fmt/353"],
    },
    "fmt/92": {
        "format_name": "Scalable Vector Graphics",
        "bin": Bin.MAGICK,
        "accepted": False,
        "target_container": "tif",
        "processing_args": "-density 300",
        "expected": ["fmt/353"],
    },
    "fmt/413": {
        "format_name": "Scalable Vector Graphics Tiny",
        "bin": Bin.MAGICK,
        "accepted": False,
        "target_container": "tif",
        "processing_args": "-density 300",
        "expected": ["fmt/353"],
    },
    ###
    # AUDIO
    # we currently accept mp3, should we convert them to wav? or m4a (codec aac)
    "fmt/134": {
        "format_name": "MPEG 1/2 Audio Layer 3",
        "bin": Bin.FFMPEG,
        "accepted": True,
    },
    # uncompressed
    "fmt/6": {"format_name": "Waveform Audio", "bin": Bin.FFMPEG, "accepted": True},
    "fmt/141": {
        "format_name": "Waveform Audio (PCMWAVEFORMAT)",
        "bin": Bin.FFMPEG,
        "accepted": True,
    },
    "fmt/142": {
        "format_name": "Waveform Audio (WAVEFORMATEX)",
        "bin": Bin.FFMPEG,
        "accepted": True,
    },
    "fmt/143": {
        "format_name": "Waveform Audio (WAVEFORMATEXTENSIBLE)",
        "bin": Bin.FFMPEG,
        "accepted": True,
    },
    # aif -> wav
    "fmt/414": {
        "format_name": "Audio Interchange File Format",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-codec copy",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    # alac -> wav
    "fmt/596": {
        "format_name": "Apple Lossless Audio Codec",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    "x-fmt/136": {
        "format_name": "Audio Interchange File Format (compressed)",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    # what about flac etc? it's lossless, should we support it or convert to wav?
    "fmt/279": {
        "format_name": "FLAC (Free Lossless Audio Codec)",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    "fmt/947": {
        "format_name": "Ogg FLAC Compressed Multimedia File",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    "fmt/203": {
        "format_name": "Ogg Vorbis Codec Compressed Multimedia File",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    "fmt/946": {
        "format_name": "Ogg Opus Codec Compressed Multimedia File",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    "fmt/948": {
        "format_name": "Ogg Speex Codec Multimedia File",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "wav",
        "processing_args": "-c:a pcm_s16le",
        "expected": ["fmt/141", "fmt/142", "fmt/143"],
    },
    ###
    # VIDEO
    # mp4, add processing args because of potential reencoding (Codec: AVC/H.264, Audio: AAC)
    "fmt/199": {
        "format_name": "MPEG-4 Media File",
        "bin": Bin.FFMPEG,
        "accepted": True,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    # avi
    "fmt/5": {
        "format_name": "Audio/Video Interleaved Format",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    # quicktime
    "x-fmt/384": {
        "format_name": "Quicktime",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    "fmt/797": {
        "format_name": "Apple ProRes",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    "fmt/585": {
        "format_name": "MPEG-2 Transport Stream",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    "fmt/425": {
        "format_name": "Video Object File (MPEG-2 subset)",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    "fmt/945": {
        "format_name": "Ogg Theora Video",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    # matroska, ffv1
    # TODO do we archive ffv1 in Matroska Container? use wrappers.Ffmpeg.media_info to determine streams?
    "fmt/569": {
        "format_name": "Matroska",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    "x-fmt/152": {
        "format_name": "Digital Video",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    "fmt/133": {
        "format_name": "Windows Media Video",
        "bin": Bin.FFMPEG,
        "accepted": False,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": ["fmt/199"],
    },
    ###
    # OFFICE
    # PDF/A 1,2 -> recommended as archival format
    "fmt/95": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/354": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/476": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/477": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/478": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    # PDF/A other formats TODO do we convert them to recommended format or leave them as they are?
    # there is an implementation to convert to pdf/a 2b:
    # conf.models.LibreOfficePdfSettings / fileidentification.wrappers.wrappers.Converter
    # [False, Bin.SOFFICE, "pdf", "--headless --convert-to", ["fmt/477"]]
    #
    "fmt/479": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/480": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/481": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1910": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1911": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1912": {
        "format_name": "Acrobat PDF/A - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    # Non PDF/A Pdfs TODO do we convert them to recommended format or leave them as they are?
    "fmt/14": {
        "format_name": "Acrobat PDF 1.0 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/15": {
        "format_name": "Acrobat PDF 1.1 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/16": {
        "format_name": "Acrobat PDF 1.2 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/17": {
        "format_name": "Acrobat PDF 1.3 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/18": {
        "format_name": "Acrobat PDF 1.4 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/19": {
        "format_name": "Acrobat PDF 1.5 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/20": {
        "format_name": "Acrobat PDF 1.6 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/276": {
        "format_name": "Acrobat PDF 1.7 - Portable Document Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    # Office
    # OOXML - Office Open Extensible Markup Language
    "fmt/214": {
        "format_name": "Microsoft Excel for Windows",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/189": {
        "format_name": "Microsoft Office Open XML",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/215": {
        "format_name": "Microsoft Powerpoint for Windows",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/412": {
        "format_name": "Microsoft Word for Windows",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/487": {
        "format_name": "Macro Enabled Microsoft Powerpoint",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/523": {
        "format_name": "Macro enabled Microsoft Word Document OOXML",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/629": {
        "format_name": "Microsoft PowerPoint Show",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/630": {
        "format_name": "Microsoft PowerPoint Macro-Enabled Show",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    # non OOXML
    # convert to equivalent ooxml
    "fmt/40": {
        "format_name": "Microsoft Word Document",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "docx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/412"],
    },
    "fmt/609": {
        "format_name": "Microsoft Word (Generic)",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "docx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/412"],
    },
    "fmt/39": {
        "format_name": "Microsoft Word Document",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "docx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/412"],
    },
    "fmt/125": {
        "format_name": "Microsoft Powerpoint Presentation",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "pptx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/215"],
    },
    "fmt/126": {
        "format_name": "Microsoft Powerpoint Presentation",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "pptx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/215"],
    },
    "fmt/181": {
        "format_name": "Microsoft PowerPoint for Macintosh",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "pptx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/215"],
    },
    "fmt/59": {
        "format_name": "Microsoft Excel 5.0/95 Workbook (xls)",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "xlsx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/214"],
    },
    "fmt/61": {
        "format_name": "Microsoft Excel 97 Workbook (xls)",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "xlsx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/214"],
    },
    "fmt/62": {
        "format_name": "Microsoft Excel 2000-2003 Workbook (xls)",
        "bin": Bin.SOFFICE,
        "accepted": False,
        "target_container": "xlsx",
        "processing_args": "--headless --convert-to",
        "expected": ["fmt/214"],
    },
    ###
    # TEXT
    "x-fmt/14": {
        "format_name": "Macintosh Text File",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/15": {"format_name": "MS-DOS Text File", "bin": Bin.EMPTY, "accepted": True},
    "x-fmt/16": {
        "format_name": "Unicode Text File",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/21": {"format_name": "7-bit ANSI Text", "bin": Bin.EMPTY, "accepted": True},
    "x-fmt/22": {"format_name": "7-bit ASCII Text", "bin": Bin.EMPTY, "accepted": True},
    "x-fmt/111": {"format_name": "Plain Text File", "bin": Bin.EMPTY, "accepted": True},
    "x-fmt/130": {
        "format_name": "MS-DOS Text File with line breaks",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/282": {"format_name": "8-bit ANSI Text", "bin": Bin.EMPTY, "accepted": True},
    "x-fmt/62": {"format_name": "Log File", "bin": Bin.EMPTY, "accepted": True},
    "fmt/101": {
        "format_name": "Extensible Markup Language",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/280": {
        "format_name": "XML Schema Definition",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1474": {
        "format_name": "TEI P4 XML - Single Text File",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1475": {
        "format_name": "TEI P4 XML - Corpus File",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1476": {
        "format_name": "TEI P5 - Single Text File",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/1477": {
        "format_name": "TEI P5 XML - Corpus File",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/18": {
        "format_name": "Comma Separated Values",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/817": {
        "format_name": "JSON Data Interchange Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/263": {"format_name": "ZIP Format", "bin": Bin.EMPTY, "accepted": True},
    "x-fmt/265": {
        "format_name": "Tape Archive Format",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "x-fmt/266": {"format_name": "GZIP Format", "bin": Bin.EMPTY, "accepted": True},
    "fmt/1671": {
        "format_name": "Z Compressed Data",
        "bin": Bin.EMPTY,
        "accepted": True,
    },
    "fmt/484": {"format_name": "7Zip format", "bin": Bin.EMPTY, "accepted": True},
}
