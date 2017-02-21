# For a lock
import threading

# For Android CPython/JNI sensors
import sensor

# Contain any sensor access in a critical section.
# (We use this to never `harshexit` while a sensor is accessed.)
# See aaaaalbert/sensibility-testbed#19
sensorlock = threading.Lock()


# Fetch a sensor reading, store the sensor event timestamp (whose origin
# is the machine's boot timestamp) in milliseconds.
_, sensor_zulu_time, _, _, _ = sensor.get_acceleration()

# I would love to sync sensor events with the vessel's `getruntime()`
# more precisely.
# However, this requires access to `emulmisc.getruntime` which in turn
# causes a messy circular import problem. Fortunately, the time delta
# between `getruntime` and our sensors' time is small, a few dozen
# milliseconds on a lower-end smartphone. Thus, don't adjust.
#
#sensor_zulu_time -= emulmisc.getruntime() * 1000



def normalize_sensor_event_time(t):
  """Convert the sensor event timestamp `t` from milliseconds (see
  com.snakei/SensorService.java/onSensorChanged) to seconds, and
  rebase it so that the sensor event timestamps start at zero;
  (almost) at the vessel's start time."""
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

