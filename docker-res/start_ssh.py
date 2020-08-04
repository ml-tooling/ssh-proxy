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

ENV_NAME_SSH_TARGET_LABELS = "SSH_TARGET_LABELS"
ENV_SSH_TARGET_LABELS = os.getenv(ENV_NAME_SSH_TARGET_LABELS, "")

ENV_NAME_SSH_TARGET_PUBLICKEY_API_PORT = "SSH_TARGET_PUBLICKEY_API_PORT"
ENV_SSH_TARGET_PUBLICKEY_API_PORT = os.getenv(ENV_NAME_SSH_TARGET_PUBLICKEY_API_PORT, "")

ENV_NAME_KUBERNETES_SERVICE_HOST = "KUBERNETES_SERVICE_HOST"
ENV_KUBERNETES_SERVICE_HOST = os.getenv(ENV_NAME_KUBERNETES_SERVICE_HOST, "")

ENV_NAME_KUBERNETES_SERVICE_PORT = "KUBERNETES_SERVICE_PORT"
ENV_KUBERNETES_SERVICE_PORT = os.getenv(ENV_NAME_KUBERNETES_SERVICE_PORT, "")

if ENV_SSH_PERMIT_TARGET_HOST == "":
    print("The environment variable {} must be set.".format(ENV_NAME_PERMIT_TARGET_HOST))
    exit(1)

ENV_NAME_PERMIT_TARGET_PORT = "SSH_PERMIT_TARGET_PORT"
ENV_SSH_PERMIT_TARGET_PORT = os.getenv(ENV_NAME_PERMIT_TARGET_PORT, "22")
SSHD_CONFIG = "/etc/ssh/sshd_config"

# replace the PermitOpen directive placeholders in the sshd_config
call("sed -i 's/{" + ENV_NAME_PERMIT_TARGET_HOST + "}/" + ENV_SSH_PERMIT_TARGET_HOST + "/g' " + SSHD_CONFIG, shell=True)
call("sed -i 's/{" + ENV_NAME_PERMIT_TARGET_PORT + "}/" + ENV_SSH_PERMIT_TARGET_PORT + "/g' " + SSHD_CONFIG, shell=True)

# export environment variables to a file which sshd can read to preserve their values in the ssh session
call("echo 'export {}={}' >> {}".format(ENV_NAME_PERMIT_TARGET_HOST, ENV_SSH_PERMIT_TARGET_HOST, os.getenv("SSHD_ENVIRONMENT_VARIABLES")), shell=True)
call("echo 'export {}={}' >> {}".format(ENV_NAME_MANUAL_AUTH_FILE, ENV_MANUAL_AUTH_FILE, os.getenv("SSHD_ENVIRONMENT_VARIABLES")), shell=True)
call("echo 'export {}={}' >> {}".format(ENV_NAME_SSH_TARGET_LABELS, ENV_SSH_TARGET_LABELS, os.getenv("SSHD_ENVIRONMENT_VARIABLES")), shell=True)
call("echo 'export {}={}' >> {}".format(ENV_NAME_SSH_TARGET_PUBLICKEY_API_PORT, ENV_SSH_TARGET_PUBLICKEY_API_PORT, os.getenv("SSHD_ENVIRONMENT_VARIABLES")), shell=True)
call("echo 'export {}={}' >> {}".format(ENV_NAME_KUBERNETES_SERVICE_HOST, ENV_KUBERNETES_SERVICE_HOST, os.getenv("SSHD_ENVIRONMENT_VARIABLES")), shell=True)
call("echo 'export {}={}' >> {}".format(ENV_NAME_KUBERNETES_SERVICE_PORT, ENV_KUBERNETES_SERVICE_PORT, os.getenv("SSHD_ENVIRONMENT_VARIABLES")), shell=True)

call("/usr/local/sbin/sshd -D -f " + SSHD_CONFIG, shell=True)
