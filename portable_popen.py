# Split out Popen into its own library to reduce circular imports with
# nonportable.

# This may fail on Windows CE
try:
  import subprocess
  mobile_no_subprocess = False
except ImportError:
  # Set flag to avoid using subprocess
  mobile_no_subprocess = True 

# Detect windows.
import os

def Popen(args):
  # Defined in Winbase.h, CREATE_NO_WINDOW is a CreationFlag meaning "don't
  # create a console window for the started process." For more info, see:
  #   http://msdn.microsoft.com/en-us/library/ms684863%28VS.85%29.aspx
  CREATE_NO_WINDOW = 0x08000000

  if mobile_no_subprocess:
    raise Exception("No subprocess available on this platform!")

  # On android we use a custom fork-and-run C-Python extension,
  # because we don't have a Python binary.
  try:
    import android
    # Other commands (ps, wc, ifconfig, ...) don't use this extension
    # args[0] could also be empty if  no sys.executable was found
    # if len(args) >= 2 and ("python" in args[0] or not args[0]):

    # We must sanitize the arguments to our JNI popen, see
    # aaaaalbert/sensibility-testbed#31:
    #
    # Sanitize 1, make sure our call argument is a list.
    if type(args) is not list:
      raise TypeError("You must supply a list argument")

    # Sanitize 2, There must not be too many arguments, so as to not
    #    overflow the JNI's 512 local reference table slots. I'll fix
    #    the allowed maximum at an arbitrary 100 for now. This should
    #    more than suffice for our sandbox-calling purposes.
    POPEN_MAX_ARGS = 100
    if len(args) > POPEN_MAX_ARGS:
      # Do as `subprocess.Popen(["a"]*10000000)` does
      raise OSError("Invalid argument. portable_popen's argument list " +
          "is restricted to " + str(POPEN_MAX_ARGS) + " entries.")

    # Sanitize 3, Only string arguments are allowed inside the args list.
    for arg in args:
      if type(arg) is not str:
        # Do as `subprocess.Popen([123])` does
        raise TypeError("portable_popen's argument list must only " +
            "contain string arguments!" )

    # Args are sane, call down
    return android.popen_python(args[1:])

  except ImportError:
    pass

  if os.name == 'nt':
    # Windows
    return subprocess.Popen(args, creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  else:
    # Everything else
    return subprocess.Popen(args, close_fds=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
