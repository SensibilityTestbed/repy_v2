# For a lock
import threading

# For Android CPython/JNI sensors
import miscinfo
import sensor
import media
import location
import androidlog


# Allow at most this many seconds of vibration
# (We limit this here because namespace.py's `Float` value processor
# does not provide configurable mins or maxes).
MAX_VIBRATION_DURATION = 10

# Contain any sensor access in a critical section.
# (We use this to never `harshexit` while a sensor is accessed.)
# See aaaaalbert/sensibility-testbed#19
sensorlock = threading.Lock()
outputlock = threading.Lock()
medialock = threading.Lock()
vibratelock = threading.Lock()

# For simpler handling, provide an iterable lock list
locklist = [sensorlock, outputlock, medialock, vibratelock, ]


# Fetch a sensor reading, store the sensor event timestamp (whose origin
# is the machine's boot timestamp) in milliseconds. This is later used
# for "normalizing" the sensor event time.
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



def wrap_with(lock):
  """
  Return a helper function that puts the given `lock` around calls of
  its argument. Use this like so:
    wrap_with_foo_lock = wrap_with(foo_lock)  # This is what we return
    # Wrap something with the returned wrapper function:
    wrapped_function_call1 = wrap_with_foo_lock(a_function_call)
    wrapped_function_call2 = wrap_with_foo_lock(another_function_call)
    wrapped_funtion_call1(args) # This call will acquire foo_lock now
                                # before doing the actual a_function_call1.
  """
  def lock_this(function):
    def call_into_function():
      lock.acquire()
      return_value = function()
      lock.release()
      return return_value
    return call_into_function
  return lock_this



def refine_1d(sensor_function):
  """Refine the values returned by 1-axis sensor implementations, i.e.
  tuples containing (epochtime, eventtime, sensor_reading).
  In particular, drop epochtime from the return values, and normalize
  the sensor event time."""
  def refined_sensor_function_1d():
    _, t, x = sensor_function()
    return [normalize_sensor_event_time(t), x]
  return refined_sensor_function_1d



def refine_3d(sensor_function):
  """Refine the values returned by 3-axis sensor implementations, i.e.
  tuples containing (epochtime, eventtime, x, y, z).
  In particular, drop epochtime from the return values, and normalize
  the sensor event time."""
  def refined_sensor_function_3d():
    _, t, x, y, z = sensor_function()
    return [normalize_sensor_event_time(t), x, y, z]
  return refined_sensor_function_3d



# Create lock wrapper helper functions for the various locks, and
# wrap the sensor calls from the different CPython implementations.
sensorlock_wrap = wrap_with(sensorlock)
medialock_wrap = wrap_with(medialock)
outputlock_wrap = wrap_with(outputlock)
vibratelock_wrap = wrap_with(vibratelock)


# Wrap the `miscinfo` module calls
get_bluetooth_info = sensorlock_wrap(miscinfo.get_bluetooth_info)
get_bluetooth_scan_info = sensorlock_wrap(miscinfo.get_bluetooth_scan_info)
is_wifi_enabled = sensorlock_wrap(miscinfo.is_wifi_enabled)
get_wifi_state = sensorlock_wrap(miscinfo.get_wifi_state)
get_wifi_connection_info = sensorlock_wrap(miscinfo.get_wifi_connection_info)
get_wifi_scan_info = sensorlock_wrap(miscinfo.get_wifi_scan_info)
get_network_info = sensorlock_wrap(miscinfo.get_network_info)
get_cellular_provider_info = sensorlock_wrap(miscinfo.get_cellular_provider_info)
get_cell_info = sensorlock_wrap(miscinfo.get_cell_info)
get_sim_info = sensorlock_wrap(miscinfo.get_sim_info)
get_phone_info = sensorlock_wrap(miscinfo.get_phone_info)
get_mode_settings = sensorlock_wrap(miscinfo.get_mode_settings)
get_display_info = sensorlock_wrap(miscinfo.get_display_info)
get_volume_info = sensorlock_wrap(miscinfo.get_volume_info)
get_battery_info = sensorlock_wrap(miscinfo.get_battery_info)


# Wrap the `sensor` module calls
# (Some calls get a second wrapping because their return values need to be
# "refined", i.e. the epoch timestamp dropped and the sensor event
# timestamp converted to seconds.)
get_sensor_list = sensorlock_wrap(sensor.get_sensor_list)
get_acceleration = refine_3d(sensorlock_wrap(sensor.get_acceleration))
get_ambient_temperature = refine_1d(sensorlock_wrap(sensor.get_ambient_temperature))
get_game_rotation_vector = refine_3d(sensorlock_wrap(sensor.get_game_rotation_vector))
get_geomagnetic_rotation_vector = refine_3d(sensorlock_wrap(sensor.get_geomagnetic_rotation_vector))
get_gravity = refine_3d(sensorlock_wrap(sensor.get_gravity))
get_gyroscope = refine_3d(sensorlock_wrap(sensor.get_gyroscope))
get_gyroscope_uncalibrated = refine_3d(sensorlock_wrap(sensor.get_gyroscope_uncalibrated))
get_heart_rate = refine_1d(sensorlock_wrap(sensor.get_heart_rate))
get_light = refine_1d(sensorlock_wrap(sensor.get_light))
get_linear_acceleration = refine_3d(sensorlock_wrap(sensor.get_linear_acceleration))
get_magnetic_field = refine_3d(sensorlock_wrap(sensor.get_magnetic_field))
get_magnetic_field_uncalibrated = refine_3d(sensorlock_wrap(sensor.get_magnetic_field_uncalibrated))
get_pressure = refine_1d(sensorlock_wrap(sensor.get_pressure))
get_proximity = refine_1d(sensorlock_wrap(sensor.get_proximity))
get_relative_humidity = refine_1d(sensorlock_wrap(sensor.get_relative_humidity))
get_rotation_vector = refine_3d(sensorlock_wrap(sensor.get_rotation_vector))
get_step_counter = refine_1d(sensorlock_wrap(sensor.get_step_counter))


# Wrap the `media` module calls
# XXX Locking here means we can't tts_speak while microphone_record'ing.
# XXX microphone_record allows recording into arbitrarily-named files!
# XXX microphone_record's record length is quasi-unlimited!
microphone_record = medialock_wrap(media.microphone_record)
is_media_playing = medialock_wrap(media.is_media_playing)
is_tts_speaking = medialock_wrap(media.is_tts_speaking)
tts_speak = medialock_wrap(media.tts_speak)

# Wrap the `location` module calls
get_location = sensorlock_wrap(location.get_location)
get_lastknown_location = sensorlock_wrap(location.get_lastknown_location)
get_geolocation = sensorlock_wrap(location.get_geolocation)

# Wrap the `androidlog` module calls
# XXX `prompt` blocks indefinitely when the prompt GUI widget disappears!
android_log = outputlock_wrap(androidlog.log)
toast = outputlock_wrap(androidlog.toast)
notify = outputlock_wrap(androidlog.notify)
prompt = outputlock_wrap(androidlog.prompt)


# The `androidlog.vibrate` wrapper also makes sure we don't vibrate
# (and thus block the vibratelock) forever.
def vibrate(seconds):
  if 0 <= seconds <= MAX_VIBRATION_DURATION:
    vibratelock.acquire()
    androidlog.vibrate(seconds)
    vibratelock.release()
  else:
    raise RepyArgumentError("Vibration duration must be between 0 and " +
        str(MAX_VIBRATION_DURATION))

