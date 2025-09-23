import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from fileidentification.models import BasicAnalytics
from fileidentification.conf.settings import JsonOutput
from fileidentification.policies.default import default_policies


@dataclass
class PolicyParams:
    format_name: str = field(default_factory=str)
    bin: str = field(default_factory=str)
    accepted: bool = True
    target_container: str = field(default_factory=str)
    processing_args: str = field(default_factory=str)
    expected: list[str] = field(default_factory=list)
    remove_original: bool = False


def generate_policies(
    outpath: Path,
    ba: BasicAnalytics,
    fmt2ext: dict[str, Any],
    strict: bool = False,
    remove_original: bool = False,
    blank: bool = False,
    loaded_pol: dict[str, PolicyParams] | None = None,
) -> dict[str, Any]:
    policies: dict[str, Any] = {}
    jsonfile = f"{outpath}{JsonOutput.POLICIES}"

    # blank caveat
    if blank:
        for puid in ba.puid_unique:
            policies[puid] = asdict(PolicyParams(format_name=fmt2ext[puid]["name"]))
        # write out policies with name of the folder, return policies and BasicAnalytics
        with open(jsonfile, "w") as f:
            json.dump(policies, f, indent=4, ensure_ascii=False)
        return policies

    # default values
    ba.blank = []
    for puid in ba.puid_unique:
        # if it is run in extend mode, add the existing policy if there is any
        if loaded_pol and puid in loaded_pol:
            policy = loaded_pol[puid]
            policies[puid] = policy
        elif loaded_pol and strict and puid not in loaded_pol:
            pass  # don't create a blank policies -> files of this type are moved to FAILED
        # if there are no default values of this filetype
        elif puid not in default_policies:
            policies[puid] = asdict(PolicyParams(format_name=fmt2ext[puid]["name"]))
            ba.blank.append(puid)
        else:
            policies[puid] = default_policies[puid]
            if not policies[puid]["accepted"] or puid in ["fmt/199"]:
                policies[puid].update({"remove_original": remove_original})

    # write out the policies with name of the folder, return policies
    with open(jsonfile, "w") as f:
        json.dump(policies, f, indent=4, ensure_ascii=False)
    return policies
