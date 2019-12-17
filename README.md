# MappApp

## TODO

### Basic logging

### Saving of experimental data to file (across all processes)

### Enable StimulationProtocol class to handle protocol specific batches of data
Some data (e.g. a multidimensional array of random numbers) may be required by multiple stimuli in a protocol, which differ in
other parameters. (Re)creation of these arrays during initialization of the stimulus may drain performance and
introduce lags into stimulus presentation. Enabling the StimulationProtocol to initialize and retain these arrays to
be used by multiple stimuli in the protocol would improve performance.

However, this could cause stimuli to be incompatible with protocols which do not provide these data batches.