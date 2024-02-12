import random
from multiprocessing import Pool
from pathlib import Path

import matplotlib as mpl
import pandas as pd

from embed import embed
from plot import plot

# What size should the output heat map be (width, height)?
SIZE = (128, 32)

# Where are the payloads stored
PAYLOADS = Path.home() / "workspace" / "payloads"

# How many files should be embedded in the traffic (one flow per file)?
N = 3


def main(infile):
    data = pd.read_feather(infile)
    plot(data, SIZE[0], SIZE[1], False, mpl.colors.LogNorm()
         ).save(infile.name.with_suffix(".png"))

    payloads = [file for file in PAYLOADS.iterdir() if not file.name.startswith(".")]
    # len(payloads) needs to be the same as N
    if len(payloads) > N:
        payloads = random.sample(payloads, N)
    elif len(payloads) < N:
        payloads = random.choices(payloads, k=N)

    embedded_traffic = embed(data, N, payloads)
    plot(embedded_traffic, SIZE[0], SIZE[1], False, mpl.colors.LogNorm()
         ).save(f"emb_{infile.name.with_suffix(".png")}")


if __name__ == "__main__":
    INFILES = Path.home() / "workspace" / "data"
    files = INFILES.glob("*.feather")

    with Pool() as pool:
        pool.map(main, files)
