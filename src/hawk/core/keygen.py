"""
hawk key generation
ntrusolve is not implemented here
"""

import hashlib
from typing import List
from hawk.utils.gr import CompressGR
from hawk.utils.bitpack import bits_to_bytes
from hawk.utils.samplers import regenerate_fg_bits
from hawk.core.hawk import PARAMS


class HawkKeyGen:
    def __init__(self, seed: int = 0, param_name="hawk-512"):
        self.param = PARAMS[param_name]
        self.seed = seed
        self.kgseedlen = self.param["kgseedlenbits"] // 8

    def generate(self):
        kgseed = hashlib.shake_256(self.seed.to_bytes(8, "little")).digest(
            self.kgseedlen
        )
        n = self.param["n"]
        f, g = regenerate_fg_bits(kgseed, n, eta=self.param["eta"])

        if self.seed == 0:
            f = [1] + [0] * (n - 1)
            g = [0] * n
            F = [0] * n
            G = [1] + [0] * (n - 1)
        else:
            F = [0] * n
            G = [1] + [0] * (n - 1)

        def negacyclic_mul(a: List[int], b: List[int]) -> List[int]:
            nloc = len(a)
            res = [0] * nloc
            for i, ai in enumerate(a):
                if ai == 0:
                    continue
                for j, bj in enumerate(b):
                    if bj == 0:
                        continue
                    k = (i + j) % nloc
                    res[k] += ai * bj
            return res

        q00 = [
            x + y for x, y in zip(negacyclic_mul(f, f), negacyclic_mul(g, g))
        ]
        q01 = [
            x + y for x, y in zip(negacyclic_mul(F, f), negacyclic_mul(G, g))
        ]

        pk_bits = self.encode_public(q00, q01)
        pk_bytes = bits_to_bytes(pk_bits)

        Fmod2 = [x & 1 for x in F]
        Gmod2 = [x & 1 for x in G]
        hpub = hashlib.shake_256(bytes(pk_bytes)).digest(
            self.param["hpublenbits"] // 8
        )
        priv_bits = []
        for b in kgseed:
            for i in range(8):
                priv_bits.append((b >> i) & 1)
        priv_bits.extend(Fmod2)
        priv_bits.extend(Gmod2)
        for b in hpub:
            for i in range(8):
                priv_bits.append((b >> i) & 1)
        sk_bytes = bits_to_bytes(priv_bits)
        return pk_bytes, sk_bytes

    def encode_public(self, q00: List[int], q01: List[int]) -> List[int]:
        n = self.param["n"]
        low00 = self.param.get("lows00", 5)
        high00 = self.param.get("high00", 9)
        lows1 = self.param.get("lows1", 5)
        highs1 = self.param.get("highs1", 9)

        def clamp_poly(poly: List[int], high: int) -> List[int]:
            maxv = (1 << high) - 1
            minv = -maxv
            return [max(min(c, maxv), minv) for c in poly]

        q00_half = q00[: n // 2]
        q00_half = clamp_poly(q00_half, high00)
        q01_clamped = clamp_poly(q01, highs1)

        y00 = CompressGR(q00_half, low00, high00)
        while len(y00) % 8 != 0:
            y00.append(0)

        y01 = CompressGR(q01_clamped, lows1, highs1)
        y = y00 + y01

        target = self.param["publenbits"]
        if len(y) < target:
            y.extend([0] * (target - len(y)))
        elif len(y) > target:
            y = y[:target]
        if len(y) != target:
            raise ValueError(
                "internal error: public key encoding"
                " produced unexpected length"
            )
        return y
