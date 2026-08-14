# PIXI_IMAGE_TAG selects the pixi base image. The build script picks this
# automatically: the plain tag on a MacBook (no GPU), the CUDA-enabled tag
# on an H100/H200 box (nvidia-smi detected). Override manually if needed.
ARG PIXI_IMAGE_TAG=0.41.4
FROM ghcr.io/prefix-dev/pixi:${PIXI_IMAGE_TAG} AS build

# Important packages
RUN apt-get update && apt-get install -y \
    vim nano git sudo make clang gcc \
    locales xdg-utils wget \
    htop tmux curl \
    libffi-dev libglib2.0-dev openssh-client \
    ca-certificates

RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash
RUN apt-get install git-lfs

# Docker CLI only (no daemon) so GROBID's docker-compose service can be
# started/stopped from inside the devcontainer via the host's mounted
# docker socket ("docker-outside-of-docker"). The GROBID container itself
# runs as a sibling on the host, not inside this container.
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-compose-plugin

# Set the locale. Required for TMUX and neovim
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Change user
ARG USER_ID
ARG GROUP_ID
ARG GROUP_NAME
ARG USER_NAME
RUN groupadd -f -g "${GROUP_ID}" "${GROUP_NAME}"
RUN useradd -m -l -s /bin/bash -d /home/"${USER_NAME}" -u "${USER_ID}" -g "${GROUP_ID}" "${USER_NAME}" && \
    echo "${USER_NAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER "${USER_NAME}"

CMD [ "tail", "-f", "/dev/null" ]
