# Visualization-based network steganalysis using heat maps

This repository contains scripts and instructions used for generating heat maps to visualize the values of a field in network traffic. A more detailed description of the heat map can be seen in the section below. The heat maps are intended for steganalysis and were inspired by [1, 2].

## Heat Maps
The X-axis of the heat map represents the value of the ID field. The ID field is 16 bits,
which results in 65,536 possible values. To limit the size of the image, I grouped the ID
values in evenly sized bins. Each pixel represents one bin. This image is 128 pixels wide,
displaying 128 groups of 512 values each.

The color shows the number of occurrences of the bin indicated by the X-axis. More
specifically, it is a cumulative count of the number of occurrences. The count gradually
increases as time progresses from the top to the bottom of the heat map, making the color
darker. I also normalized the counts to the 0 − 1 range on the log scale. This made it so
that I could easily translate the counts into colors. I used the logarithmic scale due to the
significant differences in how often individual bins occurred.

The Y-axis represents time. The top of the heat map is the beginning of the traffic
capture, while the bottom is the end. The heat map is 32 bits high, so each bit contains the
packets for approximately 2 seconds because the traffic capture used to generate this heat
map was 60 seconds long.
Altogether, the heat map represents how the distribution of ID values changes over
time. It could show both if and when a covert transmission was embedded in the traffic.

All values referred to above can be customized by modifying the scripts contained in this repository.

## Instructions
### Preparing the Traffic
This section assumes that you have traffic ready in the pcap (or equivalent) format. Otherwise, you may need to perform steps 1-3 differently.
1. Remove any traffic you are not interested in. In my work, this was IPv6 and ICMP traffic.
   Both commands listed below will read all `.pcap` files in the current directory, and save the filtered ones with an underscore prepended to the original name (`_[old_name].pcap`).

   **Using tcpdump (on Linux)**
   ```bash
   for pcap in `ls *.pcap`; do tcpdump -r $pcap -w _$pcap ip and not icmp; done
   ```
   **Using tshark (on Windows)**
   ```pwsh
   foreach ($InFile in Get-ChildItem -Filter *.pcap) { tshark.exe -Y "ip and not icmp" -F pcap -r $InFile.FullName -w "_$($Infile.Name)" }
   ```
3. I recommend splitting the files into even parts, especially if they're large. The command below splits them into one minute segments. The command assumes all the original files are in `.\unsplit\`, and saves all output in `.\split\`.
   ```pwsh
   foreach ($file in gci .\unsplit) {
     editcap -i 60 -F pcap $file .\split\$($file.name)
   }
   ```
4. Export the .pcap to .csv (you can also do this using Scapy if your files aren't too large). This command collects the IPv4 Identification field - adjust as needed.
   ```pwsh
   gci *.pcap | foreach { tshark -o gui.column.format:"SP,%uS,DP,%uD,Time,%t" -t e -T fields -e frame.number -e _ws.col.Time -e ip.src -e ip.dst -e _ws.col.SP -e _ws.col.DP -e ip.proto -e ip.id -E separator="," -E quote=d -r $_ > "$($_.BaseName).csv" }
   ```
   Note: `-o gui.column.format:"SP,%uS,DP,%uD"` adds `_ws.col.SP` and `_ws.col.DP` which contain the source/destination ports irrespective of the protocol (normally I would have to type `tcp.srcport`, `udp.srcport` etc.).
5. Run `csv2feather.py` on the csv files. This will perform additional preprocessing on the data (see the code and comments) and convert it to `.feather`, a faster and more efficient format.

### Further Preprocessing
Embedding the traffic and generating the heat maps can be done using the scripts in the scripts folder of this repo. Specific instructions and an example can be found inside.

## References
1. M. Zuppelli and L. Caviglione, “pcapStego: A Tool for Generating Traffic Traces for Experimenting with Network Covert Channels”, in Proceedings of the 16th International Conference on Availability, Reliability and Security, ser. ARES ’21, New York, NY, SA: Association for Computing Machinery, Aug. 2021, pp. 1–8, ISBN: 978-1-4503-9051-4. DOI:10.1145/3465481.3470067. [Online]. Available: https://doi.org/10.1145/3465481.3470067.

2. M. Repetto, L. Caviglione, and M. Zuppelli, “Bccstego: A Framework for Investigating Network Covert Channels”, in Proceedings of the 16th International Conference on Availability, Reliability and Security, ser. ARES ’21, New York, NY, USA: Association for Computing Machinery, Aug. 2021, pp. 1–7, ISBN: 978-1-4503-9051-4. DOI:10.1145/3465481.3470028. [Online]. Available: https://doi.org/10.1145/3465481.3470028.

