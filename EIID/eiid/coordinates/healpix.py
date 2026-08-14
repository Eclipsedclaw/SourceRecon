"""HEALPix 天空网格的轻量包装。"""

from __future__ import annotations

import numpy as np

from .healpix_ring import RingHealpixMath


class HealpixSkyGrid:
    """集中管理 nside、ordering 和方向/像素转换。

    构造和像素数计算不要求安装 healpy；真正执行球面索引时才加载它，便于
    基础配置在精简服务器环境中先行校验。
    """

    def __init__(self, nside: int, nested: bool = False):
        self.nside = int(nside)
        self.nested = bool(nested)
        if self.nside <= 0 or self.nside & (self.nside - 1):
            raise ValueError("HEALPix nside 必须是正的 2 的幂。")

    @property
    def pixel_count(self) -> int:
        return int(12 * self.nside * self.nside)

    @staticmethod
    def _healpy():
        try:
            import healpy as hp
        except ImportError as error:
            raise ImportError(
                "执行 HEALPix 方向索引需要 healpy；请安装项目 science 依赖。"
            ) from error
        return hp

    def all_pixel_directions(self) -> np.ndarray:
        """返回全部像素中心；RING ordering 可使用纯 NumPy 后备。"""

        if not self.nested:
            return RingHealpixMath(self.nside).pixels_to_directions(
                np.arange(self.pixel_count)
            )
        hp = self._healpy()
        pixels = np.arange(self.pixel_count)
        return np.column_stack(hp.pix2vec(self.nside, pixels, nest=True))

    def directions_to_pixels(self, directions) -> np.ndarray:
        """批量方向索引；输出形状等于输入去掉最后一个向量维度。"""

        if not self.nested:
            return RingHealpixMath(self.nside).directions_to_pixels(directions)
        vectors = np.asarray(directions, dtype=float)
        if vectors.shape[-1:] != (3,):
            raise ValueError("方向数组最后一维必须为 3。")
        norms = np.linalg.norm(vectors, axis=-1)
        if np.any(norms <= 0.0) or not np.all(np.isfinite(vectors)):
            raise ValueError("方向必须有限且非零。")
        unit = vectors / norms[..., np.newaxis]
        hp = self._healpy()
        return np.asarray(
            hp.vec2pix(
                self.nside,
                unit[..., 0],
                unit[..., 1],
                unit[..., 2],
                nest=True,
            ),
            dtype=np.int64,
        )

    def direction_to_pixel(self, direction) -> int:
        """单位来源方向转 HEALPix 像素。"""

        vector = np.asarray(direction, dtype=float)
        if vector.shape != (3,) or not np.all(np.isfinite(vector)):
            raise ValueError("direction 必须是三个有限数字。")
        norm = float(np.linalg.norm(vector))
        if norm <= 0.0:
            raise ValueError("direction 不能是零向量。")
        vector = vector / norm
        return int(self.directions_to_pixels(vector))

    def pixel_to_direction(self, pixel_index: int) -> np.ndarray:
        """HEALPix 像素中心转单位来源方向。"""

        index = int(pixel_index)
        if index < 0 or index >= self.pixel_count:
            raise IndexError("HEALPix pixel_index 超出范围。")
        if not self.nested:
            return RingHealpixMath(self.nside).pixels_to_directions([index])[0]
        hp = self._healpy()
        return np.asarray(hp.pix2vec(self.nside, index, nest=True), dtype=float)
