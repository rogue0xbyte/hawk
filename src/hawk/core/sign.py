"""
signing module
"""

import hashlib
from hawk.utils.bitpack import bits_to_bytes
from hawk.utils.gr import CompressGR
from hawk.core.keygen import HawkKeyGen
from hawk.core.hawk import PARAMS


class HawkSign:
    def __init__(
        self, sk_bytes, message: bytes, seed=0, param_name="hawk-512"
    ):
        self.sk = sk_bytes
        self.message = message
        self.seed = seed
        self.param = PARAMS[param_name]

    def sign(self):

        kg = HawkKeyGen(
            seed=self.seed,
            param_name=(
                self.param["name"] if "name" in self.param else "hawk-512"
            ),
        )
        pk, _ = kg.generate()

        hpub = hashlib.shake_256(pk).digest(self.param["hpublenbits"] // 8)
        M = hashlib.shake_256(self.message + hpub).digest(64)

        saltlen = self.param["saltlenbits"] // 8
        salt = hashlib.shake_256(self.seed.to_bytes(8, "little")).digest(
            saltlen
        )

        h = hashlib.shake_256(M + salt).digest(2 * self.param["n"] // 8)

        h_bits = []
        for b in h:
            for i in range(8):
                h_bits.append((b >> i) & 1)

        h1 = h_bits[self.param["n"]:self.param["n"] * 2]

        low = self.param["lows1"]
        high = self.param["highs1"]
        rng = high - low + 1

        import math

        bits_per = math.ceil(math.log2(rng))
        s1 = []

        for i in range(self.param["n"]):
            start = i * bits_per
            chunk = h1[start:start + bits_per]
            if len(chunk) < bits_per:
                chunk += [0] * (bits_per - len(chunk))
            val = 0
            for j, b in enumerate(chunk):
                val |= (b & 1) << j
            s1.append(low + (val % rng))

        comps = CompressGR(s1, low, high)
        if comps is None:
            raise RuntimeError("CompressGR failed")

        salt_bits = []
        for b in salt:
            for i in range(8):
                salt_bits.append((b >> i) & 1)

        sig_bits = salt_bits + comps

        if len(sig_bits) > self.param["siglenbits"]:
            raise RuntimeError(
                "signature overflow: "
                f"{len(sig_bits)} > {self.param['siglenbits']}"
            )
        while len(sig_bits) < self.param["siglenbits"]:
            sig_bits.append(0)

        sig_bytes = bits_to_bytes(sig_bits)
        return sig_bytes
