"""
fft and invfft utilities.
we implement float-based numpy fft
spec prefers integer-friendly transforms
(ntt) in optimized implementations
implementing a correct integer negacyclic ntt
requires careful modular arithmetic
and choice of moduli. for prototype and
testing we use numpy.fft with rounding
to integers where needed and test invertibility
ref: section 2 (number fields & transforms)
"""

import numpy as np


def FFT(poly):
    return np.fft.fft(poly)


def InvFFT(spectrum):
    res = np.fft.ifft(spectrum)
    return [int(round(x.real)) for x in res]
