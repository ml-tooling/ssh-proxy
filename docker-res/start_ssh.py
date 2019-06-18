"""
Container init script
"""
#!/usr/bin/python

from subprocess import call, Popen
import os
import time

# Start the SSH server that will serve as a jump host to the Workspaces to allow a user to ssh into a target
ENV_NAME_PERMIT_SERVICE_PREFIX = "SSH_PERMIT_SERVICE_PREFIX"
ENV_SSH_PERMIT_SERVICE_PREFIX = os.getenv(ENV_NAME_PERMIT_SERVICE_PREFIX, "")

ENV_NAME_MANUAL_AUTH_FILE = "MANUAL_AUTH_FILE"
ENV_MANUAL_AUTH_FILE = os.getenv(ENV_NAME_MANUAL_AUTH_FILE, "false")

if ENV_SSH_PERMIT_SERVICE_PREFIX == "":
    print("The environment variable {} must be set.".format(ENV_NAME_PERMIT_SERVICE_PREFIX))
    exit(1)

ENV_SSH_PERMIT_SERVICE_PORT = os.getenv("SSH_PERMIT_SERVICE_PORT", "22")
SSHD_CONFIG = "/etc/ssh/sshd_config"
call("sed -i 's/{PERMIT_SERVICE_PREFIX}/" + ENV_SSH_PERMIT_SERVICE_PREFIX + "/g' " + SSHD_CONFIG, shell=True)
call("sed -i 's/{PERMIT_SERVICE_PORT}/" + ENV_SSH_PERMIT_SERVICE_PORT + "/g' " + SSHD_CONFIG, shell=True)
call("sed -i \"s@{" + ENV_NAME_PERMIT_SERVICE_PREFIX + "}@" + ENV_SSH_PERMIT_SERVICE_PREFIX + "@g\" /etc/ssh/authorize.sh", shell=True)
call("sed -i \"s@{" + ENV_NAME_MANUAL_AUTH_FILE + "}@" + ENV_MANUAL_AUTH_FILE + "@g\" /etc/ssh/authorize.sh", shell=True)

call("/usr/local/sbin/sshd -D -f " + SSHD_CONFIG, shell=True)
