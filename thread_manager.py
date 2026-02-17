import asyncio
from dataclasses import dataclass, field
import json
import os
import tempfile
from typing import Dict, Optional


@dataclass
class MatchThreads():
    """Represents a match and its associated threads on Reddit"""
    slug: str
    match: Optional[str] = None
    pre: Optional[str] = None
    post: Optional[str] = None
    stream_link: Optional[str] = field(default=None, metadata={"json_key": "stream-link"})

    @classmethod
    def from_dict(cls, data: Dict) -> 'MatchThreads':
        return cls(
            slug=data["slug"],
            match=data.get("match"),
            pre=data.get("pre"),
            post=data.get("post"),
            stream_link=data.get("stream-link")
        )

    def to_dict(self) -> Dict:
        result = {"slug": self.slug}
        if self.pre:
            result["pre"] = self.pre
        if self.match:
            result["match"] = self.match
        if self.post:
            result["post"] = self.post
        if self.stream_link:
            result["stream-link"] = self.stream_link
        return result

class ThreadManager:
    """Manages match thread data persistence"""
    def __init__(self, filename: str):
        self.filename = filename
        self.threads: Dict[str, MatchThreads] = {}
        self._lock: Optional[asyncio.Lock] = None
        self.load()

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def load(self) -> None:
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                self.threads = {
                    sportec_id: MatchThreads.from_dict(thread_data)
                    for sportec_id, thread_data in data.items()
                }
        except FileNotFoundError:
            self.threads = {}

    async def save(self) -> None:
        async with self._get_lock():
            data = {
                sportec_id: thread.to_dict()
                for sportec_id, thread in self.threads.items()
            }
            dir_name = os.path.dirname(os.path.abspath(self.filename))
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=4)
                os.replace(tmp_path, self.filename)
            except BaseException:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    async def add_threads(self, sportec_id: str, thread: MatchThreads) -> None:
        self.threads[sportec_id] = thread
        await self.save()

    def get_threads(self, sportec_id: str) -> Optional[MatchThreads]:
        return self.threads.get(sportec_id)

    async def update_thread(self, sportec_id: str, **kwargs) -> None:
        if sportec_id in self.threads:
            thread = self.threads[sportec_id]
            for key, value in kwargs.items():
                if hasattr(thread, key):
                    setattr(thread, key, value)
            await self.save()
