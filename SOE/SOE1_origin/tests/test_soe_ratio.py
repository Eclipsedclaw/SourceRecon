"""SOE count ratio 的边界和对称性测试。"""

import numpy as np

from soe1.reconstruction.sampler import SphericalSoeSampler


def test_move_between_equally_occupied_pixels_has_unit_ratio():
    value = SphericalSoeSampler._log_soe_count_ratio(
        old_count=3,
        new_count=2,
    )
    assert np.isclose(value, 0.0)


def test_move_out_of_singleton_pixel_is_finite():
    value = SphericalSoeSampler._log_soe_count_ratio(
        old_count=1,
        new_count=0,
    )
    assert np.isfinite(value)
