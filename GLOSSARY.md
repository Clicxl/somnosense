# Sleep Monitor

A web app that shows readings from bedside and wearable sleep sensors for a single sleeper and turns them into a sleep score.

## Language

**Sleeper**:
The one person whose sleep is monitored. There is exactly one.
_Avoid_: User, patient, account

**Sensor**:
A source of one kind of measurement: heart rate, temperature, humidity, motion, and optionally sound level.
_Avoid_: Device, module, modality

**Reading**:
One timestamped value reported by one Sensor.
_Avoid_: Sample, data point, measurement

**Simulated Reading**:
A Reading produced by the Simulator rather than by real hardware, and always labelled as such.
_Avoid_: Fake data, mock data, dummy data

**Simulator**:
The stand-in for the sensor hardware that produces Simulated Readings.
_Avoid_: Mock, emulator, generator

**Scenario**:
A named night the Simulator can play, such as a good night, a restless night, a hot and humid room, or a noisy room.
_Avoid_: Profile, preset, test case

**Sleep Session**:
One night of the Sleeper's sleep, from the moment they start it to the moment they stop it, with every Reading taken in between.
_Avoid_: Night, recording, run

**Auto-closed Session**:
A Sleep Session the Sleeper never stopped, which was closed automatically at its last Reading.
_Avoid_: Timed-out session, abandoned session

**Data Gap**:
A stretch of a Sleep Session in which one Sensor sent no Readings for longer than the allowed gap.
_Avoid_: Dropout, missing data

**Live View**:
The view of the latest Readings while a Sleep Session is in progress.
_Avoid_: Dashboard, monitor

**Morning Report**:
The summary of a finished Sleep Session, including its Sleep Score.
_Avoid_: Nightly report, summary, results

**Sleep Score**:
A single number summarising the quality of one Sleep Session, always shown together with the inputs that produced it.
_Avoid_: Sleep quality, rating

**Baseline**:
What is typical for the Sleeper, taken from their past Sleep Sessions.
_Avoid_: Average, norm, history
