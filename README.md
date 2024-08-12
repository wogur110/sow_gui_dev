# S.O.W Machine

This project is a GUI application for monitoring and controlling a system with sensors and actuators using a Raspberry Pi. It displays real-time data from various sensors and allows the user to control certain parameters through a graphical interface built with PyQt5 and Matplotlib.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [File Descriptions](#file-descriptions)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features
- Real-time data plotting using Matplotlib.
- Adjustable parameters through a graphical interface.
- Data logging to a CSV file.
- User-friendly interface for controlling pumps, chiller, and other parameters.
- Adjustable x-axis scale for real-time graph.

## Requirements
- Python 3.x
- PyQt5
- Matplotlib
- numpy (if not already installed with matplotlib)
- Raspberry Pi with Raspbian or any Debian-based Linux distribution

## Installation

### 1. Update and Upgrade Your System
```sh
sudo apt-get update
sudo apt-get upgrade
```

### 2. Install Necessary Libraries
```sh
sudo apt-get install python3-pyqt5
sudo apt-get install libgl1-mesa-glx libgl1-mesa-dri
sudo apt-get install libglapi-mesa libgles2-mesa
sudo apt-get install mesa-utils
pip3 install matplotlib
```

### 3. Clone the Repository
```sh
git clone <repository_url>
cd <repository_directory>
```

## Usage

### Running the Application
To start the application, run the following command:
```sh
python3 main.py
```

## File Descriptions

### `main.py`
This is the main script that contains the entire application logic including:
- GUI setup using PyQt5
- Real-time data plotting with Matplotlib
- Data logging to CSV
- Control mechanisms for pumps and other parameters

### `sow_machine.jpg`
This image is used as the logo for the application.

## Troubleshooting

### Common Issues

#### libGL Error
If you encounter an error related to `libGL`, such as `libGL error: MESA-LOADER: failed to open swrast`, follow these steps:

1. Ensure all necessary OpenGL libraries are installed:
    ```sh
    sudo apt-get install libgl1-mesa-glx libgl1-mesa-dri
    ```

2. Set environment variables:
    ```sh
    export LIBGL_DRIVERS_PATH=/usr/lib/dri
    export LIBGL_DEBUG=verbose
    ```

3. Reboot the system:
    ```sh
    sudo reboot
    ```

### Checking OpenGL Configuration
To verify your system's OpenGL configuration, install `mesa-utils` and run `glxinfo`:
```sh
sudo apt-get install mesa-utils
glxinfo | grep "OpenGL"
```

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.