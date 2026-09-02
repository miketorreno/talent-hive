import builtins

Set = builtins.set


class FakeRedis:
    """In-memory stand-in for the redis commands the repositories use."""

    def __init__(self) -> None:
        self._strings: dict[str, str] = {}
        self._sets: dict[str, Set[bytes]] = {}

    async def get(self, key: str) -> str | None:
        return self._strings.get(key)

    async def set(self, key: str, value: str) -> None:
        self._strings[key] = value

    async def delete(self, key: str) -> int:
        existed = key in self._strings
        self._strings.pop(key, None)
        return 1 if existed else 0

    async def smembers(self, key: str) -> Set[bytes]:
        return Set(self._sets.get(key, Set()))

    async def sadd(self, key: str, *values: str) -> int:
        self._sets.setdefault(key, Set()).update(v.encode() for v in values)
        return len(values)

    async def srem(self, key: str, *removals: str) -> int:
        bucket = self._sets.get(key, Set())
        removed = 0
        for v in removals:
            if v.encode() in bucket:
                bucket.remove(v.encode())
                removed += 1
        return removed

    async def smismember(self, key: str, *members: str) -> list[int]:
        bucket = self._sets.get(key, Set())
        return [1 if m.encode() in bucket else 0 for m in members]
