from __future__ import annotations

import numpy as np


class HealpixPixelizer:
    """
    healpy 的小型面向对象包装器。

    SOE 仅依赖 direction_to_pixel、pixel_to_direction 和 pixel_count，
    因而未来可替换其他等立体角像素化而不修改采样器。
    """

    def __init__(self, nside: int, nested: bool = False):
        try:
            import healpy as hp
        except ImportError as exc:
            raise ImportError(
                "球面像素化需要 healpy：pip install healpy"
            ) from exc

        nside = int(nside)
        if not hp.isnsideok(nside):
            raise ValueError("非法 HEALPix nside：" + str(nside))
        self.hp = hp
        self.nside = nside
        self.nested = bool(nested)
        self.pixel_count = int(hp.nside2npix(nside))

    def direction_to_pixel(self, direction: np.ndarray) -> int:
        vector = np.asarray(direction, dtype=float)
        vector = vector / np.linalg.norm(vector)
        return int(
            self.hp.vec2pix(
                self.nside,
                vector[0],
                vector[1],
                vector[2],
                nest=self.nested,
            )
        )

    def pixel_to_direction(self, pixel_index: int) -> np.ndarray:
        x, y, z = self.hp.pix2vec(
            self.nside,
            int(pixel_index),
            nest=self.nested,
        )
        return np.array([x, y, z], dtype=float)

