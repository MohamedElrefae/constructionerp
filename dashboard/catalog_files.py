"""Local producer/consumer trust boundary; no authentication claims from file contents."""
import os
import stat
from pathlib import Path


def private_parent(path):
    path = Path(os.path.abspath(path))
    # Reject symlinks in every component, including the leaf when it exists.
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Catalog paths must not contain symlinks')
    parent = path.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('Catalog directory must be owner-only (0700)')
    return path


def read_private(path, limit):
    path = private_parent(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_nlink != 1:
            raise ValueError('Catalog must be a private regular file owned by this user')
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Catalog is too large')
    return raw
