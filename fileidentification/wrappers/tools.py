"""
The MediaTool seam: one interface over the external tools (ffmpeg, imagemagick, soffice), so each tool's quirks
(command shape, corruption probe, media info) live with the tool. Resolve one with ``tool_for`` (from a policy's
bin) or ``tool_from_mime`` (from a mimetype); both return None when no tool applies.
"""

import json
import platform
import shlex
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess

from fileidentification.definitions.models import LogMsg, PolicyParams
from fileidentification.definitions.settings import PDFSETTINGS, Bin, LOPath, REencMsg
from fileidentification.wrappers.ffmpeg import ffmpeg_collect_warnings, ffmpeg_media_info
from fileidentification.wrappers.imagemagick import imagemagick_collect_warnings, imagemagick_media_info
from fileidentification.wrappers.sipi import sipi_verify

_SOFFICE = LOPath.Linux if platform.system() == LOPath.Linux.name else LOPath.Darwin


@dataclass
class ProbeResult:
    """
    Outcome of probing a media file with its tool.
    is_corrupt: the file could not be read / played; warnings: the diagnostic output;
    specs: the technical metadata string; needs_reencode: a minor error fixable by re-encoding.
    """

    is_corrupt: bool
    warnings: str
    specs: str
    needs_reencode: bool = False


class MediaTool(ABC):
    """
    An external tool (ffmpeg / imagemagick / soffice) behind a single interface.
    ``bin`` is the executable key used in policies and as the log label for probe output.
    ``serial`` marks a tool that cannot run concurrent instances (the conversion module serializes it).
    """

    bin: str
    serial: bool = False

    def build_command(self, source: Path, args: PolicyParams, target: Path, wdir: Path) -> list[str]:
        """Return the argv that converts ``source`` to ``target`` inside ``wdir`` (probe-only tools don't)."""
        raise NotImplementedError(f"{self.bin} does not convert")  # noqa: EM102

    def read_log(self, result: CompletedProcess[str]) -> str:
        """Return the tool's log output from a finished conversion (stderr by default)."""
        return result.stderr

    def probe(self, path: Path, verbose: bool) -> ProbeResult | None:
        """Probe the file for corruption / warnings. None if this tool does not probe (e.g. soffice)."""
        return None

    def media_info(self, path: Path) -> LogMsg | None:
        """Return the file's technical metadata as a log entry, or None if this tool has none."""
        return None


class Ffmpeg(MediaTool):
    """ffmpeg / ffprobe: audio and video."""

    bin = Bin.FFMPEG

    def build_command(self, source: Path, args: PolicyParams, target: Path, wdir: Path) -> list[str]:
        return ["ffmpeg", "-y", "-i", str(source), *shlex.split(args.processing_args), str(target)]

    def probe(self, path: Path, verbose: bool) -> ProbeResult | None:
        is_corrupt, warnings, specs = ffmpeg_collect_warnings(path, verbose=verbose)
        return ProbeResult(
            is_corrupt=is_corrupt,
            warnings=warnings,
            specs=specs,
            needs_reencode=any(msg in warnings for msg in REencMsg),
        )

    def media_info(self, path: Path) -> LogMsg | None:
        return LogMsg(name="ffmpeg", msg=json.dumps(ffmpeg_media_info(path)))


class Imagemagick(MediaTool):
    """imagemagick (magick / identify): images."""

    bin = Bin.MAGICK

    def build_command(self, source: Path, args: PolicyParams, target: Path, wdir: Path) -> list[str]:
        return ["magick", *shlex.split(args.processing_args), str(source), str(target)]

    def probe(self, path: Path, verbose: bool) -> ProbeResult | None:
        is_corrupt, warnings, specs = imagemagick_collect_warnings(path, verbose=verbose)
        return ProbeResult(is_corrupt=is_corrupt, warnings=warnings, specs=specs)

    def media_info(self, path: Path) -> LogMsg | None:
        return LogMsg(name="imagemagick", msg=imagemagick_media_info(path))


class Soffice(MediaTool):
    """LibreOffice (soffice): office documents. Must run one conversion at a time (serial)."""

    bin = Bin.SOFFICE
    serial = True

    def build_command(self, source: Path, args: PolicyParams, target: Path, wdir: Path) -> list[str]:
        soffice_filter = f"pdf{PDFSETTINGS}" if args.target_container == "pdf" else args.target_container
        return [
            str(_SOFFICE),
            *shlex.split(args.processing_args),
            soffice_filter,
            str(source),
            "--outdir",
            str(wdir),
        ]

    def read_log(self, result: CompletedProcess[str]) -> str:
        # soffice reports on stdout; ffmpeg / magick on stderr
        return result.stdout + result.stderr


class Sipi(MediaTool):
    """sipi: validates DaSCH service files (JP2 / pyramidal TIFF). Probe-only guard — does not convert."""

    bin = Bin.SIPI

    def probe(self, path: Path, verbose: bool) -> ProbeResult | None:
        is_corrupt, warnings = sipi_verify(path)
        return ProbeResult(is_corrupt=is_corrupt, warnings=warnings, specs="")


_TOOLS: dict[str, MediaTool] = {tool.bin: tool for tool in (Ffmpeg(), Imagemagick(), Soffice(), Sipi())}


def tool_for(bin_: str) -> MediaTool | None:
    """Return the MediaTool for a policy's bin value, or None if there is none (empty / unknown)."""
    return _TOOLS.get(bin_)


def tool_from_mime(mime: str) -> MediaTool | None:
    """Pick a probing tool from a mimetype: image -> imagemagick, audio/video -> ffmpeg, else None."""
    top = mime.split("/", maxsplit=1)[0]
    if top == "image":
        return _TOOLS[Bin.MAGICK]
    if top in ("audio", "video"):
        return _TOOLS[Bin.FFMPEG]
    return None
