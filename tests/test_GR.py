try:
    from hawk.utils.gr import CompressGR, DecompressGR
except ModuleNotFoundError:
    import sys
    import os

    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")),
    )
    from hawk.utils.gr import CompressGR, DecompressGR


def test_gr_roundtrip_basic():
    x = [0, 1, -1, 5, -3, 7, 2, -8]
    low = 3
    high = 7
    bits = CompressGR(x, low, high)
    res = DecompressGR(bits, len(x), low, high)
    assert res is not None
