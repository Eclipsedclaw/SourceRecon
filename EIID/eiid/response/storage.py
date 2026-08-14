"""明确标注为非正式格式的 NPZ + JSON 响应库适配器。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from eiid.domain import EnergyGrid

from .library import ResponseLibrary, ResponseLibraryMetadata
from .sensitivity import SensitivityBundle, SensitivityKind, SensitivityMap


class PrototypeNpzJsonResponseStore:
    """阶段 3 小规模闭环适配器，不代表正式响应库格式决策。

    JSON manifest 最后原子写入，因而它也充当完成标记；存在孤立 NPZ 时不会
    被误认为完整响应库。
    """

    FORMAT_ID = "eiid.prototype.npz_json.v1"
    MANIFEST_NAME = "manifest.json"
    ARRAY_NAME = "arrays.npz"
    COMPLETION_NAME = "SUCCESS.json"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _map_manifest(item: SensitivityMap, value_key: str, error_key: str) -> Dict[str, Any]:
        return {
            "kind": item.kind.value,
            "unit": item.unit,
            "definition": item.definition,
            "metadata": dict(item.metadata),
            "value_array": value_key,
            "standard_error_array": error_key,
        }

    @staticmethod
    def _map_from_manifest(payload, arrays) -> SensitivityMap:
        return SensitivityMap(
            kind=SensitivityKind(str(payload["kind"])),
            values=arrays[str(payload["value_array"])],
            standard_error=arrays[str(payload["standard_error_array"])],
            unit=str(payload["unit"]),
            definition=str(payload["definition"]),
            metadata=dict(payload.get("metadata", {})),
        )

    def save(
        self,
        library: ResponseLibrary,
        directory_value,
        overwrite: bool = False,
    ) -> Path:
        directory = Path(directory_value).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        manifest_path = directory / self.MANIFEST_NAME
        array_path = directory / self.ARRAY_NAME
        completion_path = directory / self.COMPLETION_NAME
        if not overwrite and (
            manifest_path.exists() or array_path.exists() or completion_path.exists()
        ):
            raise FileExistsError("响应库已存在；只有显式 overwrite 才允许替换。")

        array_payload = {"energy_edges_mev": library.energy_grid.edges_mev}
        sensitivity_manifest = {}
        slots = (
            ("conditional", library.sensitivities.conditional),
            ("effective_area", library.sensitivities.effective_area),
            ("finite_distance_emitted", library.sensitivities.finite_distance_emitted),
        )
        for slot, item in slots:
            if item is None:
                sensitivity_manifest[slot] = None
                continue
            value_key = "sensitivity__" + slot + "__values"
            error_key = "sensitivity__" + slot + "__standard_error"
            array_payload[value_key] = item.values
            array_payload[error_key] = item.standard_error
            sensitivity_manifest[slot] = self._map_manifest(item, value_key, error_key)

        calibration_manifest = {}
        for name, array in library.calibration_arrays.items():
            key = "calibration__" + name
            array_payload[key] = array
            calibration_manifest[name] = key

        temporary_array = directory / (self.ARRAY_NAME + ".tmp")
        with temporary_array.open("wb") as stream:
            np.savez_compressed(stream, **array_payload)

        metadata = library.metadata
        manifest = {
            "format_id": self.FORMAT_ID,
            "format_status": "prototype_not_formal",
            "array_file": self.ARRAY_NAME,
            "array_sha256": self._sha256(temporary_array),
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
            "sky_grid": dict(library.sky_grid),
            "sensitivity": sensitivity_manifest,
            "calibration_arrays": calibration_manifest,
        }
        # 在替换已有数组前验证元数据可序列化；manifest 最后落位并充当完成标记。
        serialized = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        temporary_manifest = directory / (self.MANIFEST_NAME + ".tmp")
        with temporary_manifest.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.write("\n")
        os.replace(str(temporary_array), str(array_path))
        os.replace(str(temporary_manifest), str(manifest_path))
        completion = {
            "status": "success",
            "format_id": self.FORMAT_ID,
            "manifest": self.MANIFEST_NAME,
            "array_sha256": manifest["array_sha256"],
            "producer_run_id": metadata.producer_run_id,
        }
        temporary_completion = directory / (self.COMPLETION_NAME + ".tmp")
        with temporary_completion.open(
            "w", encoding="utf-8", newline="\n"
        ) as stream:
            json.dump(
                completion,
                stream,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            stream.write("\n")
        os.replace(str(temporary_completion), str(completion_path))
        return manifest_path

    def is_complete(self, directory_value) -> bool:
        """检查完成标记、数据文件和 SHA-256，不只检查目录是否存在。"""

        directory = Path(directory_value).expanduser().resolve()
        manifest_path = directory / self.MANIFEST_NAME
        completion_path = directory / self.COMPLETION_NAME
        if not manifest_path.is_file() or not completion_path.is_file():
            return False
        try:
            with manifest_path.open("r", encoding="utf-8") as stream:
                manifest = json.load(stream)
            if manifest.get("format_id") != self.FORMAT_ID:
                return False
            with completion_path.open("r", encoding="utf-8") as stream:
                completion = json.load(stream)
            array_path = directory / str(manifest["array_file"])
            checksum = self._sha256(array_path) if array_path.is_file() else None
            return (
                completion.get("status") == "success"
                and completion.get("format_id") == self.FORMAT_ID
                and checksum == manifest["array_sha256"]
                and completion.get("array_sha256") == manifest["array_sha256"]
            )
        except (KeyError, OSError, ValueError, json.JSONDecodeError):
            return False

    def load(self, directory_value) -> ResponseLibrary:
        directory = Path(directory_value).expanduser().resolve()
        if not self.is_complete(directory):
            raise ValueError("响应库缺少有效 SUCCESS 标记或完整性校验失败。")
        manifest_path = directory / self.MANIFEST_NAME
        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
        if manifest.get("format_id") != self.FORMAT_ID:
            raise ValueError("响应库格式标识不受此原型适配器支持。")
        array_path = directory / str(manifest["array_file"])
        if self._sha256(array_path) != str(manifest["array_sha256"]):
            raise ValueError("响应库数组 SHA-256 校验失败，文件可能不完整或已损坏。")

        with np.load(str(array_path), allow_pickle=False) as loaded:
            arrays = {name: np.asarray(loaded[name]) for name in loaded.files}
        energy_grid = EnergyGrid(np.asarray(arrays["energy_edges_mev"], dtype=float))
        sensitivity = manifest["sensitivity"]
        conditional = self._map_from_manifest(sensitivity["conditional"], arrays)
        effective_payload = sensitivity.get("effective_area")
        emitted_payload = sensitivity.get("finite_distance_emitted")
        bundle = SensitivityBundle(
            conditional=conditional,
            effective_area=(
                None
                if effective_payload is None
                else self._map_from_manifest(effective_payload, arrays)
            ),
            finite_distance_emitted=(
                None
                if emitted_payload is None
                else self._map_from_manifest(emitted_payload, arrays)
            ),
        )
        metadata_payload = manifest["metadata"]
        metadata = ResponseLibraryMetadata(
            library_id=str(metadata_payload["library_id"]),
            schema_version=str(metadata_payload["schema_version"]),
            library_status=str(metadata_payload["library_status"]),
            response_model_kind=str(metadata_payload["response_model_kind"]),
            geometry_version=str(metadata_payload["geometry_version"]),
            physics_list=str(metadata_payload["physics_list"]),
            digitizer_version=str(metadata_payload["digitizer_version"]),
            trigger_definition=str(metadata_payload["trigger_definition"]),
            producer_run_id=metadata_payload.get("producer_run_id"),
            created_utc=metadata_payload.get("created_utc"),
            attributes=dict(metadata_payload.get("attributes", {})),
        )
        calibration = {
            name: arrays[array_key]
            for name, array_key in manifest.get("calibration_arrays", {}).items()
        }
        return ResponseLibrary(
            metadata=metadata,
            energy_grid=energy_grid,
            sky_grid=dict(manifest["sky_grid"]),
            sensitivities=bundle,
            calibration_arrays=calibration,
        )
