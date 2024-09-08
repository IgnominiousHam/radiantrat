# RadiantRat

**RadiantRat** is a sophisticated tool designed for mapping device locations based on Wi-Fi signatures. It allows users to visualize and analyze the spatial distribution of devices by capturing and interpreting Wi-Fi signals.

## Features

- **Device Location Mapping:** Map and track the locations of devices using Wi-Fi signals.
- **Data Visualization:** Graphical representation of device locations on a map.
- **Advanced Analysis:** Insights into device movement and signal patterns.

## Getting Started

To get started with RadiantRat, follow these instructions:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/IgnominiousHam/radiantrat.git
   cd radiantrat
   ```

2. **Configure Device:**

   Run ratsetup.sh to configure your device as a node (device doing the detecting) or hub (device seeing and mapping the nodes):

   ```bash
   sudo bash ratsetup.sh
   ```
   The rat currently assumes that Kismet and ssh credentials all match the following format: username = kali, password = kali. If you haven't set up Kismet, be sure to visit port 2501 after starting capture to set the proper credentials. We're working on making this more dynamic.

3. **Start Ratting:**

   If using as hub, run radiantrat.sh.

   ```bash
   python radiantrat.py
   ```
   If using as node, no need to do anything. Ratsetup enables a service, so the required script is already running.

## License

RadiantRat is distributed under a **Closed Source License**. See the [LICENSE](LICENSE) file for details.

## Contributing

As RadiantRat is a closed-source project, contributions are not accepted at this time. If you have any suggestions or feedback, please contact us at [chippyhamilton@gmail.com](mailto:chippyhamilton@gmail.com).

## Contact

For any questions or support, please reach out to [chippyhamilton@gmail.com](mailto:chippyhamilton@gmail.com).

## Acknowledgments

- **Libraries & Tools:** We acknowledge the use of third-party libraries and tools in the development of RadiantRat.
