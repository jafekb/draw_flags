from __future__ import annotations

import hashlib
from typing import Iterable, List

from backend.common.flag_data import Flag, FlagList


def compute_flag_id(flag: Flag) -> str:
    raw_id = f"{flag.wikipedia_page}|{flag.wikipedia_image_url}|{flag.name}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()


class MetadataStore:
    def get_many(self, ids: Iterable[int]) -> List[Flag]:
        raise NotImplementedError


class LocalMetadataStore(MetadataStore):
    def __init__(self, flag_list: FlagList) -> None:
        self._flags = flag_list.flags
        self._stable_ids = [compute_flag_id(flag) for flag in self._flags]

    def get_many(self, ids: Iterable[int]) -> List[Flag]:
        results: List[Flag] = []
        for idx in ids:
            flag = self._flags[idx]
            flag_with_id = flag.model_copy(update={"id": self._stable_ids[idx]})
            results.append(flag_with_id)
        return results
