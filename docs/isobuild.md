# OpenOS ISO Build Guide

This document outlines the detailed steps required to build the bootable live ISO for OpenOS.

## Prerequisites

Building a Debian live ISO requires a Debian-based host system (e.g., Debian, Ubuntu, Kali) and the `live-build` toolkit.

Install the required build dependencies on your host system:

```bash
sudo apt update
sudo apt install -y live-build make git debootstrap xorriso squashfs-tools mtools
```

## Build Process

You can build the ISO using the included Makefile or by running the `live-build` commands manually. 

### Method 1: Using Makefile (Recommended)

From the root of the repository, simply run:

```bash
make iso
```

This command will automatically navigate to the `build` directory and run the necessary `lb clean`, `lb config`, and `lb build` commands using `sudo`.

### Method 2: Manual Build

If you want more control over the build process, you can run the commands manually:

```bash
cd build

# 1. Clean any previous build artifacts
sudo lb clean

# 2. Configure the build environment
sudo lb config

# 3. Start the build process (This will take a while)
sudo lb build
```

## Build Outputs

Once the build process completes successfully, you will find the generated ISO image in the `build` directory:

```text
build/live-image-amd64.hybrid.iso
```

## Troubleshooting

- **Permission Denied**: Building an ISO requires root privileges because it creates a `chroot` environment and modifies loop devices. Ensure you use `sudo`.
- **Disk Space**: The build process requires significant disk space. Ensure you have at least 15-20 GB of free space available.
- **Cache Issues**: If you modified dependencies in `build/config/package-lists/openos.list.chroot` and they are not appearing, ensure you run `sudo lb clean` before building to clear the cache.
- **Ollama Download**: The build hook temporarily starts Ollama to pull the `llama3.2:3b` model. If your network connection is interrupted, the ISO will simply defer the model download until the first boot.
