"""Used for sshd's AuthorizedKeysCommand to fetch a list of authorized keys.
The script will create a file in ssh's authorized_keys format at `/etc/ssh/authorized_keys_cache` containing
authorized_keys from all ssh target containers / pods (by exec'ing into them and fetching the public keys).
The script will cache the containers / pods it already got the keys from to reduce runtime and will only exec
into those it did not fetch the keys from in a previous run. This behavior can be changed with the first argument arg1.

Args:
    arg1 (str): If value of arg1 is 'full', then the cache files are not considered

"""

import docker
from kubernetes import client, config, stream
import os
import sys
from filelock import FileLock, Timeout
from subprocess import getoutput
import re
import requests

SSH_PERMIT_TARGET_HOST = os.getenv("SSH_PERMIT_TARGET_HOST", "*")
SSH_TARGET_KEY_PATH = os.getenv("SSH_TARGET_KEY_PATH", "~/.ssh/id_ed25519.pub")
SSH_TARGET_PUBLICKEY_API_PORT = os.getenv("SSH_TARGET_PUBLICKEY_API_PORT", 8080)
ENV_SSH_TARGET_LABELS = os.getenv("SSH_TARGET_LABELS", "")

authorized_keys_cache_file = "/etc/ssh/authorized_keys_cache"
authorized_keys_cache_file_lock = "cache_files.lock"
query_cache_file = "/etc/ssh/query_cache"

container_client = None
CONTAINER_CLIENT_KUBERNETES = "kubernetes"
CONTAINER_CLIENT_DOCKER = "docker"

PRINT_KEY_COMMAND = '/bin/bash -c  "cat {SSH_TARGET_KEY_PATH}"'.format(SSH_TARGET_KEY_PATH=SSH_TARGET_KEY_PATH)

SSH_PERMIT_TARGET_HOST_REGEX = SSH_PERMIT_TARGET_HOST.replace("*", ".*")
SSH_PERMIT_TARGET_HOST_REGEX = re.compile(SSH_PERMIT_TARGET_HOST_REGEX)


# First try to find Kubernetes client. If Kubernetes client or the config is not there, use the Docker client
try:
    try:
        # incluster config is the config given by a service account and it's role permissions
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    kubernetes_client = client.CoreV1Api()
    container_client = CONTAINER_CLIENT_KUBERNETES

    # at this path the namespace the container is in is stored in Kubernetes deployment (see https://stackoverflow.com/questions/31557932/how-to-get-the-namespace-from-inside-a-pod-in-openshift)
    NAMESPACE = getoutput(
        "cat /var/run/secrets/kubernetes.io/serviceaccount/namespace")
except (FileNotFoundError, TypeError):
    try:
        docker_client = docker.from_env()
        docker_client.ping()
        container_client = CONTAINER_CLIENT_DOCKER
    except FileNotFoundError:
        pass

if container_client is None:
    print("Could neither initialize Kubernetes nor Docker client. Stopping execution.")
    exit(1)


def get_authorized_keys_kubernetes(query_cache: list = []) -> (list, list):
    """Execs into all Kubernetes pods where the name complies to `SSH_PERMIT_TARGET_HOST` and returns it's public key.

    Note: 
        This method can be quite slow. For big setups / clusters, think about rewriting it to fetch public keys from a REST API or so.

    Args:
        query_cache (list[str]): contains Pod names which are skipped

    Returns:
        list[str]: newly fetched public keys
        list[str]: name of all pods (previously cached ones and newly exec'd ones)

    """

    pod_list = kubernetes_client.list_namespaced_pod(
        NAMESPACE, field_selector="status.phase=Running", label_selector=ENV_SSH_TARGET_LABELS)
    authorized_keys = []
    new_query_cache = []
    for pod in pod_list.items:
        name = pod.metadata.name
        pod_ip = pod.status.pod_ip

        if SSH_PERMIT_TARGET_HOST_REGEX.match(name) is None:
            continue
        elif name in query_cache:
            new_query_cache.append(name)
            continue

        key = None
        # Try to get the public key via an API call first
        publickey_url = "http://{}:{}/publickey".format(pod_ip, str(SSH_TARGET_PUBLICKEY_API_PORT))
        timeout_seconds = 10
        try:
            request = requests.request("GET", publickey_url, timeout=timeout_seconds)
            if request.status_code == 200:
                key = request.text
        except requests.exceptions.ConnectTimeout:
            print("Connection to {ip} timed out after {timeout} seconds. Will try to exec into the pod to retrieve the key.".format(ip=pod_ip, timeout=str(timeout_seconds)))

        # If the API call did not work, try to exec into the pod. 
        # Make sure that the executing process has permission to exec into the target pod (e.g. when Kubernetes roles are used)
        if key is None:
            try:
                exec_result = stream.stream(kubernetes_client.connect_get_namespaced_pod_exec, name,
                                            NAMESPACE, command=PRINT_KEY_COMMAND, stderr=True, stdin=False, stdout=True, tty=False)
                key = exec_result
            except:
                # This can happen when the pod is in a false state such as Terminating, as status.phase is 'Running' but pod cannot be reached anymore
                print("Could not reach pod {}".format(name))

        if key is not None:
            authorized_keys.append(key)
            new_query_cache.append(name)

    return authorized_keys, new_query_cache


