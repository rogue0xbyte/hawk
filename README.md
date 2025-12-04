# **HAWK**

This repository aims to research on post-quantum cryptography "HAWK" signature scheme.
This re-implements the scheme as described [here](https://hawk-sign.info/hawk-spec.pdf) in Python, and
attempts to find vulnerabilities in the same.


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