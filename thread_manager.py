

from dataclasses import dataclass, field
import json
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
        if self.match:
            result["match"] = self.match
        if self.pre:
            result["match"] = self.pre
        if self.post:
            result["match"] = self.post
        if self.stream_link:
            result["stream-link"] = self.stream_link
    
class ThreadManager:
    """Manages match thread data persistence"""
    def __init__(self, filename: str):
        self.filename = filename
        self.threads: Dict[str, MatchThreads] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                self.threads = {
                    opta_id: MatchThreads.from_dict(thread_data)
                    for opta_id, thread_data in data.items()
                }
        except FileNotFoundError:
            self.threads = {}
    
    def save(self) -> None:
        data = {
            opta_id: thread.to_dict()
            for opta_id, thread in self.threads.items()
        }
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)
    
    def add_threads(self, opta_id: str, thread: MatchThreads) -> None:
        self.threads[opta_id] = thread
        self.save()
    
    def get_threads(self, opta_id: str) -> Optional[MatchThreads]:
        return self.threads.get(opta_id)

    def update_thread(self, opta_id: str, **kwargs) -> None:
        if opta_id in self.threads:
            thread = self.threads[opta_id]
            for key, value in kwargs.items():
                if hasattr(thread, key):
                    setattr(thread, key, value)
            self.save()