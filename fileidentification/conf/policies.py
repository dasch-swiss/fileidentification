####
# configuration
# accepted: a list of puid of files accepted as they are
# conversions: a dict for puid of files this script does convert them. please pay attention to the pattern.
####

# list of accepted fmts
accepted: list = [

    # Image
    "x-fmt/392",  # JP2 (JPEG 2000 part 1)
    "fmt/11",     # PNG 1.0 / Portable Network Graphics
    "fmt/12",     # PNG 1.1 / Portable Network Graphics
    "fmt/13",     # PNG 1.2 / Portable Network Graphics
    "fmt/353",    # TIFF - Tagged Image File Format
    "fmt/42",     # JPEG File Interchange Format - 1.0
    "fmt/43",     # JPEG File Interchange Format - 1.01
    "fmt/44",     # JPEG File Interchange Format - 1.02

    # Video
    "fmt/199",    # MPEG-4 Media File (Codec: AVC/H.264, Audio: AAC)
    # "fmt/569",  # TODO Do we archive ffv1?

    # Audio
    "fmt/134",    # MPEG 1/2 Audio Layer 3 (MP3)
    "fmt/6",      # Waveform Audio File Format (WAVE)
    "fmt/141",
    "fmt/142",
    "fmt/143",

    # PDF/A
    "fmt/95",     # Acrobat PDF/A 1a
    "fmt/354",    # Acrobat PDF/A 1b
    "fmt/476",    # Acrobat PDF/A 2a
    "fmt/477",    # Acrobat PDF/A 2b
    "fmt/478",    # Acrobat PDF/A 2u
    "fmt/479",    # Acrobat PDF/A 3a
    "fmt/480",    # Acrobat PDF/A 3b
    "fmt/481",    # Acrobat PDF/A 3u
    "fmt/1910",   # Acrobat PDF/A 4
    "fmt/1911",   # Acrobat PDF/A 4e
    "fmt/1912",   # Acrobat PDF/A 4f
    

    # Non PDF/A Pdfs TODO do we convert them to PDF/A or leave them as they are?
    "fmt/14",     # Acrobat PDF 1.0
    "fmt/15",     # Acrobat PDF 1.1
    "fmt/16",     # Acrobat PDF 1.2
    "fmt/17",     # Acrobat PDF 1.3
    "fmt/18",     # Acrobat PDF 1.4
    "fmt/19",     # Acrobat PDF 1.5
    "fmt/20",     # Acrobat PDF 1.6
    "fmt/276",    # Acrobat PDF 1.7

    # Office
    "fmt/214",    # Microsoft Excel
    "fmt/189",    # OOXML - Office Open Extensible Markup Language
    "fmt/215",
    "fmt/412",
    "fmt/487",
    "fmt/523",
    "fmt/629",
    "fmt/630",

    # Text
    "x-fmt/14",   # TXT - Plain Text (UTF-8, UTF-16, ISO 8859-1, ISO 8859-15, ASCII)
    "x-fmt/15",
    "x-fmt/16",
    "x-fmt/21",
    "x-fmt/22",
    "x-fmt/111",
    "x-fmt/130",
    "x-fmt/282",
    "x-fmt/62",   # TXT - log file
    "fmt/101",    # XML - eXtensible Markup Language (UTF-8, UTF-16, ISO 8859-1, ISO 8859-15, ASCII)
    "x-fmt/280",  # XML Schema Definition
    "fmt/1474",   # TEI P4 / P5
    "fmt/1475",
    "fmt/1476",
    "fmt/1477",
    "x-fmt/18",   # CSV - Comma Separated Values (UTF-8, UTF-16, ISO 8859-1, ISO 8859-15, ASCII)

    # Archive
    "x-fmt/263",   # ZIP Format
    "x-fmt/265",   # Tape Archive Format
    "x-fmt/266",   # GZIP Format
    "fmt/1671",    # Z Compressed Data
    "fmt/484",     # 7Zip format
    # ...
]


conversions: dict = {
    ####
    # pattern
    # fmt : [exec, target file container, args]
    ####

    # Audio/Video
    # avi
    "fmt/5": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # quicktime
    "x-fmt/384": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # proRes
    "fmt/797": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # MPEG-2 Transport Stream
    "fmt/585": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # Video Object File (MPEG-2 subset)
    "fmt/425": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # ffv1
    # TODO do we archive ffv1 in Matroska Container? or Matroska Container in general? it can contain a lot of codecs
    "fmt/569": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # dv
    "x-fmt/152": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # wmv
    "fmt/133": ["ffmpeg", "mp4", "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"],
    # ... TODO there's a lot more, add them step by step

    # Images
    # Canon Raw
    "fmt/592": ["convert", "jp2", "-quality 90"],  # do we reduce the quality on raw files?
    # ... TODO there's a lot more, add them step by step

    # Office TODO i would recommend to convert them to the x version, as it's then xml based
    # Microsoft Word (doc)
    "fmt/40": ["soffice", "docx", "--headless --convert-to"],
    "fmt/609": ["soffice", "docx", "--headless --convert-to"],
    "fmt/39": ["soffice", "docx", "--headless --convert-to"],
    # Microsoft Powerpoint (ppt)
    "fmt/125": ["soffice", "pptx", "--headless --convert-to"],
    "fmt/126": ["soffice", "pptx", "--headless --convert-to"],
    "fmt/181": ["soffice", "pptx", "--headless --convert-to"],
    # Microsoft Excel (xls)
    "fmt/59": ["soffice", "xlsx", "--headless --convert-to"],
    "fmt/61": ["soffice", "xlsx", "--headless --convert-to"],
    "fmt/62": ["soffice", "xlsx", "--headless --convert-to"],

}
