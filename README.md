# **HAWK**

This repository aims to research on post-quantum cryptography "HAWK" signature scheme.
This re-implements a toy version of the scheme as described [here](https://hawk-sign.info/hawk-spec.pdf) in Python.

> **⚠️ Note**: This is a basic prototype. Don't use it for anything production.
> Only HAWK-512 is functional and tested in this version.

## 
**Motivation**

HAWK is a signature scheme inspired by the introduction of the lattice isomorphism
problem (LIP). In particular, the distribution used to sample private keys in HAWK is
simplified compared to that in HAWK-AC22.

## 
**Prior Work**

*   [HAWK v1.1](https://hawk-sign.info/hawk-spec.pdf)
*	[hawk-py](https://github.com/hawk-sign/hawk-py)
*	[lil-hawk-py](https://github.com/mjosaarinen/lil-hawk-py) 

##
**Quick Start**

### Prerequisites

- Python 3.13+
- Poetry (for dependency management)

### Installation

1. **Clone the repository**:

   ```bash
   git clone git@github.com:rogue0xbyte/hawk.git
   cd hawk
   ```

2. **Install dependencies**:

   ```bash
   poetry install
   ```

3. **Activate the virtual environment**:

   ```bash
   eval $(poetry env activate)
   ```

### Usage

**To run a demo script**:
```bash
poetry run hawk demo --seed 0 --param hawk-512
```

**To generate re-usable keys and run**:
```bash
# generate keys
mkdir demo; poetry run hawk gen-keys --outdir ./demo/keys/
# write message
echo "<your message>" > demo/msg.txt
# sign
poetry run hawk sign --skey ./demo/keys/sk.bin --msg demo/msg.txt --sig demo/sig.bin
# verify
poetry run hawk verify --skey ./demo/keys/pk.bin --msg demo/msg.txt --sig demo/sig.bin
# write faux message
echo "tamper/faux message" > demo/faux.txt
# verify
poetry run hawk verify --skey ./demo/keys/pk.bin --msg demo/faux.txt --sig demo/sig.bin
```

## License

Licensed under the Apache License 2.0. See `LICENSE` file for details.

## Security

This project deals with sensitive data processing. Please review the security considerations in `SECURITY.md`
before using in any production-like environment.