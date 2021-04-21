import shutil
from inspect import BoundArguments
from pathlib import Path

from dask.base import tokenize

import flowsaber


class Serializer(object):
    def load(self, file):
        raise NotImplementedError

    def dump(self, value, file):
        raise NotImplementedError


class CloudPickleSerializer(Serializer):
    def load(self, file):
        from cloudpickle import load
        return load(file)

    def dump(self, value, file):
        from cloudpickle import dump
        return dump(value, file)


class CacheInvalidError(Exception):
    pass


NO_CACHE = object()


class Cache(object):
    """Cache is used for persisting results of met inputs. The cache should produce unique keys for unique inputs by
    implementing `hash` method. Hash of inputs can be further used to write/read related data.
    """

    def __init__(self, task=None, cache: bool = True):
        self.task = task
        self.enable = cache

    def hash(self, input_args: BoundArguments, **kwargs):
        raise NotImplementedError

    def put(self, input_key: str, output):
        raise NotImplementedError

    def get(self, input_key: str, default=NO_CACHE):
        raise NotImplementedError

    def remove(self, input_key: str):
        raise NotImplementedError

    def persist(self):
        raise NotImplementedError


class LocalCache(Cache):
    """LocalCache treat hash keys as directories in disk and dump/load python objects in the corresponding directories.
    """
    VALUE_FILE = ".__Cache_value__"

    def __init__(self, serializer: Serializer = CloudPickleSerializer(), **kwargs):
        super().__init__(**kwargs)
        self.cache = {}
        self.serializer = serializer

    def __copy__(self):
        return self

    def __deepcopy__(self, memodict={}):
        return self

    def hash(self, input_args: BoundArguments, **kwargs):
        flowsaber.context.logger.debug("hash input", input_args, kwargs)
        # we do not count for parameter names, we only care about orders
        if not self.enable:
            return ""
        hash_dict = {
            'data': tuple(input_args.arguments.values()),
            **kwargs,
        }
        return tokenize(hash_dict)

    def remove(self, run_key):
        path = Path(run_key)
        if path.exists():
            for f in path.glob('*'):
                if not f.name.startswith('._'):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                    else:
                        shutil.rmtree(f, ignore_errors=True)

            return self.cache.pop(run_key, None)

    def get(self, run_key: str, default=NO_CACHE) -> object:
        if not self.enable:
            self.remove(run_key)
            flowsaber.context.logger.debug(f"Clean cache: {run_key} since cache set to False")
            return default
        # case 1, in memory cache
        if run_key in self.cache:
            flowsaber.context.logger.debug(f"{self.task} read cache:{run_key} succeed from memory.")
        else:
            # case 2, in disk cache
            value_path = Path(run_key, self.VALUE_FILE)
            try:
                with value_path.open('rb') as f:
                    value = self.serializer.load(f)
            except Exception as e:
                self.remove(run_key)
                flowsaber.context.logger.debug(f"{self.task} read cache:{run_key} failed from disk with error: {e}")
                return default
            self.cache[run_key] = value
            flowsaber.context.logger.debug(f"{self.task} read cache:{run_key} succeed from disk.")
        return self.cache[run_key]

    def put(self, run_key: str, output):
        if not self.enable:
            return
        flowsaber.context.logger.debug(f"set cache:{run_key} with: {output}")
        self.cache[run_key] = output

    def persist(self):
        """
        This should be called before python program ends
        """
        flowsaber.context.logger.debug(f"Persist cache data: {self.cache}")
        for key, value in self.cache.items():
            f = Path(key, self.VALUE_FILE)
            f.parent.mkdir(parents=True, exist_ok=True)
            with f.open('wb') as wf:
                self.serializer.dump(value, wf)


def get_cache(cache: str = 'local', *args, **kwargs):
    cache_cls = {
        'local': LocalCache
    }
    if cache not in cache_cls:
        raise ValueError(f"cache type {cache} not supported, choose one of {cache_cls.keys()}")

    return cache_cls[cache](*args, **kwargs)
