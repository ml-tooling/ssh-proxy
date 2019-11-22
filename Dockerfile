FROM ubuntu:18.04

# Basics
ENV _RESOURCES_PATH="/resources"

# Layer cleanup script
COPY docker-res/scripts/clean-layer.sh /usr/bin/clean-layer.sh

RUN \
    mkdir $_RESOURCES_PATH && \
    chmod ug+rwx $_RESOURCES_PATH && \
    chmod a+rwx /usr/bin/clean-layer.sh

RUN \
    apt-get update && \
    apt-get install -y \
        wget \
        python3 \
        python3-pip    && \
        ln -s /usr/bin/pip3 /usr/bin/pip && \
        ln -s /usr/bin/python3 /usr/bin/python && \
    # Cleanup
    clean-layer.sh

# SSH Server
## Install & Prepare SSH
RUN \
    mkdir /var/run/sshd && \
    mkdir /root/.ssh && \
    mkdir /var/lib/sshd && \
    chmod -R 700 /var/lib/sshd/ && \
    chown -R root:sys /var/lib/sshd/ && \
    useradd -r -U -d /var/lib/sshd/ -c "sshd privsep" -s /bin/false sshd && \
    apt-get update && \
    apt-get install -y build-essential libssl-dev zlib1g-dev && \
    cd $_RESOURCES_PATH && \
    wget "https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-8.0p1.tar.gz" && \
    tar xfz openssh-8.0p1.tar.gz && \
    cd $_RESOURCES_PATH/openssh-8.0p1/ && \
    # modify the code where the 'PermitOpen' host is checked so that it supports regexes
    sed -i "s@strcmp(allowed_open->host_to_connect, requestedhost) != 0@strcmp(allowed_open->host_to_connect, requestedhost) != 0 \&\& match_hostname(requestedhost, allowed_open->host_to_connect) == 0@g" ./channels.c && \
    ./configure && \
    make && \
    make install && \
    # filelock is needed for our custom AuthorizedKeysCommand script in the OpenSSH server
    apt-get install -y python3-setuptools && \
    pip install filelock && \
    # Python kubernetes client is needed for caching the authorized keys in Kubernetes mode
    pip install kubernetes && \
    pip install docker && \
    # Cleanup
    clean-layer.sh

## Create user with restricted permissions for ssh
# https://gist.github.com/smoser/3e9430c51e23e0c0d16c359a2ca668ae
# https://www.tecmint.com/restrict-ssh-user-to-directory-using-chrooted-jail/
# http://www.ab-weblog.com/en/creating-a-restricted-ssh-user-for-ssh-tunneling-only/
RUN useradd -d /home/limited-user -m -s /bin/true --gid nogroup --skel /dev/null --create-home limited-user && \ 
    #chmod 755 /home/limited-user && \ 
    #chmod g+rwx /home/limited-user && \ 
    echo 'PATH=""' >> /home/limited-user/.profile && \
    echo 'limited-user:limited' |chpasswd && \
    chmod 555 /home/limited-user/ && \
    cd /home/limited-user/ && \
    # .bash_logout .bashrc
    chmod 444 .profile && \
    chown root:root /home/limited-user/

COPY docker-res/start_ssh.py $_RESOURCES_PATH/start_ssh.py
COPY docker-res/ssh/* /etc/ssh/

# Set default configuration
ENV SSH_PERMIT_TARGET_HOST="*" \
    SSH_PERMIT_TARGET_PORT="*" \ 
    SSH_TARGET_KEY_PATH="~/.ssh/id_ed25519.pub" \ 
    MANUAL_AUTH_FILE="false" \
    SSHD_ENVIRONMENT_VARIABLES="${_RESOURCES_PATH}/sshd_environment" \
    SSH_TARGET_PUBLICKEY_API_PORT=8080 \
    ENV_NAME_SSH_TARGET_LABELS=""

RUN \
    chmod -R ug+rwx $_RESOURCES_PATH && \
    touch $SSHD_ENVIRONMENT_VARIABLES && \
    chmod a+r $SSHD_ENVIRONMENT_VARIABLES && \
    # Replace the environment variable in the script directly here, since the script is executed from sshd shell and cannot 
    # access the environment variable directly 
    sed -i 's@$SSHD_ENVIRONMENT_VARIABLES@'"$SSHD_ENVIRONMENT_VARIABLES"'@g' /etc/ssh/authorize.sh

ENTRYPOINT python $_RESOURCES_PATH/start_ssh.py
