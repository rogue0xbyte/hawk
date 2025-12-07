"""
samplers: regenerate_fg_bits (shaake256x4 emulation)
and simple samplers
implements Regeneratefg deterministically
using SHAKE256 with interleaving, similar
to SHAKE256x4
also provides a discrete_gaussian_sampler
(toy rejection sampler) and
centred_binomial_from_bits helper
ref: Algorithm 12
"""

import hashlib
from typing import List
import math
import random


def shake256x4(seed: bytes, out_bytes: int) -> bytes:
    res = bytearray()
    per = (out_bytes + 3) // 4
    for j in range(4):
        h = hashlib.shake_256(seed + bytes([j]))
        res_j = h.digest(per)
        res.extend(res_j)
    return bytes(res[:out_bytes])


def regenerate_fg_bits(kgseed: bytes, n: int, eta: int = 4):
    b = n // 64
    out_bits = 2 * b * n
    out_bytes = (out_bits + 7) // 8
    y = shake256x4(kgseed, out_bytes)
    bits = []
    for byte in y:
        for i in range(8):
            bits.append((byte >> i) & 1)
    bits = bits[: 2 * b * n]
    f = []
    g = []
    for i in range(n):
        s = 0
        for j in range(b):
            s += bits[i * b + j]
        f.append(s - b // 2)
    for i in range(n):
        s = 0
        for j in range(b):
            s += bits[(i + n) * b + j]
        g.append(s - b // 2)
    return f, g


def discrete_gaussian_sampler(
    k: int, sigma: float, seed: int = 0
) -> List[int]:
    rnd = random.Random(seed)
    samples = []
    for _ in range(k):
        while True:
            u1 = rnd.random()
            u2 = rnd.random()
            z = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(
                2 * math.pi * u2
            )
            s = int(round(z * sigma))
            samples.append(s)
            break
    return samples


def centred_binomial_from_bits(
    bits: List[int], n: int, eta: int
) -> List[int]:
    if eta <= 0:
        raise ValueError("eta must be > 0")
    need = 2 * eta * n
    if len(bits) < need:
        raise ValueError(f"not enough bits: need {need}, got {len(bits)}")
    out = []
    pos = 0
    for i in range(n):
        a = 0
        b = 0
        for j in range(eta):
            a += bits[pos + j]
        for j in range(eta):
            b += bits[pos + eta + j]
        out.append(a - b)
        pos += 2 * eta
    return out
