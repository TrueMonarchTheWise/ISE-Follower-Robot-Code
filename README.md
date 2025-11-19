These files are the code to my ISE 102 final project. 
The project is a hijacked ELEGOO Tumbller kit robot, but instead of self balancing, it is now too heavy to self balance (whoops) but now follows the color red!
The parts added to the original kit are: 
- Anker 20,000 mAh battery pack
- Raspberry Pi 5 16gb
- USB Webcam
- JBL Go 4

The original footprint of the robot was too shallow to accompany all of the parts added onto it, so the chasis was modified. 
Instead of putting all of the acryllic plates vertical, one acryllic plate was placed behind the aluminum sheet to hold the anker battery pack.
With the anker battry pack as the base, the original battery pack, speaker, and wire container were all built on top of it. 

A part of the robot is that it plays sounds when performing certian actions.
The robot plays sounds when it is:
- Searching
- Tracking
- At random intervals

The code itself does not have a volume control, but that can be easily set through the Raspberry Pi before taking off. 
The spaker used does not HAVE to be a JBL Go 4, it can be any speaker, bluetooth or wired, as long as the Pi recognizes it and the cables do not get wrapped up in the wheels.

FOR SOUND SETUP:
as the python is to be written and executed on a Raspberry Pi 5 running Linux, the ./sounds file must be placed IN THE DIRECTORY OF THE PYTHON CODE
The sounds currently written in the code "shaw.mp3", "tada.mp3" are not included in the repository.
