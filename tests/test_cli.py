import unittest
import tempfile
import os
try:
    from hawk.cli import demo, gen_keys, sign_message, verify_message, save_key, load_key
except:
    import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from hawk.cli import demo, gen_keys, sign_message, verify_message, save_key, load_key


class Args:
    """Simple args container for CLI functions."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestHawkCLI(unittest.TestCase):
    def test_demo_metrics(self):
        args = Args(seed=0, param="hawk-512")
        results = demo(args)
        # all signed messages should verify correctly
        for r in results[:-1]:
            self.assertTrue(r["ok"])
        # adversary check should fail
        self.assertFalse(results[-1]["ok"])

    def test_gen_keys_and_file_io(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = Args(seed=123, param="hawk-512", outdir=tmpdir)
            gen_keys(args)
            pk_path = os.path.join(tmpdir, "pk.bin")
            sk_path = os.path.join(tmpdir, "sk.bin")
            self.assertTrue(os.path.exists(pk_path))
            self.assertTrue(os.path.exists(sk_path))
            # Keys should load correctly
            pk = load_key(pk_path)
            sk = load_key(sk_path)
            self.assertTrue(len(pk) > 0)
            self.assertTrue(len(sk) > 0)

    def test_sign_and_verify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # generate keys
            args = Args(seed=0, param="hawk-512", outdir=tmpdir)
            gen_keys(args)
            pk_path = os.path.join(tmpdir, "pk.bin")
            sk_path = os.path.join(tmpdir, "sk.bin")

            # create a dummy message
            msg_path = os.path.join(tmpdir, "msg.txt")
            sig_path = os.path.join(tmpdir, "sig.bin")
            message = "hello hawk"
            with open(msg_path, "w") as f:
                f.write(message)

            # sign
            args_sign = Args(skey=sk_path, msg=msg_path, sig=sig_path)
            sign_message(args_sign)
            self.assertTrue(os.path.exists(sig_path))
            self.assertTrue(os.path.getsize(sig_path) > 0)

            # verify
            args_verify = Args(pkey=pk_path, msg=msg_path, sig=sig_path)
            import io, sys
            captured = io.StringIO()
            sys.stdout = captured
            verify_message(args_verify)
            sys.stdout = sys.__stdout__
            X = captured.getvalue()
            print(X)
            self.assertIn("Verification result: True", X)


            tampered_msg = os.path.join(tmpdir, "msg2.txt")
            with open(tampered_msg, "w") as f:
                f.write("tampered")
            args_verify2 = Args(pkey=pk_path, msg=tampered_msg, sig=sig_path)
            captured = io.StringIO()
            sys.stdout = captured
            verify_message(args_verify2)
            sys.stdout = sys.__stdout__
            self.assertIn("Verification result: False", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
