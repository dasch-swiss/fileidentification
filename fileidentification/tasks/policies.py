from typer import secho, colors

from fileidentification.definitions.models import SfInfo, LogTables, LogMsg, Policies
from fileidentification.definitions.constants import PCMsg
from fileidentification.tasks.os_tasks import remove
from fileidentification.wrappers.ffmpeg import ffmpeg_media_info


def apply_policy(sfinfo: SfInfo, policies: Policies, log_tables: LogTables, strict: bool) -> None:
    puid = sfinfo.processed_as
    if not puid:
        return
    if sfinfo.status.pending:
        return

    if puid not in policies:
        # in strict mode, move file
        if strict:
            sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=f"{PCMsg.NOTINPOLICIES}"))
            remove(sfinfo, log_tables)
            return
        # just flag it as skipped
        sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=f"{PCMsg.SKIPPED}"))
        return

    # case where file needs to be converted
    if not policies[puid].accepted:
        sfinfo.status.pending = True
        return

    # check if mp4 / mkv has correct stream (i.e. h264 and aac)
    if puid in ["fmt/199", "fmt/569"]:
        if not _has_valid_streams(sfinfo, puid):
            sfinfo.status.pending = True
            return


def _has_valid_streams(sfinfo: SfInfo, puid: str) -> bool:
    streams = ffmpeg_media_info(sfinfo.path)
    if not streams:
        secho(f"\t{sfinfo.filename} throwing errors. consider inspection", fg=colors.RED, bold=True)
        return True
    if puid in ["fmt/199"]:
        for stream in streams:
            if stream["codec_name"] not in ["h264", "aac"]:  # type: ignore
                return False
    if puid in ["fmt/569"]:
        for stream in streams:
            if stream["codec_name"] in ["ffv1"]:  # type: ignore
                return True
            return False
    return True
