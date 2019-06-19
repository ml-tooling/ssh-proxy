"""
Container init script
"""
#!/usr/bin/python

from subprocess import call, Popen
import os
import time

# Start the SSH server that will serve as a jump host to the Workspaces to allow a user to ssh into a target
ENV_NAME_PERMIT_TARGET_HOST = "SSH_PERMIT_TARGET_HOST"
ENV_SSH_PERMIT_TARGET_HOST = os.getenv(ENV_NAME_PERMIT_TARGET_HOST, "")

ENV_NAME_MANUAL_AUTH_FILE = "MANUAL_AUTH_FILE"
ENV_MANUAL_AUTH_FILE = os.getenv(ENV_NAME_MANUAL_AUTH_FILE, "false")

if ENV_SSH_PERMIT_TARGET_HOST == "":
    print("The environment variable {} must be set.".format(ENV_NAME_PERMIT_TARGET_HOST))
    exit(1)

ENV_NAME_PERMIT_TARGET_PORT = "SSH_PERMIT_TARGET_PORT"
ENV_SSH_PERMIT_TARGET_PORT = os.getenv(ENV_NAME_PERMIT_TARGET_PORT, "22")
SSHD_CONFIG = "/etc/ssh/sshd_config"

# replace the PermitOpen directive placeholders in the sshd_config
call("sed -i 's/{" + ENV_NAME_PERMIT_TARGET_HOST + "}/" + ENV_SSH_PERMIT_TARGET_HOST + "/g' " + SSHD_CONFIG, shell=True)
call("sed -i 's/{" + ENV_NAME_PERMIT_TARGET_PORT + "}/" + ENV_SSH_PERMIT_TARGET_PORT + "/g' " + SSHD_CONFIG, shell=True)

# add environment variables to the script executed by sshd to preserve their values in the ssh session
call("sed -i \"s@{" + ENV_NAME_PERMIT_TARGET_HOST + "}@" + ENV_SSH_PERMIT_TARGET_HOST + "@g\" /etc/ssh/authorize.sh", shell=True)
call("sed -i \"s@{" + ENV_NAME_MANUAL_AUTH_FILE + "}@" + ENV_MANUAL_AUTH_FILE + "@g\" /etc/ssh/authorize.sh", shell=True)

call("/usr/local/sbin/sshd -D -f " + SSHD_CONFIG, shell=True)
