from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np


@dataclass(frozen=True)
class SimulationMetadata:
    """从批量模拟文件名解析出的已知条件，只用于评估，不进入重建。"""

    source_path: str
    file_name: str
    dataset_slug: str
    energy_mev: float
    distance_m: float
    position_label: str
    source_offset_angle_deg: float
    expected_direction_x: float
    expected_direction_y: float
    expected_direction_z: float
    generated_event_count: Optional[int] = None

    @property
    def expected_direction(self) -> np.ndarray:
        vector = np.array(
            [
                self.expected_direction_x,
                self.expected_direction_y,
                self.expected_direction_z,
            ],
            dtype=float,
        )
        return vector / np.linalg.norm(vector)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class SimulationMetadataParser:
    """
    解析 jcding 批量模拟的文件名。

    默认支持：
        b1output_gamma_0.662MeV_z0.5m_center.root
        b1output_gamma_1.000MeV_z1m_xp.root
    """

    DEFAULT_PATTERN = (
        r"^b1output_gamma_"
        r"(?P<energy>[0-9]+(?:\.[0-9]+)?)MeV_"
        r"z(?P<distance>[0-9]+(?:\.[0-9]+)?)m_"
        r"(?P<position>center|xp|xm|yp|ym)\.root$"
    )

    def __init__(
        self,
        source_offset_angle_deg: float = 15.0,
        file_name_pattern: str = None,
        center_direction=None,
        horizontal_axis=None,
        vertical_axis=None,
        generated_event_count=None,
    ):
        self.source_offset_angle_deg = float(source_offset_angle_deg)
        self.center_direction = self._unit_vector(
            center_direction or [0.0, 0.0, -1.0],
            "center_direction",
        )
        self.horizontal_axis = self._transverse_unit_vector(
            horizontal_axis or [-1.0, 0.0, 0.0],
            "horizontal_axis",
        )
        self.vertical_axis = self._transverse_unit_vector(
            vertical_axis or [0.0, -1.0, 0.0],
            "vertical_axis",
        )
        self.generated_event_count = (
            None
            if generated_event_count is None
            else int(generated_event_count)
        )
        self.pattern = re.compile(
            file_name_pattern or self.DEFAULT_PATTERN,
            flags=re.IGNORECASE,
        )

    def parse(self, path: Path) -> SimulationMetadata:
        match = self.pattern.match(path.name)
        if match is None:
            raise ValueError("无法解析模拟文件名：" + path.name)

        energy = float(match.group("energy"))
        distance = float(match.group("distance"))
        position = match.group("position").lower()
        direction = self._expected_direction(position)
        slug = self._slug(energy, distance, position)
        return SimulationMetadata(
            source_path=str(path.resolve()),
            file_name=path.name,
            dataset_slug=slug,
            energy_mev=energy,
            distance_m=distance,
            position_label=position,
            source_offset_angle_deg=self.source_offset_angle_deg,
            expected_direction_x=float(direction[0]),
            expected_direction_y=float(direction[1]),
            expected_direction_z=float(direction[2]),
            generated_event_count=self.generated_event_count,
        )

    def _expected_direction(self, position: str) -> np.ndarray:
        angle = np.deg2rad(self.source_offset_angle_deg)
        mapping = {
            "center": self.center_direction,
            "xp": (
                np.cos(angle) * self.center_direction
                + np.sin(angle) * self.horizontal_axis
            ),
            "xm": (
                np.cos(angle) * self.center_direction
                - np.sin(angle) * self.horizontal_axis
            ),
            "yp": (
                np.cos(angle) * self.center_direction
                + np.sin(angle) * self.vertical_axis
            ),
            "ym": (
                np.cos(angle) * self.center_direction
                - np.sin(angle) * self.vertical_axis
            ),
        }
        if position not in mapping:
            raise ValueError("未知位置标签：" + position)
        return mapping[position] / np.linalg.norm(mapping[position])

    @staticmethod
    def _unit_vector(value, label) -> np.ndarray:
        vector = np.asarray(value, dtype=float)
        if vector.shape != (3,) or not np.all(np.isfinite(vector)):
            raise ValueError(label + " 必须是三个有限数字。")
        norm = np.linalg.norm(vector)
        if norm <= 0.0:
            raise ValueError(label + " 不能是零向量。")
        return vector / norm

    def _transverse_unit_vector(self, value, label) -> np.ndarray:
        vector = self._unit_vector(value, label)
        vector = vector - np.dot(
            vector, self.center_direction
        ) * self.center_direction
        norm = np.linalg.norm(vector)
        if norm <= 1e-12:
            raise ValueError(label + " 不能与 center_direction 平行。")
        return vector / norm

    @staticmethod
    def _slug(energy: float, distance: float, position: str) -> str:
        energy_text = f"{energy:.3f}".replace(".", "p")
        distance_text = (
            f"{distance:g}".replace(".", "p")
        )
        return (
            "E"
            + energy_text
            + "MeV__z"
            + distance_text
            + "m__"
            + position
        )