def get_authorized_keys_docker(query_cache: list = []) -> (list, list):
    """Execs into all Docker containers where the name starts with `SSH_PERMIT_TARGET_HOST` and returns it's public key.

    Note: 
        This method can be quite slow. For big setups / clusters, think about rewriting it to fetch public keys from a REST API or so.

    Args:
        query_cache (list[str]): contains container ids which are skipped

    Returns:
        list[str] newly fetched public keys
        list[str]: ids of all containers (previously cached ones and newly exec'd ones)

    """

    filters = {"status": "running"}
    if ENV_SSH_TARGET_LABELS != "":
        SSH_TARGET_LABELS = ENV_SSH_TARGET_LABELS.split(",")
        filters.update({"label": SSH_TARGET_LABELS})
    
    containers = docker_client.containers.list(filters=filters)
    authorized_keys = []
    new_query_cache = []
    for container in containers:

        if SSH_PERMIT_TARGET_HOST_REGEX.match(container.name) is None:
            continue
        elif container.id in query_cache:
            new_query_cache.append(container.id)
            continue

        key = None
        # Try to get the public key via an API call first
        publickey_url = "http://{}:{}/publickey".format(container.name, str(SSH_TARGET_PUBLICKEY_API_PORT))
        timeout_seconds = 10
        try:
            request = requests.request("GET", publickey_url, timeout=timeout_seconds)
            if request.status_code == 200:
                key = request.text
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            print("Connection to {ip} timed out after {timeout} seconds. Will try to exec into the pod to retrieve the key.".format(ip=container.id, timeout=str(timeout_seconds)))

        if key is None:
            exec_result = container.exec_run(PRINT_KEY_COMMAND)
            key = exec_result[1].decode("utf-8")
        
        if key is not None:
            authorized_keys.append(key)
            new_query_cache.append(container.id)

    return authorized_keys, new_query_cache


def update_cache_file():
    # make sure only a single script execution can update authorized_keys file
    lock = FileLock(authorized_keys_cache_file_lock, timeout=0)
    try:
        with lock:
            write_mode = 'a'
            # Delete query_cache file in case it is a 'full' run
            if len(sys.argv) == 2 and sys.argv[1] == "full":
                if os.path.isfile(query_cache_file):
                    os.remove(query_cache_file)
                write_mode = 'w'

            query_cache = []
            if os.path.isfile(query_cache_file):
                with open(query_cache_file, 'r') as cache_file:
                    for line in cache_file.readlines():
                        # the strip will remove the newline character at the end of each line
                        query_cache.append(line.strip())

            if container_client == CONTAINER_CLIENT_DOCKER:
                authorized_keys, new_query_cache = get_authorized_keys_docker(
                    query_cache=query_cache)
            elif container_client == CONTAINER_CLIENT_KUBERNETES:
                authorized_keys, new_query_cache = get_authorized_keys_kubernetes(
                    query_cache=query_cache)

            with open(authorized_keys_cache_file, write_mode) as cache_file:
                for authorized_key in authorized_keys:
                    if authorized_key.startswith("ssh") == False:
                        continue

                    cache_file.write("{}\n".format(authorized_key))

            with open(query_cache_file, 'w') as cache_file:
                for entry in new_query_cache:
                    cache_file.write("{}\n".format(entry))

    except Timeout:
        # The cache is currently updated by someone else
        print("The cache is currently updated by someone else")
        pass


if __name__ == "__main__":
    update_cache_file()
