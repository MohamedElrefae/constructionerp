"""Synthetic worker descendant: reports kernel-observed identity and egress."""
import json
import os
import socket


def main():
    try:
        socket.create_connection(("203.0.113.1", 443), timeout=2)
        egress = "ALLOWED"
    except OSError:
        egress = "DENIED"
    print(json.dumps({
        "child_pid": os.getpid(),
        "child_netns_inode": os.stat("/proc/self/ns/net").st_ino,
        "egress": egress,
        "host_home_visible": os.path.exists(os.environ["REHEARSAL_HOST_HOME"]),
    }))


if __name__ == "__main__":
    main()
