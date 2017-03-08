"""
Description:
  This file provides a Python interface to low-level system calls
  on Android. It is based on linux_api.py and nix_common_api.py.
"""
import os
import subprocess

import linux_api
_plain_process_stat_file = linux_api._process_stat_file

def _process_stat_file(filename):
  """Work around aaaaalbert/sensibility-testbed#30, monitoring process
  can't access the monitored process's procfs entry"""
  # We can access our own CPU time stats just fine
  if filename == "/proc/" + str(os.getpid()) + "/stat":
    return _plain_process_stat_file(filename)

  # However, for PIDs other than our own, we rely on nonportable's
  # `do_forked_resource_monitor_android` to pass us a handle to the
  # monitored process's procfs stat entry.
  # Read and process the information ourselves.
  # (This is just copied from linux_api's implementation.)
  global monitored_process_procfs_stat_file
  data = monitored_process_procfs_stat_file.read()
  monitored_process_procfs_stat_file.seek(0)
  data = data.strip("\n")
  # Remove the substring that says "(python)", since it changes the field alignment
  start_index = data.find("(")
  if start_index != -1:
    end_index = data.find(")", start_index)
    data = data[:start_index-1] + data[end_index+1:]

  # Break the data into an array by spaces
  return data.split(" ")

linux_api._process_stat_file = _process_stat_file

import textops      # Import seattlelib's text processing lib

monitored_process_procfs_stat_file = None

# Reuse most of the Linux API's functionality
get_process_cpu_time = linux_api.get_process_cpu_time
get_process_rss = linux_api.get_process_rss
get_current_thread_cpu_time = linux_api.get_current_thread_cpu_time
get_system_uptime = linux_api.get_system_uptime
get_uptime_granularity = linux_api.get_uptime_granularity
get_system_thread_count = linux_api.get_system_thread_count


# Override what's necessary.
#
# Concretely, we override nix_common_api's and linux_api's functions
# wherever they use `portable_popen` and/or refer to a command-line
# tool by full path. Our Android implementation has `portable_popen`
# overridden to only work for spawning a new Python interpreter
# (rather than arbitrary tools). Also, tool paths on Android differ
# from other platforms, which, while allowed for e.g. /bin/sh by
# POSIX [1], is a problem for us.
#
# [1] http://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html

# From linux_api.py
def get_interface_ip_addresses(interfaceName):
  """
  <Purpose>
    Returns the IP address associated with the interface.

  <Arguments>
    interfaceName: The string name of the interface, e.g. eth0

  <Returns>
    A list of IP addresses associated with the interface.
  """

  # Launch up a shell, get the feed back
  # We use ifconfig with the interface name.
  ifconfig_process = subprocess.Popen(["ifconfig", interfaceName.strip()],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)

  ifconfig_output, _ = ifconfig_process.communicate()
  ifconfig_lines = textops.textops_rawtexttolines(ifconfig_output)

  # Look for ipv4 addresses
  target_lines = textops.textops_grep("inet", ifconfig_lines)
  # and not ipv6
  target_lines = textops.textops_grep("inet6", target_lines, exclude=True)

  # Only take the ip(s)
  target_lines = textops.textops_cut(target_lines, delimiter=":", fields=[1])
  target_lines = textops.textops_cut(target_lines, delimiter=" ", fields=[0])

  # Create an array for the ip's
  ipaddressList = []

  for line in target_lines:
     # Strip the newline and any spacing
     line = line.strip("\n\t ")
     ipaddressList.append(line)

  # Done, return the interfaces
  return ipaddressList




