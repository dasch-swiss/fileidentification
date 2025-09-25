import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from fileidentification.conf.settings import JsonOutput
from fileidentification.models import BasicAnalytics


class PolicyParams(BaseModel):
    format_name: str = Field(default_factory=str)
    bin: str = Field(default="")
    accepted: bool = Field(default=True)
    target_container: str = Field(default="")
    processing_args: str = Field(default="")
    expected: list[str] = Field(default=[""])
    remove_original: bool = Field(default=False)


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
            policies[puid] = PolicyParams(format_name=fmt2ext[puid]["name"]).model_dump()
        # write out policies with name of the folder, return policies and BasicAnalytics
        with open(jsonfile, "w") as f:
            json.dump(policies, f, indent=4, ensure_ascii=False)
        return policies

    # default values
    default_policies = json.loads(Path("fileidentification/policies/dasch.json").read_text())

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
            policies[puid] = PolicyParams(format_name=fmt2ext[puid]["name"]).model_dump()
            ba.blank.append(puid)
        else:
            policies[puid] = default_policies[puid]
            if not policies[puid]["accepted"] or puid in ["fmt/199"]:
                policies[puid].update({"remove_original": remove_original})

    # write out the policies with name of the folder, return policies
    with open(jsonfile, "w") as f:
        json.dump(policies, f, indent=4, ensure_ascii=False)
    return policies
