"""带完整性校验的第一版可移植响应库适配器。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np

from eiid.domain import EnergyGrid

from .library import ResponseLibrary, ResponseLibraryMetadata
from .sensitivity import SensitivityBundle, SensitivityKind, SensitivityMap


class PortableNpzJsonResponseStore:
    """JSON manifest + NPZ 数组的版本化交换格式。

    该适配器只负责可靠存储，不决定 Geant4 物理列表、阈值或扫描节点。
    manifest 与 SUCCESS 均在数组完整写入并校验后原子提交。
    """

    FORMAT_ID = "eiid.portable.npz_json.v1"
    MANIFEST_NAME = "response_manifest.json"
    ARRAY_NAME = "response_arrays.npz"
    COMPLETION_NAME = "SUCCESS.json"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _sensitivity_manifest(item: SensitivityMap, prefix: str) -> Dict[str, Any]:
        return {
            "kind": item.kind.value,
            "unit": item.unit,
            "definition": item.definition,
            "metadata": dict(item.metadata),
            "values": prefix + "__values",
            "standard_error": prefix + "__standard_error",
        }

    @staticmethod
    def _load_sensitivity(payload, arrays) -> SensitivityMap:
        return SensitivityMap(
            kind=SensitivityKind(str(payload["kind"])),
            values=arrays[str(payload["values"])],
            standard_error=arrays[str(payload["standard_error"])],
            unit=str(payload["unit"]),
            definition=str(payload["definition"]),
            metadata=dict(payload.get("metadata", {})),
        )

    def save(self, library: ResponseLibrary, directory_value, overwrite: bool = False) -> Path:
        directory = Path(directory_value).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        targets = tuple(
            directory / name
            for name in (self.MANIFEST_NAME, self.ARRAY_NAME, self.COMPLETION_NAME)
        )
        if not overwrite and any(path.exists() for path in targets):
            raise FileExistsError("响应库目标已存在；必须显式允许覆盖。")

        arrays = {"energy_edges_mev": library.energy_grid.edges_mev}
        sensitivity_manifest = {}
        for slot, item in (
            ("conditional", library.sensitivities.conditional),
            ("effective_area", library.sensitivities.effective_area),
            ("finite_distance_emitted", library.sensitivities.finite_distance_emitted),
        ):
            if item is None:
                sensitivity_manifest[slot] = None
                continue
            prefix = "sensitivity__" + slot
            arrays[prefix + "__values"] = item.values
            arrays[prefix + "__standard_error"] = item.standard_error
            sensitivity_manifest[slot] = self._sensitivity_manifest(item, prefix)

        calibration_manifest = {}
        for name, value in library.calibration_arrays.items():
            key = "calibration__" + name
            arrays[key] = value
            calibration_manifest[name] = key

        array_path = directory / self.ARRAY_NAME
        array_tmp = directory / (self.ARRAY_NAME + ".tmp")
        with array_tmp.open("wb") as stream:
            np.savez_compressed(stream, **arrays)
        checksum = self._sha256(array_tmp)
        metadata = library.metadata
        manifest = {
            "format_id": self.FORMAT_ID,
            "format_version": 1,
            "array_file": self.ARRAY_NAME,
            "array_sha256": checksum,
            "metadata": {
                "library_id": metadata.library_id,
                "schema_version": metadata.schema_version,
                "library_status": metadata.library_status,
                "response_model_kind": metadata.response_model_kind,
                "geometry_version": metadata.geometry_version,
                "physics_list": metadata.physics_list,
                "digitizer_version": metadata.digitizer_version,
                "trigger_definition": metadata.trigger_definition,
                "producer_run_id": metadata.producer_run_id,
                "created_utc": metadata.created_utc,
                "attributes": dict(metadata.attributes),
            },
            "energy_grid": {"unit": "MeV", "edges_array": "energy_edges_mev"},
            "sky_grid": dict(library.sky_grid),
            "sensitivity": sensitivity_manifest,
            "calibration_arrays": calibration_manifest,
        }
        manifest_tmp = directory / (self.MANIFEST_NAME + ".tmp")
        with manifest_tmp.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(str(array_tmp), str(array_path))
        os.replace(str(manifest_tmp), str(directory / self.MANIFEST_NAME))
        completion = {
            "status": "success",
            "format_id": self.FORMAT_ID,
            "array_sha256": checksum,
            "library_id": metadata.library_id,
            "library_status": metadata.library_status,
        }
        completion_tmp = directory / (self.COMPLETION_NAME + ".tmp")
        with completion_tmp.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(completion, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(str(completion_tmp), str(directory / self.COMPLETION_NAME))
        return directory / self.MANIFEST_NAME

    def is_complete(self, directory_value) -> bool:
        directory = Path(directory_value).expanduser().resolve()
        try:
            with (directory / self.MANIFEST_NAME).open("r", encoding="utf-8") as stream:
                manifest = json.load(stream)
            with (directory / self.COMPLETION_NAME).open("r", encoding="utf-8") as stream:
                completion = json.load(stream)
            array_path = directory / str(manifest["array_file"])
            checksum = self._sha256(array_path)
            return (
                manifest.get("format_id") == self.FORMAT_ID
                and completion.get("status") == "success"
                and completion.get("format_id") == self.FORMAT_ID
                and checksum == manifest.get("array_sha256")
                and checksum == completion.get("array_sha256")
            )
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False

    def load(self, directory_value) -> ResponseLibrary:
        directory = Path(directory_value).expanduser().resolve()
        if not self.is_complete(directory):
            raise ValueError("响应库不完整或 SHA-256 校验失败。")
        with (directory / self.MANIFEST_NAME).open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
        with np.load(str(directory / manifest["array_file"]), allow_pickle=False) as data:
            arrays = {name: np.asarray(data[name]) for name in data.files}
        sensitivity = manifest["sensitivity"]
        conditional = self._load_sensitivity(sensitivity["conditional"], arrays)
        effective = sensitivity.get("effective_area")
        emitted = sensitivity.get("finite_distance_emitted")
        bundle = SensitivityBundle(
            conditional=conditional,
            effective_area=None if effective is None else self._load_sensitivity(effective, arrays),
            finite_distance_emitted=None if emitted is None else self._load_sensitivity(emitted, arrays),
        )
        raw = manifest["metadata"]
        metadata = ResponseLibraryMetadata(
            library_id=str(raw["library_id"]),
            schema_version=str(raw["schema_version"]),
            library_status=str(raw["library_status"]),
            response_model_kind=str(raw["response_model_kind"]),
            geometry_version=str(raw["geometry_version"]),
            physics_list=str(raw["physics_list"]),
            digitizer_version=str(raw["digitizer_version"]),
            trigger_definition=str(raw["trigger_definition"]),
            producer_run_id=raw.get("producer_run_id"),
            created_utc=raw.get("created_utc"),
            attributes=dict(raw.get("attributes", {})),
        )
        calibration = {
            name: arrays[key]
            for name, key in manifest.get("calibration_arrays", {}).items()
        }
        return ResponseLibrary(
            metadata=metadata,
            energy_grid=EnergyGrid(arrays["energy_edges_mev"]),
            sky_grid=dict(manifest["sky_grid"]),
            sensitivities=bundle,
            calibration_arrays=calibration,
        )


class ResponseStoreFactory:
    """把配置 adapter 名称映射为存储实现，重建器不依赖磁盘格式。"""

    @staticmethod
    def create(adapter: str):
        name = str(adapter).strip()
        if name == "portable_npz_json_v1":
            return PortableNpzJsonResponseStore()
        if name in {"prototype_npz_json", "prototype_npz_json_v1"}:
            from .storage import PrototypeNpzJsonResponseStore

            return PrototypeNpzJsonResponseStore()
        raise ValueError("不支持的响应库 adapter：" + name)
