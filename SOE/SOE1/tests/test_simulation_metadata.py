from pathlib import Path

import numpy as np

from soe1.analysis import SimulationMetadataParser


def test_parse_center_dataset_name():
    metadata = SimulationMetadataParser().parse(
        Path("b1output_gamma_0.662MeV_z0.5m_center.root")
    )

    assert metadata.energy_mev == 0.662
    assert metadata.distance_m == 0.5
    assert metadata.position_label == "center"
    assert np.allclose(metadata.expected_direction, [0.0, 0.0, -1.0])
    assert metadata.dataset_slug == "E0p662MeV__z0p5m__center"


def test_parse_positive_horizontal_offset():
    metadata = SimulationMetadataParser(
        source_offset_angle_deg=15.0
    ).parse(Path("b1output_gamma_1.000MeV_z1m_xp.root"))

    expected = np.array(
        [
            np.sin(np.deg2rad(15.0)),
            0.0,
            -np.cos(np.deg2rad(15.0)),
        ]
    )
    assert np.allclose(metadata.expected_direction, expected)
