#!/usr/bin/env python3

"""
simple cli wrapper to run
demo/keygen/sign/verify
"""

import argparse
import time
import tracemalloc
import json
import os
from hawk.core.keygen import HawkKeyGen
from hawk.core.sign import HawkSign
from hawk.core.verify import HawkVerify


def save_key(path, key_bytes):
    with open(path, "wb") as f:
        f.write(key_bytes)


def load_key(path):
    with open(path, "rb") as f:
        return f.read()


def demo(args):
    start = time.perf_counter()
    tracemalloc.start()
    print("demo: generating keypair (seed=%s)..." % (args.seed,))
    kg = HawkKeyGen(seed=args.seed, param_name=args.param)
    pk, sk = kg.generate()
    t0 = time.perf_counter()
    print("keygen time: %.6fs" % (t0 - start))
    # sign a few messages of varying sizes
    msgs = [b"hello world", b"a" * 64, b"b" * 1024]
    results = []
    for m in msgs:
        t1 = time.perf_counter()
        sig = HawkSign(sk, m, seed=args.seed).sign()
        t2 = time.perf_counter()
        ok = HawkVerify(pk, m, sig).verify()
        results.append(
            {"msglen": len(m), "siglen": len(sig), "time": t2 - t1, "ok": ok}
        )
        print(
            "signed msg len %d -> sig len %d time %.6fs ok=%s"
            % (len(m), len(sig), t2 - t1, ok)
        )
    m = b"adversary"
    ok = HawkVerify(pk, m, sig).verify()
    results.append({"msglen": len(m), "ok": ok})
    print(
        "unsigned msg len %d -> sig len %d time %.6fs ok=%s"
        % (len(m), len(sig), t2 - t1, ok)
    )
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = time.perf_counter() - start
    print(
        "demo done. total time: %.6fs, peak mem: %.2f kiB"
        % (total, peak / 1024)
    )
    print(json.dumps(results, indent=2))
    return results


def gen_keys(args):
    kg = HawkKeyGen(seed=args.seed, param_name=args.param)
    pk, sk = kg.generate()
    os.makedirs(args.outdir, exist_ok=True)
    pk_path = os.path.join(args.outdir, "pk.bin")
    sk_path = os.path.join(args.outdir, "sk.bin")
    save_key(pk_path, pk)
    save_key(sk_path, sk)
    print(f"Keys saved to {args.outdir}")
    print(f"Public key: {pk_path} ({len(pk)} bytes)")
    print(f"Private key: {sk_path} ({len(sk)} bytes)")


def sign_message(args):
    sk = load_key(args.skey)
    with open(args.msg, "rb") as f:
        m = f.read()
    sig = HawkSign(sk, m).sign()
    with open(args.sig, "wb") as f:
        f.write(sig)
    print(f"Message signed. Signature saved to {args.sig} ({len(sig)} bytes)")


def verify_message(args):
    pk = load_key(args.pkey)
    with open(args.msg, "rb") as f:
        m = f.read()
    with open(args.sig, "rb") as f:
        sig = f.read()
    ok = HawkVerify(pk, m, sig).verify()
    print(f"Verification result: {ok}")


def main():
    parser = argparse.ArgumentParser(
        description="hawk demo and key management"
    )
    parser.add_argument(
        "--seed", type=int, default=0, help="deterministic seed for tests"
    )
    parser.add_argument(
        "--param",
        type=str,
        default="hawk-512",
        choices=["hawk-256", "hawk-512", "hawk-1024"],
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("demo")

    gen_parser = sub.add_parser("gen-keys")
    gen_parser.add_argument(
        "--outdir", required=True, help="directory to save keys"
    )

    sign_parser = sub.add_parser("sign")
    sign_parser.add_argument(
        "--skey", required=True, help="path to private key"
    )
    sign_parser.add_argument(
        "--msg", required=True, help="path to message file"
    )
    sign_parser.add_argument(
        "--sig", required=True, help="output path for signature"
    )

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument(
        "--pkey", required=True, help="path to public key"
    )
    verify_parser.add_argument(
        "--msg", required=True, help="path to message file"
    )
    verify_parser.add_argument(
        "--sig", required=True, help="path to signature file"
    )

    args = parser.parse_args()

    if args.command == "demo":
        demo(args)
    elif args.command == "gen-keys":
        gen_keys(args)
    elif args.command == "sign":
        sign_message(args)
    elif args.command == "verify":
        verify_message(args)


if __name__ == "__main__":
    main()
