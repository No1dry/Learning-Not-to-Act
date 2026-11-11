"""Per-process verified hashes and bounded, compact preparation progress."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time


class Progress:
    def __init__(self, stage, callback=None, interval=30):
        self.stage = stage
        self.callback = callback or (lambda record: print(json.dumps(record, ensure_ascii=False, allow_nan=False), file=sys.stderr, flush=True))
        self.interval = min(30, max(0, float(interval)))
        self.started = time.monotonic()
        self.last = None
        self.fields = {}

    def update(self, **fields):
        self.fields.update(fields)
        now = time.monotonic()
        if self.last is None or now-self.last >= self.interval:
            self._emit(now)

    emit = update
    tick = update

    def _emit(self, now):
        record = dict(self.fields, stage=self.stage, elapsed_seconds=round(now-self.started, 3))
        if record.get('total'):
            record['percent'] = round(100*record.get('completed', 0)/record['total'], 2)
        self.callback(record)
        self.last = now

    def finish(self, **fields):
        self.fields.update(fields)
        self.fields['finished'] = True
        self._emit(time.monotonic())


class HashContext:
    """Memoize only stable canonical files within this live process.

    A cached path whose stat changes is rejected, including during the first
    read. No disk cache or persisted verification exemptions are used.
    """
    def __init__(self, progress=None):
        self.progress = progress or Progress('hash')
        self._verified = {}
        self.files_read = 0
        self.bytes_read = 0

    @staticmethod
    def _stat(path):
        value = path.stat()
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns

    def sha256(self, path):
        path = Path(path).expanduser().resolve(strict=True)
        key = os.path.normcase(str(path))
        before = self._stat(path)
        if key in self._verified:
            stat, digest = self._verified[key]
            if stat != before:
                raise ValueError('verified source stat changed: '+str(path))
            return digest
        digest = hashlib.sha256()
        size = 0
        with path.open('rb') as stream:
            while True:
                chunk = stream.read(1024*1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
                self.progress.update(source=str(path), file_bytes=size, file_total_bytes=before[2],
                                     files=self.files_read, bytes=self.bytes_read+size)
        after = self._stat(path)
        if before != after or size != before[2]:
            raise ValueError('source changed while hashing: '+str(path))
        result = digest.hexdigest()
        self._verified[key] = (after, result)
        self.files_read += 1
        self.bytes_read += size
        self.progress.update(source=str(path), file_bytes=size, file_total_bytes=before[2],
                             files=self.files_read, bytes=self.bytes_read)
        return result

    def verify(self, path, sha):
        if self.sha256(path) != sha:
            raise ValueError('source SHA bytes changed: '+str(path))
        return True
