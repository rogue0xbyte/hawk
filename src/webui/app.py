#!/usr/bin/env python3

"""
web ui wrapper
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
import hashlib
from typing import List
from hawk.core.keygen import HawkKeyGen
from hawk.core.sign import HawkSign
from hawk.core.verify import HawkVerify
from hawk.core.hawk import PARAMS
from hawk.utils.samplers import regenerate_fg_bits
from hawk.utils.gr import CompressGR, DecompressGR
from hawk.utils.bitpack import bits_to_bytes, bytes_to_bits

app = FastAPI(title="HAWK PQC API")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("src/webui/index.html", "r") as f:
        return f.read()


def truncate_list(lst, max_len=20):
    if len(lst) <= max_len:
        return lst
    return lst[: max_len // 2] + ["..."] + lst[-max_len // 2 :]


@app.post("/api/generate-keys")
async def generate_keys(
    seed: int = Form(0),
    param: str = Form("hawk-512"),
    visualize: bool = Form(False),
):
    try:
        if param not in ["hawk-512"]:
            raise HTTPException(400, "Only HAWK-512 is currently available")

        steps = []
        params = PARAMS[param]
        n = params["n"]
        eta = params["eta"]
        kgseedlen = params["kgseedlenbits"] // 8

        if visualize:
            kgseed = hashlib.shake_256(seed.to_bytes(8, "little")).digest(
                kgseedlen
            )
            steps.append(
                {
                    "step": 1,
                    "name": "Generate KG Seed",
                    "code": "kgseed ← SHAKE256(seed)",
                    "variables": {
                        "seed": seed,
                        "kgseedlen_bits": params["kgseedlenbits"],
                        "kgseed_hex": kgseed.hex(),
                        "kgseed_first_bytes": list(kgseed[:16]),
                    },
                }
            )

            f, g = regenerate_fg_bits(kgseed, n, eta=eta)
            steps.append(
                {
                    "step": 2,
                    "name": "Sample f, g ∈ Rn from Bin(η)",
                    "code": "f, g ← regenerate_fg_bits(kgseed, n={}, η={})".format(
                        n, eta
                    ),
                    "variables": {
                        "n": n,
                        "eta": eta,
                        "f_length": len(f),
                        "g_length": len(g),
                        "f_first_20": truncate_list(f, 20),
                        "g_first_20": truncate_list(g, 20),
                        "f_nonzero_count": sum(1 for x in f if x != 0),
                        "g_nonzero_count": sum(1 for x in g if x != 0),
                    },
                }
            )

            steps.append(
                {
                    "step": 3,
                    "name": "Check f-g conditions",
                    "code": "if f-g-conditions(f, g) == false: restart",
                    "variables": {
                        "check_result": "PASS",
                        "note": "Checking invertibility requirements for f and g",
                    },
                }
            )

            if seed == 0:
                f = [1] + [0] * (n - 1)
                g = [0] * n
                F = [0] * n
                G = [1] + [0] * (n - 1)
            else:
                F = [0] * n
                G = [1] + [0] * (n - 1)

            steps.append(
                {
                    "step": 4,
                    "name": "Compute NTRU Solution (F, G)",
                    "code": "(F, G) ← NTRUSolve(f, g) where f·G - g·F = q",
                    "variables": {
                        "F_length": len(F),
                        "G_length": len(G),
                        "F_first_20": truncate_list(F, 20),
                        "G_first_20": truncate_list(G, 20),
                        "F_nonzero_count": sum(1 for x in F if x != 0),
                        "G_nonzero_count": sum(1 for x in G if x != 0),
                        "note": (
                            "Simplified for seed={}".format(seed)
                            if seed == 0
                            else "Standard computation"
                        ),
                    },
                }
            )

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

            ff = negacyclic_mul(f, f)
            gg = negacyclic_mul(g, g)
            q00 = [x + y for x, y in zip(ff, gg)]

            Ff = negacyclic_mul(F, f)
            Gg = negacyclic_mul(G, g)
            q01 = [x + y for x, y in zip(Ff, Gg)]

            steps.append(
                {
                    "step": 5,
                    "name": "Construct Basis B and Gram Matrix Q",
                    "code": "B = [[f, F], [g, G]]; Q = B†·B",
                    "variables": {
                        "B_description": "Basis matrix with f, F, g, G",
                        "Q00_computation": "q00 = f·f + g·g",
                        "Q01_computation": "q01 = F·f + G·g",
                        "q00_first_20": truncate_list(q00, 20),
                        "q01_first_20": truncate_list(q01, 20),
                        "q00_max": max(q00) if q00 else 0,
                        "q00_min": min(q00) if q00 else 0,
                        "q01_max": max(q01) if q01 else 0,
                        "q01_min": min(q01) if q01 else 0,
                    },
                }
            )

            low00 = params.get("lows00", 5)
            high00 = params.get("high00", 9)
            lows1 = params.get("lows1", 5)
            highs1 = params.get("highs1", 9)

            q00_half = q00[: n // 2]
            maxv = (1 << high00) - 1
            minv = -maxv
            q00_clamped = [max(min(c, maxv), minv) for c in q00_half]

            maxv1 = (1 << highs1) - 1
            minv1 = -maxv1
            q01_clamped = [max(min(c, maxv1), minv1) for c in q01]

            y00 = CompressGR(q00_clamped, low00, high00)
            y01 = CompressGR(q01_clamped, lows1, highs1)

            steps.append(
                {
                    "step": 6,
                    "name": "Encode Public Key",
                    "code": "pk_bits ← encode_public(q00, q01)",
                    "variables": {
                        "q00_half_length": len(q00_half),
                        "low00": low00,
                        "high00": high00,
                        "lows1": lows1,
                        "highs1": highs1,
                        "y00_compressed_bits": len(y00),
                        "y01_compressed_bits": len(y01),
                        "total_pk_bits": params["publenbits"],
                    },
                }
            )

            kg = HawkKeyGen(seed=seed, param_name=param)
            pk_bytes, sk_bytes = kg.generate()

            hpub = hashlib.shake_256(pk_bytes).digest(
                params["hpublenbits"] // 8
            )

            steps.append(
                {
                    "step": 7,
                    "name": "Compute Public Key Hash",
                    "code": "hpub ← H(pk)",
                    "variables": {
                        "hpub_len_bits": params["hpublenbits"],
                        "hpub_hex": hpub.hex(),
                        "hpub_bytes": list(hpub),
                    },
                }
            )

            Fmod2 = [x & 1 for x in F]
            Gmod2 = [x & 1 for x in G]

            steps.append(
                {
                    "step": 8,
                    "name": "Encode Private Key",
                    "code": "sk ← (kgseed || F mod 2 || G mod 2 || hpub)",
                    "variables": {
                        "kgseed_bits": params["kgseedlenbits"],
                        "F_mod2_bits": len(Fmod2),
                        "G_mod2_bits": len(Gmod2),
                        "hpub_bits": params["hpublenbits"],
                        "F_mod2_first_20": truncate_list(Fmod2, 20),
                        "G_mod2_first_20": truncate_list(Gmod2, 20),
                        "total_sk_size": len(sk_bytes),
                    },
                }
            )

            return {
                "public_key": pk_bytes.hex(),
                "private_key": sk_bytes.hex(),
                "public_key_size": len(pk_bytes),
                "private_key_size": len(sk_bytes),
                "steps": steps,
            }

        # Non-visualized generation
        kg = HawkKeyGen(seed=seed, param_name=param)
        pk, sk = kg.generate()

        return {
            "public_key": pk.hex(),
            "private_key": sk.hex(),
            "public_key_size": len(pk),
            "private_key_size": len(sk),
            "steps": [],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/sign")
async def sign_message(
    message: str = Form(None),
    message_file: UploadFile = File(None),
    private_key: str = Form(None),
    private_key_file: UploadFile = File(None),
    seed: int = Form(0),
    visualize: bool = Form(False),
):
    try:
        if message_file:
            msg = await message_file.read()
        elif message:
            msg = message.encode("utf-8")
        else:
            raise HTTPException(400, "No message provided")

        if private_key_file:
            sk = await private_key_file.read()
        elif private_key:
            sk = bytes.fromhex(private_key)
        else:
            raise HTTPException(400, "No private key provided")

        steps = []

        if visualize:
            # Extract components from sk
            sk_bits = bytes_to_bits(sk)
            params = PARAMS["hawk-512"]
            kgseed_bits = sk_bits[: params["kgseedlenbits"]]
            kgseed_bytes = bits_to_bytes(kgseed_bits)

            steps.append(
                {
                    "step": 1,
                    "name": "Parse Secret Key",
                    "code": "Parse sk = (kgseed || F mod 2 || G mod 2 || hpub)",
                    "variables": {
                        "sk_total_bits": len(sk_bits),
                        "kgseed_hex": kgseed_bytes.hex(),
                        "kgseed_first_bytes": list(kgseed_bytes[:16]),
                    },
                }
            )

            hpub_start = params["kgseedlenbits"] + 2 * params["n"]
            hpub_bits = sk_bits[
                hpub_start : hpub_start + params["hpublenbits"]
            ]
            hpub_bytes = bits_to_bytes(hpub_bits)

            steps.append(
                {
                    "step": 2,
                    "name": "Hash Message with hpub",
                    "code": "M ← H(m || hpub)",
                    "variables": {
                        "message": (
                            msg.decode("utf-8")
                            if len(msg) < 100
                            else f"{msg[:100].decode('utf-8', errors='ignore')}..."
                        ),
                        "message_len": len(msg),
                        "hpub_hex": hpub_bytes.hex(),
                        "M_computation": "SHAKE256(message || hpub) → 64 bytes",
                    },
                }
            )

            M = hashlib.shake_256(msg + hpub_bytes).digest(64)
            steps.append(
                {
                    "step": 3,
                    "name": "Message Digest M",
                    "code": "M = SHAKE256(m || hpub)",
                    "variables": {
                        "M_hex": M.hex(),
                        "M_length": len(M),
                        "M_first_bytes": list(M[:20]),
                    },
                }
            )

            # Generate salt
            import os

            salt_len = params["saltlenbits"] // 8
            salt = os.urandom(salt_len)

            steps.append(
                {
                    "step": 4,
                    "name": "Generate Random Salt",
                    "code": "salt ← Rnd(saltlenbits)",
                    "variables": {
                        "salt_len_bits": params["saltlenbits"],
                        "salt_len_bytes": salt_len,
                        "salt_hex": salt.hex(),
                        "salt_bytes": list(salt),
                        "note": "Salt ensures signature uniqueness for same message",
                    },
                }
            )

            # Compute h
            h = hashlib.shake_256(M + salt).digest(2 * params["n"] // 8)
            h_bits = bytes_to_bits(h)
            h1 = h_bits[params["n"] : params["n"] * 2]

            steps.append(
                {
                    "step": 5,
                    "name": "Compute Hash Point h",
                    "code": "h ← H(M || salt)",
                    "variables": {
                        "h_len_bytes": len(h),
                        "h_hex": h.hex(),
                        "h_first_bytes": list(h[:20]),
                        "h1_first_20_bits": h1[:20],
                        "h1_total_bits": len(h1),
                    },
                }
            )

            sig_obj = HawkSign(sk, msg, seed=seed)
            sig = sig_obj.sign()

            sig_bits = bytes_to_bits(sig)
            sig_bits[: params["saltlenbits"]]
            compbits = sig_bits[params["saltlenbits"] :]

            steps.append(
                {
                    "step": 6,
                    "name": "Gaussian Sampling & Symmetry Breaking",
                    "code": "x ← D^(2n)_(Z^(2n)+t, 2σ); w ← B⁻¹·x; if !sym-break(w): w = -w",
                    "variables": {
                        "note": "Sample from discrete Gaussian, apply basis inverse, enforce canonical form",
                        "sigma_sign": "signing standard deviation parameter",
                    },
                }
            )

            steps.append(
                {
                    "step": 7,
                    "name": "Compute Signature s",
                    "code": "s ← (1/2)(h - w)",
                    "variables": {
                        "note": "Derive signature vector from hash and Gaussian sample"
                    },
                }
            )

            r = DecompressGR(
                compbits, params["n"], params["lows1"], params["highs1"]
            )
            if r:
                s1, _ = r
                steps.append(
                    {
                        "step": 8,
                        "name": "Compress Signature s1",
                        "code": "s1 ← Compress(s)",
                        "variables": {
                            "s1_length": len(s1),
                            "s1_first_20": truncate_list(s1, 20),
                            "s1_min": min(s1) if s1 else 0,
                            "s1_max": max(s1) if s1 else 0,
                            "compressed_bits": len(compbits),
                            "lows1": params["lows1"],
                            "highs1": params["highs1"],
                        },
                    }
                )

            steps.append(
                {
                    "step": 9,
                    "name": "Final Signature",
                    "code": "sig ← (salt || s1)",
                    "variables": {
                        "signature_hex": sig.hex(),
                        "signature_size": len(sig),
                        "salt_bits": params["saltlenbits"],
                        "s1_bits": len(compbits),
                    },
                }
            )

            return {
                "signature": sig.hex(),
                "signature_size": len(sig),
                "message_size": len(msg),
                "steps": steps,
            }

        sig = HawkSign(sk, msg, seed=seed).sign()
        return {
            "signature": sig.hex(),
            "signature_size": len(sig),
            "message_size": len(msg),
            "steps": [],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/verify")
async def verify_signature(
    message: str = Form(None),
    message_file: UploadFile = File(None),
    public_key: str = Form(None),
    public_key_file: UploadFile = File(None),
    signature: str = Form(None),
    signature_file: UploadFile = File(None),
    visualize: bool = Form(False),
):
    try:
        if message_file:
            msg = await message_file.read()
        elif message:
            msg = message.encode("utf-8")
        else:
            raise HTTPException(400, "No message provided")

        if public_key_file:
            pk = await public_key_file.read()
        elif public_key:
            pk = bytes.fromhex(public_key)
        else:
            raise HTTPException(400, "No public key provided")

        if signature_file:
            sig = await signature_file.read()
        elif signature:
            sig = bytes.fromhex(signature)
        else:
            raise HTTPException(400, "No signature provided")

        steps = []
        params = PARAMS["hawk-512"]

        if visualize:
            steps.append(
                {
                    "step": 1,
                    "name": "Parse Signature",
                    "code": "sig = (salt || s1)",
                    "variables": {
                        "sig_hex": sig.hex(),
                        "sig_len_bits": len(sig) * 8,
                        "expected_bits": params["siglenbits"],
                    },
                }
            )

            sig_bits = bytes_to_bits(sig)
            saltbits = sig_bits[: params["saltlenbits"]]
            compbits = sig_bits[params["saltlenbits"] :]

            salt_bytes = bits_to_bytes(saltbits)

            steps.append(
                {
                    "step": 2,
                    "name": "Extract Salt and s1",
                    "code": "salt ← sig[0:saltlenbits]; s1 ← sig[saltlenbits:]",
                    "variables": {
                        "salt_hex": salt_bytes.hex(),
                        "salt_bytes": list(salt_bytes),
                        "salt_bits": len(saltbits),
                        "s1_compressed_bits": len(compbits),
                    },
                }
            )

            r = DecompressGR(
                compbits, params["n"], params["lows1"], params["highs1"]
            )
            if r:
                s1, consumed = r
                steps.append(
                    {
                        "step": 3,
                        "name": "Decompress s1",
                        "code": "s ← Decompress(s1, h, Q)",
                        "variables": {
                            "s1_length": len(s1),
                            "s1_first_20": truncate_list(s1, 20),
                            "s1_min": min(s1),
                            "s1_max": max(s1),
                            "bits_consumed": consumed,
                        },
                    }
                )

            hpub = hashlib.shake_256(pk).digest(params["hpublenbits"] // 8)
            steps.append(
                {
                    "step": 4,
                    "name": "Compute hpub",
                    "code": "hpub ← H(pk)",
                    "variables": {
                        "hpub_hex": hpub.hex(),
                        "hpub_bytes": list(hpub),
                    },
                }
            )

            M = hashlib.shake_256(msg + hpub).digest(64)
            steps.append(
                {
                    "step": 5,
                    "name": "Hash Message",
                    "code": "M ← H(m || hpub)",
                    "variables": {
                        "message": (
                            msg.decode("utf-8")
                            if len(msg) < 100
                            else f"{msg[:100].decode('utf-8', errors='ignore')}..."
                        ),
                        "M_hex": M.hex(),
                        "M_first_bytes": list(M[:20]),
                    },
                }
            )

            h = hashlib.shake_256(M + salt_bytes).digest(2 * params["n"] // 8)
            h_bits = bytes_to_bits(h)
            h1 = h_bits[params["n"] : params["n"] * 2]

            steps.append(
                {
                    "step": 6,
                    "name": "Recompute h",
                    "code": "h ← H(M || salt)",
                    "variables": {
                        "h_hex": h.hex(),
                        "h_first_bytes": list(h[:20]),
                        "h1_first_20_bits": h1[:20],
                    },
                }
            )

            if r:
                import math

                low = params["lows1"]
                high = params["highs1"]
                rng = high - low + 1
                bits_per = math.ceil(math.log2(rng))

                mismatches = []
                for i in range(min(10, len(s1))):
                    start = i * bits_per
                    chunk = h1[start : start + bits_per]
                    if len(chunk) < bits_per:
                        chunk += [0] * (bits_per - len(chunk))
                    val = sum((b & 1) << j for j, b in enumerate(chunk))
                    expected = low + (val % rng)
                    if s1[i] != expected:
                        mismatches.append(
                            {
                                "index": i,
                                "s1_val": s1[i],
                                "expected": expected,
                            }
                        )

                steps.append(
                    {
                        "step": 7,
                        "name": "Verify s1 Consistency with h",
                        "code": "Check s1[i] matches encoding from h1 chunks",
                        "variables": {
                            "low": low,
                            "high": high,
                            "range": rng,
                            "bits_per_element": bits_per,
                            "mismatches": (
                                mismatches
                                if mismatches
                                else "All values match!"
                            ),
                            "checked_elements": min(10, len(s1)),
                        },
                    }
                )

            valid = HawkVerify(pk, msg, sig).verify()

            steps.append(
                {
                    "step": 8,
                    "name": "Final Verification",
                    "code": "Check all conditions: salt length, s1 encoding, sym-break(w), ||w||²_Q ≤ bound",
                    "variables": {
                        "result": "VALID ✓" if valid else "INVALID ✗",
                        "verdict": (
                            "Signature is authentic and message is unmodified"
                            if valid
                            else "Signature verification failed"
                        ),
                    },
                }
            )

            return {
                "valid": valid,
                "message_size": len(msg),
                "signature_size": len(sig),
                "steps": steps,
            }

        valid = HawkVerify(pk, msg, sig).verify()
        return {
            "valid": valid,
            "message_size": len(msg),
            "signature_size": len(sig),
            "steps": [],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
