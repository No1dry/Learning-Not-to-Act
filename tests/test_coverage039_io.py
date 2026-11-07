"""Synthetic-only verification for Task039 input hashing and progress."""
import hashlib
import pytest


def test_hash_context_reuses_canonical_file_and_rejects_changed_stat(tmp_path):
    from egrs.coverage039.io import HashContext
    path = tmp_path/'data.bin'; path.write_bytes(b'payload')
    context = HashContext()
    assert context.sha256(path) == hashlib.sha256(b'payload').hexdigest()
    assert context.verify(path.parent/'.'/path.name, hashlib.sha256(b'payload').hexdigest())
    assert context.files_read == 1 and context.bytes_read == 7
    path.write_bytes(b'changed payload')
    with pytest.raises(ValueError, match='changed'):
        context.sha256(path)
    assert HashContext().sha256(path) == hashlib.sha256(b'changed payload').hexdigest()


def test_hash_context_rejects_change_during_read(tmp_path, monkeypatch):
    from egrs.coverage039.io import HashContext
    path = tmp_path/'data.bin'; path.write_bytes(b'payload')
    original = type(path).open
    class ChangingFile:
        def __enter__(self):
            self.stream = original(path, 'rb'); self.changed = False; return self
        def read(self, size):
            chunk = self.stream.read(size)
            if chunk and not self.changed:
                self.changed = True
                with original(path, 'ab') as stream: stream.write(b'!')
            return chunk
        def __exit__(self,*args): self.stream.close()
    monkeypatch.setattr(type(path), 'open', lambda self,*a,**kw: ChangingFile() if self == path and a == ('rb',) else original(self,*a,**kw))
    with pytest.raises(ValueError, match='changed'):
        HashContext().sha256(path)


def test_progress_emits_interval_and_final_percent(monkeypatch):
    from egrs.coverage039 import io
    now = [0.0]; monkeypatch.setattr(io.time,'monotonic',lambda:now[0])
    records=[]; progress=io.Progress('metadata',callback=records.append)
    progress.update(completed=0,total=4,source='parent',attempt=1)
    now[0]=29; progress.tick(completed=2,total=4)
    assert len(records)==1
    now[0]=30; progress.emit(completed=3,total=4)
    progress.finish(completed=4,total=4)
    assert [r['percent'] for r in records] == [0,75,100]
    assert records[-1]['elapsed_seconds']==30 and records[-1]['stage']=='metadata'
