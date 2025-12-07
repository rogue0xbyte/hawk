try:
    from hawk.core.keygen import HawkKeyGen
    from hawk.core.sign import HawkSign
    from hawk.core.verify import HawkVerify
except:
    import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from hawk.core.keygen import HawkKeyGen
    from hawk.core.sign import HawkSign
    from hawk.core.verify import HawkVerify


def test_keygen_sign_verify_roundtrip():
    kg = HawkKeyGen(seed=0, param_name="hawk-512")
    pk, sk = kg.generate()
    m = b"unit test message"
    sig = HawkSign(sk, m, seed=0, param_name="hawk-512").sign()
    assert HawkVerify(pk, m, sig, param_name="hawk-512").verify()
