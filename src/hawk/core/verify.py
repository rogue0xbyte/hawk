"""
verification module
implements HawkVerify which decodes
public key, signature and recomputes checks
ref: Algorithm 3
"""

import hashlib
from hawk.utils.bitpack import bytes_to_bits
from hawk.utils.gr import DecompressGR
from hawk.core.hawk import PARAMS


class HawkVerify:
    def __init__(
        self, pk_bytes, message: bytes, sig_bytes, param_name="hawk-512"
    ):
        self.pk = pk_bytes
        self.msg = message
        self.sig = sig_bytes
        self.param = PARAMS[param_name]

    def verify(self):
        bits = bytes_to_bits(self.sig)
        print(len(bits))
        if len(bits) != self.param["siglenbits"]:
            return False
        saltbits = bits[:self.param["saltlenbits"]]
        compbits = bits[self.param["saltlenbits"]:]

        r = DecompressGR(
            compbits,
            self.param["n"],
            self.param["lows1"],
            self.param["highs1"],
        )
        if r is None:
            return False
        s1, consumed = r

        salt_bytes_b = bytes(
            int("".join(str(b) for b in saltbits[i:i + 8][::-1]), 2)
            for i in range(0, len(saltbits), 8)
        )

        hpub = hashlib.shake_256(self.pk).digest(
            self.param["hpublenbits"] // 8
        )
        M = hashlib.shake_256(self.msg + hpub).digest(64)
        h = hashlib.shake_256(M + salt_bytes_b).digest(
            2 * self.param["n"] // 8
        )

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

        for i, sval in enumerate(s1):

            start = i * bits_per
            chunk = h1[start:start + bits_per]
            if len(chunk) < bits_per:
                chunk += [0] * (bits_per - len(chunk))
            val = 0
            for j, b in enumerate(chunk):
                val |= (b & 1) << j
            expected = low + (val % rng)
            if sval != expected:
                return False

        return True
