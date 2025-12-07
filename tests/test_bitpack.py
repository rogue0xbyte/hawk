try:
    from hawk.utils.bitpack import bytes_to_bits, bits_to_bytes
except ModuleNotFoundError:
    import sys
    import os

    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")),
    )
    from hawk.utils.bitpack import bytes_to_bits, bits_to_bytes


def test_bits_bytes_roundtrip():
    b = b"\x01\xfe\x7f"
    bits = bytes_to_bits(b)
    b2 = bits_to_bytes(bits)
    assert b == b2
