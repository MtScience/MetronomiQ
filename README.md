# MetronomiQ

This is a small metronome emulator program that I wrote mainly for recreation and to practice working with PyQt.

## Features

MetronomiQ emulates the old-school mechanical metronome, so it doesn't allow the user to choose a time signature or play a particular rhythm. Instead it just emits regularly-spaced clicking sounds. However, it has a “precise tempo mode”, which allows the user to set a specific tempo down to 1 BPM precision. The tempo range is 40–208 BPM in “Maelzel's mode” and 20–300 BPM in “precise mode”.

In addition to the main function of counting out time, the program also shows an appropriate traditional tempo marking for each tempo and allows copying the numeric BPM value and the traditional marking.

## Notes

This program was written as an exercise in using PyQt, not as a high-precision metronome emulator (although it, supposedly, can be modified appropriately). Therefore, it does not guarantee millisecond precision. However, it should be fine for figuring out tempos, personal practice. 
