"""
core hawk utilities & parameter sets.
"""

from dataclasses import dataclass

PARAMS = {
    "hawk-256": {
        "n": 256,
        "eta": 2,
        "saltlenbits": 112,
        "kgseedlenbits": 128,
        "hpublenbits": 128,
        "publenbits": 450,
        "siglenbits": 112 + 256 * 3,
        "lows1": 5,
        "highs1": 9,
        "lows00": 5,
        "high00": 9,
    },
    "hawk-512": {
        "n": 512,
        "eta": 4,
        "saltlenbits": 192,
        "kgseedlenbits": 192,
        "hpublenbits": 256,
        "publenbits": 1024,
        "siglenbits": 192 + 512 * 3,
        "lows1": 5,
        "highs1": 9,
        "lows00": 5,
        "high00": 9,
    },
    "hawk-1024": {
        "n": 1024,
        "eta": 8,
        "saltlenbits": 320,
        "kgseedlenbits": 320,
        "hpublenbits": 512,
        "publenbits": 2440,
        "siglenbits": 320 + 1024 * 3,
        "lows1": 6,
        "highs1": 10,
        "lows00": 6,
        "high00": 10,
    },
}


@dataclass
class Hawk:
    param_name: str = "hawk-512"

    def params(self):
        return PARAMS[self.param_name]
