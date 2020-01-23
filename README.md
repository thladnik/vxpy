# Documentation

## Glumpy version to use

Currently, in order to use the fullscreen functionality, use the glumpy version on this fork: https://github.com/thladnik/glumpy

## TODO

### Update TODO list...


### Saving of experimental data to file (across all processes)



### Enable StimulationProtocol class to handle protocol specific batches of data
Some data (e.g. large multidimensional array of random numbers) may be required by multiple stimuli in a protocol, which differ in
other parameters. (Re)creation of these arrays during initialization of the stimulus may drain performance and
introduce lags into stimulus presentation. Enabling the StimulationProtocol to initialize and retain these arrays to
be used by multiple stimuli in the protocol would improve performance.

However, this could cause stimuli to be incompatible with protocols which do not provide these data batches.

**Alternative solution**: if all stimuli in the protocol are subclassing the same stimulus, these kinds of data could be created as class attributes in the parent class.
