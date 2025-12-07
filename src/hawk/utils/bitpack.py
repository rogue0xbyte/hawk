"""
bit-level helpers: bytes_to_bits, bits_to_bytes using
little-endian bit order per spec bit-grouping
implements EncodeInt/DecodeInt behaviour for bytes
"""


def bytes_to_bits(b: bytes):
    bits = []
    for byte in b:
        for i in range(7, -1, -1):  # bit 7 → bit 0
            bits.append((byte >> i) & 1)
    return bits


def bits_to_bytes(bits):
    if len(bits) % 8 != 0:
        bits = bits + [0] * (8 - (len(bits) % 8))
    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i + 8]
        byte = 0
        for j, bit in enumerate(chunk):  # j=0 is MSB
            byte = (byte << 1) | (bit & 1)
        out.append(byte)
    return bytes(out)
