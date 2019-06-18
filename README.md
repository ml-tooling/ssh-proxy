# SSH Proxy

This container will make it easy to tunnel ssh targets through the bastion itself to expose them via a single port.
The bastion does not allow port forwarding or logging into the bastion itself.
Works in Docker and Kubernetes setup.

Logins are logged at `/etc/ssh/access.log`.

## Getting started

### Prerequisites

- The target container names must start with the prefix defined via `$SSH_PERMIT_SERVICE_PREFIX`

The bastion accepts an incoming key, if it belongs to one of the targets key, in other words the bastion server authorizes all target public keys (it is still not possible to login to the bastion directly. The authorization happens only for creating the final connection). For this to work, following requirements have to be fulfilled:
- The ssh target containers must have a public key that can be found under `/root/.ssh/id_ed25519.pub`
- In Kubernetes mode, the Bastion and the ssh-targets must be in the same namespace

The implemented behavior can be slow for big clusters, as `kubectl exec` is a quite slow command.
You can avoid those requirements by setting `$MANUAL_AUTH_FILE=true` and maintaing the bastion's `/etc/ssh/authorized_keys_cache` file yourself (e.g. by mounting a file at the same location). In this case, you don't have to mount the Docker socket / Kubernetes config into the container. The `authorized_keys_cache` file has the same format as the standard ssh authorized_keys file.

### Start SSH Bastion

```bash
docker run -d \
    -p 22 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    [-v /root/.kube/config:/root/.kube/config] \
    --env SSH_PERMIT_SERVICE_PREFIX=<some-name-prefix> \
    mltooling/ssh-proxy
```

- `-v /root/.kube/config:/root/.kube/config` is only needed for a Kubernetes setup

### Connect to Target

```bash
ssh \
    -o "ProxyCommand=ssh -W %h:%p -p <bastion-port> -i ~/.ssh/<target-key> limited-user@<bastion-host>" \
    -p <target-port> \
    -i ~/.ssh/target-key \
    root@<target-host>
```

Doing this way, the connection from client to target is end-to-end encrypted.

> The "\<target-host\>" host can be the Docker container name or Kubernetes service name. In that case, the bastion has to be in the same Docker network or the connection must be allowed in case of existing Networkpolicies in Kubernetes, respectively.


### Configuration

<table>
    <tr>
        <th>Variable</th>
        <th>Description</th>
        <th>Default</th>
    </tr>
    <tr>
        <td>SSH_PERMIT_SERVICE_PREFIX</td>
        <td>Defines which other containers can be ssh targets. The container names must start with the prefix. 
            The ssh connection to the target can only be made for targets where the name starts with the same prefix. 
            The '*' character can be used as wildcards, e.g. 'workspace-*' would allow connecting to target containers/services which names start with 'workspace-'.
        </td>
        <td>Mandatory</td>
    </tr>
    <tr>
        <td>SSH_PERMIT_SERVICE_PORT</td>
        <td>Defines on which port the other containers can be reached via ssh. The ssh connection to the target can only be made via this port then.</td>
        <td>22</td>
    </tr>
    <tr>
        <td>MANUAL_AUTH_FILE</td>
        <td>Disables the bastion's public key fetching method and you have to maintain the /etc/ssh/authorized_keys_cache file yourself (e.g. by mounting a respective file there)</td>
        <td>false</td>
    </tr>
</table>
