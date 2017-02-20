# For a Repy lock
import emulmisc

# For Android CPython/JNI sensors
import sensor

# Contain any sensor access in a critical section.
# (We use this to never `harshexit` while a sensor is accessed.)
# See aaaaalbert/sensibility-testbed#19
sensorlock = emulmisc.createlock()


# Fetch a sensor reading, store the sensor event timestamp (whose origin
# is the machine's boot timestamp) in milliseconds. The constant generated
# lets us sync sensor events with the vessel's `getruntime()`.
_, sensor_zulu_time, _, _, _ = sensor.get_acceleration()
sensor_zulu_time -= emulmisc.getruntime() * 1000



def normalize_sensor_event_time(t):
  """Convert the sensor event timestamp `t` from milliseconds (see
  com.snakei/SensorService.java/onSensorChanged) to seconds, and
  rebase it so that the vessel's start time and the
  sensor event time have the same origin.
  The sensor event timestamp should then align with the vessel's notion
  of "now", i.e. `getruntime()`."""
  return (t - sensor_zulu_time) / 1000.



def wrap3(sensor_function):
  """Generalized wrapper function for 3-axis sensor implementations that
  return a tuple containing (epochtime, eventtime, x, y, z).
  This function serializes sensor access using the sensorlock, drops
  epochtime from the return values, and normalizes the sensor event time."""
  def wrapped_sensor_function():
    sensorlock.acquire(True)
    _, t, x, y, z = sensor_function()
    sensorlock.release()
    return [normalize_sensor_event_time(t), x, y, z]
  return wrapped_sensor_function

