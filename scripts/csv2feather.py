import sys
from pathlib import Path

import pandas as pd


def preprocess(df):
    # Skip files that are too short (<58 seconds) as a result of the split
    if df.time.max() - df.time.min() < 58:
        print("Path too short, skipping")
        sys.exit()

    # Handle IP within IP: RFC2003.
    # For simplicity, I discard the encapsulating packet(s) and keep the encapsulated one
    if df.proto.dtype == "object":
        indices = df.proto.str.startswith("4").fillna(False)
        if indices.any():
            df.loc[indices, "proto"] = df.proto.loc[indices].apply(lambda x: x.split(",")[-1])
            df.loc[indices, "id"] = df.id.loc[indices].apply(lambda x: x.split(",")[-1])
            df.loc[indices, "srcaddr"] = df.srcaddr.loc[indices].apply(lambda x: x.split(",")[-1])
            df.loc[indices, "dstaddr"] = df.dstaddr.loc[indices].apply(lambda x: x.split(",")[-1])
        indices = None

    # Convert dtypes and fill empty ports with 0 (avoid NaNs)
    df["id"] = df["id"].astype(str).apply(int, args=(16,)).astype('uint32')
    df["proto"] = df["proto"].astype('uint16')
    df["srcport"] = df["srcport"].fillna(0).astype('uint16')
    df["dstport"] = df["dstport"].fillna(0).astype('uint16')

    # Remove all flows with 64 or less packets
    # (64 packets x 2 bytes = only up to 128 bytes of hidden transmission)
    # If you want to skip this step comment lines 33 and 34
    df = df.groupby(['srcaddr', 'dstaddr', 'srcport', 'dstport',
                     'proto']).filter(lambda x: len(x) >= 64)

    df = df.sort_values("time").reset_index(drop=True)
    return df


if __name__ == "__main__":
    path = Path(sys.argv[1])
    df = pd.read_csv(path.resolve(),
                     sep=",",
                     header=None,
                     encoding="utf-8",
                     index_col=0,
                     names=["time", "srcaddr", "dstaddr", "srcport", "dstport", "proto", "id"],
                     low_memory=False)
    df = preprocess(df)
    df.to_feather(path.with_suffix(".feather"))