# From nix_common_api
def exists_outgoing_network_socket(localip, localport, remoteip, remoteport):
  """
  <Purpose>
    Determines if there exists a network socket with the specified unique tuple.
    Assumes TCP.

  <Arguments>
    localip: The IP address of the local socket
    localport: The port of the local socket
    remoteip:  The IP of the remote host
    remoteport: The port of the remote host

  <Returns>
    A Tuple, indicating the existence and state of the socket. E.g. (Exists (True/False), State (String or None))

  """
  # This only works if all are not of the None type
  if not (localip and localport and remoteip and remoteport):
    return (False, None)

  # Grab netstat output.
  netstat_process = subprocess.Popen(["netstat", "-an"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
  netstat_stdout, _ = netstat_process.communicate()
  netstat_lines = textops.textops_rawtexttolines(netstat_stdout)

  # Search for things matching the local and remote ip+port we are trying to get
  # information about.
  target_lines = textops.textops_grep(localip + ':' + str(localport), netstat_lines) + \
      textops.textops_grep(localip + '.' + str(localport), netstat_lines)

  target_lines = textops.textops_grep(remoteip + ':' + str(remoteport), target_lines) + \
      textops.textops_grep(remoteip + '.' + str(remoteport), target_lines)

  # Only tcp connections.
  target_lines = textops.textops_grep('tcp', target_lines)

  # Check if there is any entries
  if len(target_lines) > 0:
    line = target_lines[0]
    # Replace tabs with spaces, explode on spaces
    parts = line.replace("\t","").strip("\n").split()
    # Get the state
    socket_state = parts[-1]

    return (True, socket_state)

  else:
    return (False, None)




# From nix_common_api
def exists_listening_network_socket(ip, port, tcp):
  """
  <Purpose>
    Determines if there exists a network socket with the specified ip and port which is the LISTEN state.

  <Arguments>
    ip: The IP address of the listening socket
    port: The port of the listening socket
    tcp: Is the socket of TCP type, else UDP

  <Returns>
    True or False.
  """
  # This only works if both are not of the None type
  if not (ip and port):
    return False

  # UDP connections are stateless, so for TCP check for the LISTEN state
  # and for UDP, just check that there exists a UDP port
  if tcp:
    grep_terms = ["tcp", "LISTEN"]
  else:
    grep_terms = ["udp"]

  # Launch up a shell, get the feedback
  netstat_process = subprocess.Popen(["netstat", "-an"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
  netstat_stdout, _ = netstat_process.communicate()
  netstat_lines = textops.textops_rawtexttolines(netstat_stdout)

  # Search for things matching the ip+port we are trying to get
  # information about.
  target_lines = textops.textops_grep(ip + ':' + str(port), netstat_lines) + \
      textops.textops_grep(ip + '.' + str(port), netstat_lines)

  for term in grep_terms:
    target_lines = textops.textops_grep(term, target_lines)

  number_of_sockets = len(target_lines)

  return (number_of_sockets > 0)




# From nix_common_api
def get_available_interfaces():
  """
  <Purpose>
    Returns a list of available network interfaces.

  <Returns>
    An array of string interfaces
  """
  # Common headers
  # This list contains common header elements so that they can be stripped
  common_headers_list = ["Name", "Kernel", "Iface"]

  # Netstat will return all interfaces, but also has some duplication.
  # Cut will get the first field from each line, which is the interface name.
  # Sort prepares the input for uniq, which only works on sorted lists.
  # Uniq, is somewhat obvious, it will only return the unique interfaces to remove duplicates.
  # Launch up a shell, get the feedback
  netstat_process = subprocess.Popen(["netstat", "-i"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
  netstat_stdout, _ = netstat_process.communicate()
  netstat_lines = textops.textops_rawtexttolines(netstat_stdout)

  target_lines = textops.textops_cut(netstat_lines, delimiter=" ", fields=[0])

  unique_lines = set(target_lines)

  # Create an array for the interfaces
  interfaces_list = []

  for line in unique_lines:
    # Strip the newline
    line = line.strip("\n")
    # Check if this is a header
    if line in common_headers_list:
      continue
    interfaces_list.append(line)

  # Done, return the interfaces
  return interfaces_list

