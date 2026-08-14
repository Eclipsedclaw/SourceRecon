"""HEALPix RING ordering 的纯 NumPy 中心坐标与方向索引。"""

from __future__ import annotations

import numpy as np


class RingHealpixMath:
    """不依赖 healpy 的 HEALPix RING 数学后备实现。"""

    def __init__(self, nside: int):
        self.nside = int(nside)
        if self.nside <= 0 or self.nside & (self.nside - 1):
            raise ValueError("HEALPix nside 必须是正的 2 的幂。")
        self.pixel_count = 12 * self.nside * self.nside
        self.north_cap_count = 2 * self.nside * (self.nside - 1)

    def pixels_to_directions(self, pixel_indices) -> np.ndarray:
        """把一维像素索引数组转换成形状 (N,3) 的像素中心方向。"""

        pixels = np.asarray(pixel_indices, dtype=np.int64).reshape(-1)
        if np.any(pixels < 0) or np.any(pixels >= self.pixel_count):
            raise IndexError("HEALPix pixel_index 超出范围。")
        z = np.empty(pixels.size, dtype=float)
        phi = np.empty(pixels.size, dtype=float)
        north = pixels < self.north_cap_count
        south = pixels >= self.pixel_count - self.north_cap_count
        equatorial = ~(north | south)

        if np.any(north):
            one_based = pixels[north] + 1
            ring = np.floor(
                0.5 * (1.0 + np.sqrt(2.0 * one_based - 1.0))
            ).astype(np.int64)
            azimuth_index = one_based - 2 * ring * (ring - 1)
            z[north] = 1.0 - (ring.astype(float) ** 2) / (
                3.0 * self.nside ** 2
            )
            phi[north] = (azimuth_index - 0.5) * np.pi / (2.0 * ring)

        if np.any(equatorial):
            offset = pixels[equatorial] - self.north_cap_count
            ring = offset // (4 * self.nside) + self.nside
            azimuth_index = offset % (4 * self.nside) + 1
            half_shift = 0.5 * (
                1.0 + ((ring + self.nside) & 1).astype(float)
            )
            z[equatorial] = (
                (2 * self.nside - ring) * (2.0 / (3.0 * self.nside))
            )
            phi[equatorial] = (
                (azimuth_index - half_shift) * np.pi / (2.0 * self.nside)
            )

        if np.any(south):
            reversed_one_based = self.pixel_count - pixels[south]
            ring = np.floor(
                0.5 * (1.0 + np.sqrt(2.0 * reversed_one_based - 1.0))
            ).astype(np.int64)
            azimuth_index = (
                4 * ring
                + 1
                - (reversed_one_based - 2 * ring * (ring - 1))
            )
            z[south] = -1.0 + (ring.astype(float) ** 2) / (
                3.0 * self.nside ** 2
            )
            phi[south] = (azimuth_index - 0.5) * np.pi / (2.0 * ring)

        radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
        return np.column_stack(
            (radius * np.cos(phi), radius * np.sin(phi), z)
        )

    def directions_to_pixels(self, directions) -> np.ndarray:
        """把形状 (...,3) 的方向批量映射到 RING 像素索引。"""

        vectors = np.asarray(directions, dtype=float)
        if vectors.shape[-1:] != (3,):
            raise ValueError("方向数组最后一维必须为 3。")
        original_shape = vectors.shape[:-1]
        flat = vectors.reshape(-1, 3)
        if not np.all(np.isfinite(flat)):
            raise ValueError("方向必须全部有限。")
        norms = np.linalg.norm(flat, axis=1)
        if np.any(norms <= 0.0):
            raise ValueError("方向不能包含零向量。")
        unit = flat / norms[:, np.newaxis]
        z = np.clip(unit[:, 2], -1.0, 1.0)
        absolute_z = np.abs(z)
        phi = np.mod(np.arctan2(unit[:, 1], unit[:, 0]), 2.0 * np.pi)
        tt = phi / (0.5 * np.pi)
        pixels = np.empty(flat.shape[0], dtype=np.int64)
        equatorial = absolute_z <= (2.0 / 3.0)

        if np.any(equatorial):
            selected_tt = tt[equatorial]
            selected_z = z[equatorial]
            temp1 = self.nside * (0.5 + selected_tt)
            temp2 = self.nside * (0.75 * selected_z)
            ascending = np.floor(temp1 - temp2).astype(np.int64)
            descending = np.floor(temp1 + temp2).astype(np.int64)
            ring = self.nside + 1 + ascending - descending
            shift = 1 - (ring & 1)
            azimuth = (
                (ascending + descending - self.nside + shift + 1) // 2 + 1
            )
            azimuth = ((azimuth - 1) % (4 * self.nside)) + 1
            pixels[equatorial] = (
                self.north_cap_count
                + (ring - 1) * 4 * self.nside
                + azimuth
                - 1
            )

        polar = ~equatorial
        if np.any(polar):
            selected_tt = tt[polar]
            selected_z = z[polar]
            selected_absolute_z = absolute_z[polar]
            fractional = selected_tt - np.floor(selected_tt)
            radial = self.nside * np.sqrt(
                3.0 * (1.0 - selected_absolute_z)
            )
            ascending = np.floor(fractional * radial).astype(np.int64)
            descending = np.floor((1.0 - fractional) * radial).astype(np.int64)
            ring = ascending + descending + 1
            azimuth = (
                np.floor(selected_tt).astype(np.int64) * ring + ascending + 1
            )
            north_pixels = 2 * ring * (ring - 1) + azimuth - 1
            south_pixels = (
                self.pixel_count - 2 * ring * (ring + 1) + azimuth - 1
            )
            pixels[polar] = np.where(
                selected_z >= 0.0, north_pixels, south_pixels
            )
        return pixels.reshape(original_shape)
