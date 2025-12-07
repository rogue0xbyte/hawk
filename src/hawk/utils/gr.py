"""
implements CompressGR and DecompressGR as
pure bit-list functions
ref: Algorithm 6 and 7
"""

import math


def _bits_of_int_le(value, bitlen):
    return [(value >> i) & 1 for i in range(bitlen)]


def _int_from_bits_le(bits):
    v = 0
    for i, b in enumerate(bits):
        v |= (b & 1) << i
    return v


def CompressGR(svec, low, high):
    rng = high - low + 1
    if rng <= 0:
        raise ValueError("invalid low/high")
    bits_per = math.ceil(math.log2(rng))
    out_bits = []
    for v in svec:
        code = abs(v - low)
        out_bits.extend(_bits_of_int_le(code, bits_per))
    return out_bits


def DecompressGR(bits, k, low, high):
    rng = high - low + 1
    if rng <= 0:
        return None
    bits_per = math.ceil(math.log2(rng))
    needed = k * bits_per
    if len(bits) < needed:
        return None
    svec = []
    for i in range(k):
        chunk = bits[i * bits_per : (i + 1) * bits_per]
        code = _int_from_bits_le(chunk)
        v = code + low
        svec.append(v)
    return (svec, needed)
