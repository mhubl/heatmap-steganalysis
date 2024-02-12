from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
from PIL import Image

INTERVAL_SECONDS = 60 # how long is the capture file supposed to be


def calculate_colors(bins, norm):
    # Calculate the running count for each bin, then scale to [0, 1]
    maxbin = bins.value_counts().max()
    bin_partials = defaultdict(int)
    colors = []
    for packet in bins.values:
        bin_partials[packet] += 1
        colors.append(bin_partials[packet] / maxbin)
    colors = np.asarray(colors)

    if norm is not None:
        colors = norm(colors)

    return 255 * (1 - colors)


def draw_plot(x_res, y_res, bins, times, colors):
    # Scale the time to make the data fit the y axis
    times = times // (INTERVAL_SECONDS / y_res)

    # Invert the plot: we want 0 to be at the top, not at the bottom.
    times = np.abs(times - y_res).astype("uint16")

    # Create and fill the canvas
    canvas = np.full((y_res, x_res), 255, dtype=np.uint8)
    for (value, time, color) in zip(bins.values, times, colors):
        # Draw a bar from the current time to the top of the plot
        for row in range(time-1, y_res):
            canvas[row, value] = color

    # Create the image from the canvas
    return Image.fromarray(canvas, mode="L")


def apply_filter(pcap):
    """Removes specific values of ID from the packet capture"""
    return pcap[pcap.id > 30]


def plot(pcap, x_resolution, y_resolution, do_filter, norm=None):
    field = "id"

    if do_filter:
        pcap = apply_filter(pcap)

    pcap = pcap[["time", field]].sort_values("time", ascending=False).reset_index(drop=True)
    timedelta = pcap.time - pcap.time.min()

    bins = pd.cut(pcap.loc[:, field], x_resolution, retbins=False, labels=False).astype("uint16")

    colors = calculate_colors(bins, norm)

    return draw_plot(x_resolution, y_resolution, bins, timedelta, colors)


if __name__ == "__main__":
    INFILE = Path().home() / "workspace" / "data" / "file.feather"
    OUTFILE = Path().home() / "workspace" / "heatmaps" / "heatmap.png"
    SIZE = (128, 32)

    data = pd.read_feather(INFILE)
    # param do_filter (after size) controls if apply_filter() is called before plotting
    plot(data, SIZE[0], SIZE[1], False, norm=mpl.colors.LogNorm()).save(OUTFILE)
