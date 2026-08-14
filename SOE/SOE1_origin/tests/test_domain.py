"""领域对象的能量守恒与 layer 合并测试。"""

import numpy as np

from soe1.domain import Hit, MeasuredEvent


def _hit(hit_id, layer, energy, position):
    return Hit(
        hit_id=hit_id,
        event_id="event_1",
        channel={0: "ch2", 1: "ch1", 2: "ch0"}[layer],
        layer=layer,
        pixel_id=hit_id,
        position_mm=np.asarray(position, dtype=float),
        energy_mev=energy,
    )


def test_collapsed_by_layer_preserves_total_energy():
    event = MeasuredEvent(
        event_id="event_1",
        hits=[
            _hit("a", 0, 0.10, [0.0, 0.0, 0.0]),
            _hit("b", 2, 0.20, [0.0, 0.0, 10.0]),
            _hit("c", 2, 0.30, [2.0, 0.0, 10.0]),
        ],
    )

    collapsed = event.collapsed_by_layer().ordered("layer")
    assert collapsed.n_hits == 2
    assert np.isclose(
        collapsed.total_deposited_energy_mev,
        event.total_deposited_energy_mev,
    )
    assert np.allclose(
        collapsed.hits[1].position_mm,
        np.array([1.2, 0.0, 10.0]),
    )

