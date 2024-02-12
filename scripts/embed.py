import random
import sys
from collections import namedtuple
from pathlib import Path

import pandas as pd

# Check if the extracted data matches the embedded data
VALIDATE = True


def get_flows(bytesize: int, traffic: pd.DataFrame, bytes_per_packet: int = 2) -> list:
    """Returns a sorted list of flows that can be used to embed data into the pcap.

    Each flow is identified by a tuple of (src, dst, sport, dport, proto).
    The flows are sorted by the number of packets, ascending."""
    flow_key = ["srcaddr", "dstaddr", "srcport", "dstport", "proto"]
    counts = traffic.groupby(flow_key).agg("size")
    counts = counts[counts * bytes_per_packet >= bytesize]
    if len(counts) == 0:
        raise ValueError(f"No flows found that can hold the given data ({bytesize} bytes)")
    Flow = namedtuple("Flow", flow_key)
    return [Flow(*counts.index[i]) for i in range(len(counts))]


def get_data_chunks(data: bytes, chunk_size: int = 2) -> list:
    """Returns a list of chunks of the given size from the given data."""
    while len(data) % chunk_size != 0:
        data += b"\x00"
    return [
        int.from_bytes(data[i:i + chunk_size], byteorder="big")
        for i in range(0, len(data), chunk_size)
    ]


def embed_flow(data: bytes, flow: namedtuple, traffic: pd.DataFrame) -> pd.DataFrame:
    """Embeds the data into the given flow in the traffic, then returns the new traffic."""
    data = get_data_chunks(data)
    index = []
    # Iter over all packets looking for ones matching the flow
    for row in traffic.itertuples():
        if (row.srcaddr == flow.srcaddr and row.dstaddr == flow.dstaddr and
                row.srcport == flow.srcport and row.dstport == flow.dstport and
                row.proto == flow.proto):
            # Save the index of the matching flow
            index.append(row.Index)
            # Break if we have enough indexes for all the data
            if len(index) >= len(data):
                break

    # Save data using the indexes (much faster than saving individually in the loop)
    traffic.loc[index, "id"] = data
    traffic.loc[:, "id"] = traffic.loc[:, "id"].astype("uint32")
    return traffic


def extract(datasize: int, flow: namedtuple, traffic: pd.DataFrame) -> bytes:
    """Extracts the data from the given flow in the traffic, then returns the data."""
    data = b""
    for row in traffic.itertuples():
        if (row.srcaddr == flow.srcaddr and row.dstaddr == flow.dstaddr and
                row.srcport == flow.srcport and row.dstport == flow.dstport and
                row.proto == flow.proto):
            data += int.to_bytes(row.id, byteorder="big", length=2)
            if len(data) >= datasize:
                break
    return data


def pick_files(files, flows):
    """Creates a list of payload files to embed"""
    if len(files) > flows:
        return random.sample(files, flows)
    elif len(files) < flows:
        return random.choices(files, k=flows)
    else:
        return files


def embed(traffic: pd.DataFrame, flows: int, files: list) -> pd.DataFrame:
    flows_used = []
    for i in range(flows):
        # len(files) is guaranteed to == len(flows) here
        data = files[i].read_bytes()
        flows = get_flows(len(data), traffic)
        while True:
            flow = random.choice(flows)
            if flow not in flows_used:
                flows_used.append(flow)
                break
            flows.remove(flow)
        traffic = embed_flow(data, flow, traffic)

        if VALIDATE:
            # Trailing null bytes may have been added as padding to fill chunk_size
            extracted = extract(len(data), flow, traffic).rstrip(b"\x00")
            if extracted != data.rstrip(b"\x00"):
                raise ValueError("Data was not extracted correctly.")

    return traffic


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 embed.py <num_flows> <traffic as .feather> <files [files...]>")
        sys.exit(1)

    flows = int(sys.argv[1])
    infile = Path(sys.argv[2])
    traffic = pd.read_feather(infile)
    all_files = [Path(file) for file in sys.argv[3:]]

    for file in all_files:
        if not file.exists() or not file.is_file():
            raise OSError(f"File {file} does not exist or is not a file.")
    files = pick_files(all_files, flows)

    # If no flows are long enough for one of the files keep rerolling until it works
    # If the number of files == the number of flows to embed, rerolling will not work
    # Also limit attempts to 10
    attempts = 10
    while True:
        try:
            traffic = embed(traffic, flows, files)
            break
        except ValueError as e:
            print(e)
            if len(all_files) == flows or attempts <= 0:
                print("Failed to find appropriate flows/files")
                sys.exit(1)
            files = pick_files(all_files, flows)
            attempts -= 1

    outfile = infile.parent / (f"i{flows}_" + infile.name)
    traffic.to_feather(outfile)
