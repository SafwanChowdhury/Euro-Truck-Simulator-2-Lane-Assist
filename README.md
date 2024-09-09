![](assets/markdownLogo.png)

# Multi-Agent Platooning using Gaussian Belief Propagation

## Contents

- [Multi-Agent Platooning using Gaussian Belief Propagation](#multi-agent-platooning-using-gaussian-belief-propagation)
  - [Contents](#contents)
  - [GBPPlanner for Multi-Agent Platooning](#gbpplanner-for-multi-agent-platooning)
    - [Initial Setup](#initial-setup)
    - [Run examples](#run-examples)
      - [During simulation](#during-simulation)
    - [Play with the code](#play-with-the-code)
      - [Own formations](#own-formations)
      - [Custom Obstacles](#custom-obstacles)
    - [Cite the original paper](#cite-the-original-paper)
  - [GBPPlanner for ETS2LA](#gbpplanner-for-ets2la)
    - [Initial Setup](#initial-setup-1)
    - [Run examples](#run-examples-1)
    - [Adding External Trucks](#adding-external-trucks)
      - [During simulation](#during-simulation-1)
    - [Play with the code](#play-with-the-code-1)
      - [Custom Obstacles](#custom-obstacles-1)
  - [Euro Truck Simulator 2 Lane Assist](#euro-truck-simulator-2-lane-assist)
    - [Installer](#installer)
    - [Initial Setup](#initial-setup-2)
    - [Game Setup](#game-setup)
    - [ETS2LA Setup](#ets2la-setup)
    - [Links](#links)


## GBPPlanner for Multi-Agent Platooning
This project builds upon the GBPPlanner framework discussed in the the 2023 Robotics Automation Letters (RA-L) paper. It was also presented at ICRA 2023 (Oral).

Original Project page: https://aalpatya.github.io/gbpplanner

<p align="center">
  <img src="https://github.com/aalpatya/gbpplanner/blob/084c94e842f1f725cb6cde1e63115e152b12b769/assets/github_media/gbpplanner_circle.gif">
  <img src="https://github.com/aalpatya/gbpplanner/blob/084c94e842f1f725cb6cde1e63115e152b12b769/assets/github_media/gbpplanner_junction.gif">
</p>

**Watch the Code tutorial: https://www.youtube.com/watch?v=jvoPJ8GLiHk**

### Initial Setup
Install Raylib dependencies as mentioned in https://github.com/raysan5/raylib#build-and-installation
This will be platform dependent

Usually included with Linux (but you may need to install on other platforms)
- [OpenMP](https://www.openmp.org/)
- cmake (>=3.10)
- make

Clone the repository *with the submodule dependencies:*
```shell
git clone https://github.com/SafwanChowdhury/gbpplanner-Platooning.git --recurse-submodules
cd gbpplanner-Platooning
```
Use CMAKE to set up the build environment and then run 'make':
```shell
cd packages/gbpplanner-DACS
mkdir build
cd build
cmake ..
make
```

### Run examples
Make any changes to the simulations you want in config/config.json and then run:
```shell
./gbpplanner
```

Examples config files are in config directory, and include:
- ```config.json``` (Circle Formation - MasterSlave)
- ```circle_group.json``` (Circle Formation - Follower-Leader)
- ```circle_combined.json``` (Circle Formation - Combined Techniques)
- ```follow-leader.json``` (Snake Formation - Follower-Leader)
- ```highway.json``` (Highway Formation - MasterSlave)
- ```highway-rogue.json``` (Highway Formation - Follower-Leader, with toggleable rogue agents)
- ```highway-combined.json``` (Highway Formation - Combined Techniques)

Run the simulation with a specific configuration:
```shell
./gbpplanner --cfg "../config/highway-rogue.json
```

Or create your own config_file.json and run:
```shell
./gbpplanner --cfg ../config_file.json
```

#### During simulation
**Press 'H' to display help and tips!**

Use the mouse wheel to change the camera view (scroll : zoom, drag : pan, shift+drag : rotate)

Press 'spacebar' to transition between camera keyframes which were set in ```src/Graphics.cpp```.

### Play with the code
Edit the parameters in the config files and see the effects on the simulations!

**Watch the Code tutorial: https://www.youtube.com/watch?v=jvoPJ8GLiHk**

#### Own formations
You may want to create your own formations and scenarios for the robots.

Towards the end of ```src/Simulator.cpp``` there is a function called ```createOrDeleteRobots()```, where you may add your own case.

#### Custom Obstacles
- Create an image file (.png) with BLACK obstacles on a WHITE background (see ```assets/imgs``` for examples)
- Covert your image to a distance field image using the function in ```assets/scripts/create_distance_field.py```
- Edit the OBSTACLE_FILE value in your config.json file with the new distance image

### Cite the original paper
```
@ARTICLE{gbpplanner,
        author={Patwardhan, Aalok and Murai, Riku and Davison, Andrew J.},
        journal={IEEE Robotics and Automation Letters}, 
        title={Distributing Collaborative Multi-Robot Planning With Gaussian Belief Propagation}, 
        year={2023},
        volume={8},
        number={2},
        pages={552-559},
        doi={10.1109/LRA.2022.3227858}}
```

## GBPPlanner for ETS2LA
This project builds upon the GBPPlanner framework, add a general api framework and enables it to work with Euro Truck Simulator 2 through ETS2LA.

### Initial Setup
Ensure ETS2LA is installed on the host machines which are running ETS2 and ETS2LA. If you would like to use this without the game you may skip the installation of ETS2LA.

Clone the repository *with the submodule dependencies:*
```shell
git clone https://github.com/SafwanChowdhury/gbpplanner-Platooning.git --recurse-submodules
cd gbpplanner-Platooning
```
Use CMAKE to set up the build environment and then run 'make':
```shell
cd packages/gbpplanner-ETS2LA
mkdir build
cd build
cmake ..
make
```

### Run examples
To run the simulation with ETS2LA integration, use the following command:

```shell
./gbpplanner --cfg "../config/ets2.json"
```

### Adding External Trucks
To provide GBPPlanner with ETS2LA servers to connect to, first get the IP of the machine hosting the game and ETS2LA. Then pass these as launch parameters:
```shell
./gbpplanner --cfg "../config/ets2.json" --radar-ip "192.168.x.x" --radar-ip "192.168.x.y"
```

Ensure USE_RADAR is set to true in the ets2.json config file.

#### During simulation
**Press 'H' to display help and tips!**

Use the mouse wheel to change the camera view (scroll : zoom, drag : pan, shift+drag : rotate)

Press 'spacebar' to transition between camera keyframes which were set in ```src/Graphics.cpp```.

### Play with the code
Edit the parameters in the config files and see the effects on the simulations!

Towards the end of ```src/Simulator.cpp``` there is a function called ```createOrDeleteRobots()```, where you may modify the waypoints to fit your need.

Trucks in Group 2 will follow the Truck in Group 1, they will use their middle waypoint as the merge point. 

#### Custom Obstacles
- Create an image file (.png) with BLACK obstacles on a WHITE background (see ```assets/imgs``` for examples)
- Covert your image to a distance field image using the function in ```assets/scripts/create_distance_field.py```
- Edit the OBSTACLE_FILE value in your config.json file with the new distance image
- Create a custom obstacle map of the road segment you wish to use.

## Euro Truck Simulator 2 Lane Assist

Lane assist and plugin based interface program for SCS truck simulators tailored for gbpplanner-ETS2.

You will need a legal copy of ETS2 (likely multiple if you wish to test a platooning scenario)

### Installer
https://github.com/SafwanChowdhury/gbpplanner-Platooning/releases/download/Release/ETS2LA-Installer.exe

The installer will install all necessary files to C:/LaneAssist
### Initial Setup
Follow the steps listed in the installer. If you already have ETS2LA installed, copy the contents of the ETS2LA-DACS folder into your /app folder and replace all.

Remember to run requirements.bat to update the requirements.  

### Game Setup
Ensure ```g_developer 1 ``` and ```g_console 1``` is set in your ETS2 Game config file. You can search online "How To Enable Developer Mode ETS2" for specific instructions. 

With the console open in game Teleport the trucks using:
```shell
goto x;y;z
```

Set up your trucks at the the following coordinates:

Truck 1:  -42103 -12 -17655

Truck 2: -43968 —3 -20097

Set ingame navigation to a common point far past the merge point. I recommend the next fuel stop along the M1 North after the intersection. 

### ETS2LA Setup
Ensure your ETS2LA is setup and able to drive. Follow the instructions on youtube or wiki. 

Once ETS2LA is working, enable the ExternalAPI-Socket plugin, CruiseControl Plugin and the GBPPlannerData Plugin. 

Drive both trucks at the same time, once cruise control kicks in you can let go and the trucks will autonomously drive to the merge point. Once nearing the merge point you can active gbpplanner by navigating to the directory as stated above for gbpplanner-ETS2 and running:

```shell
./gbpplanner --cfg "../config/ets2.json" --radar-ip "192.168.x.x" --radar-ip "192.168.x.y"
```

As before ensure USE_RADAR is enabled. 

You should see the trucks arrive at the merge point and platoon together autonomously. 

### Links

Discord: https://discord.gg/ets2la

Youtube: https://www.youtube.com/@tumppi066

Wiki: https://wiki.ets2la.com/

Documentation (from original creators): https://docs.tumppi066.fi
