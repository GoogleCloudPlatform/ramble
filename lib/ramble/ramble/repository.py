# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import abc
import collections
import os
import sys
import traceback
import types
import functools
import contextlib
import re
import importlib
import importlib.machinery
import importlib.util
import inspect
import stat
import shutil
import errno

try:
    from collections.abc import Mapping  # novm
except ImportError:
    from collections.abc import Mapping


from enum import Enum

import ruamel.yaml as yaml

import llnl.util.lang
import llnl.util.filesystem as fs

import ramble.caches
import ramble.config
import ramble.spec
import ramble.util.path
import ramble.util.naming as nm
from ramble.util.logger import logger

import spack.util.spack_json as sjson
import ramble.util.imp

global_namespace = "ramble"

#: Guaranteed unused default value for some functions.
NOT_PROVIDED = object()


####
# Implement type specific functionality between here, and
#     END TYPE SPECIFIC FUNCTIONALITY
####
ObjectTypes = Enum(
    "ObjectTypes",
    [
        "applications",
        "modifiers",
        "package_managers",
        "base_applications",
        "base_modifiers",
        "base_package_managers",
    ],
)

OBJECT_NAMES = [obj.name for obj in ObjectTypes]

default_type = ObjectTypes.applications

unified_config = "repo.yaml"

type_definitions = {
    ObjectTypes.applications: {
        "file_name": "application.py",
        "dir_name": "applications",
        "abbrev": "app",
        "config_section": "repos",
        "accepted_configs": ["application_repo.yaml", unified_config],
        "singular": "application",
    },
    ObjectTypes.modifiers: {
        "file_name": "modifier.py",
        "dir_name": "modifiers",
        "abbrev": "mod",
        "config_section": "modifier_repos",
        "accepted_configs": ["modifier_repo.yaml", unified_config],
        "singular": "modifier",
    },
    ObjectTypes.package_managers: {
        "file_name": "package_manager.py",
        "dir_name": "package_managers",
        "abbrev": "pkg_man",
        "config_section": "package_manager_repos",
        "accepted_configs": ["package_manager_repo.yaml", unified_config],
        "singular": "package manager",
    },
    ObjectTypes.base_applications: {
        "file_name": "base_application.py",
        "dir_name": "base_applications",
        "abbrev": "base_app",
        "config_section": "base_application_repos",
        "accepted_configs": ["base_application_repo.yaml", unified_config],
        "singular": "base application",
    },
    ObjectTypes.base_modifiers: {
        "file_name": "base_modifier.py",
        "dir_name": "base_modifiers",
        "abbrev": "base_mod",
        "config_section": "base_modifier_repos",
        "accepted_configs": ["base_modifier_repo.yaml", unified_config],
        "singular": "base modifier",
    },
    ObjectTypes.base_package_managers: {
        "file_name": "base_package_manager.py",
        "dir_name": "base_package_managers",
        "abbrev": "base_pkg_man",
        "config_section": "base_package_manager_repos",
        "accepted_configs": ["base_package_manager_repo.yaml", unified_config],
        "singular": "base package manager",
    },
}


def _apps(repo_dirs=None):
    """Get the applications singleton RepoPath instance for Ramble."""
    return _gen_path(repo_dirs=repo_dirs, obj_type=ObjectTypes.applications)


def _mods(repo_dirs=None):
    """Get the modifiers singleton RepoPath instance for Ramble."""
    return _gen_path(repo_dirs=repo_dirs, obj_type=ObjectTypes.modifiers)


def _package_managers(repo_dirs=None):
    """Get the package managers singleton RepoPath instance for Ramble."""
    return _gen_path(repo_dirs=repo_dirs, obj_type=ObjectTypes.package_managers)


def _base_apps(repo_dirs=None):
    """Get the base applications singleton RepoPath instance for Ramble."""
    return _gen_path(repo_dirs=repo_dirs, obj_type=ObjectTypes.base_applications)


def _base_mods(repo_dirs=None):
    """Get the base modifiers singleton RepoPath instance for Ramble."""
    return _gen_path(repo_dirs=repo_dirs, obj_type=ObjectTypes.base_modifiers)


def _base_package_managers(repo_dirs=None):
    """Get the base package managers singleton RepoPath instance for Ramble."""
    return _gen_path(repo_dirs=repo_dirs, obj_type=ObjectTypes.base_package_managers)


paths = {
    ObjectTypes.applications: llnl.util.lang.Singleton(_apps),
    ObjectTypes.modifiers: llnl.util.lang.Singleton(_mods),
    ObjectTypes.package_managers: llnl.util.lang.Singleton(_package_managers),
    ObjectTypes.base_applications: llnl.util.lang.Singleton(_base_apps),
    ObjectTypes.base_modifiers: llnl.util.lang.Singleton(_base_mods),
    ObjectTypes.base_package_managers: llnl.util.lang.Singleton(_base_package_managers),
}

#####################################
#     END TYPE SPECIFIC FUNCTIONALITY
#####################################


def _gen_path(repo_dirs=None, obj_type=default_type):
    """Create a RepoPath for a specific object, add it to sys.meta_path, and return it."""
    section_name = type_definitions[obj_type]["config_section"]
    singular_name = type_definitions[obj_type]["singular"]
    repo_dirs = repo_dirs or ramble.config.get(section_name)
    if not repo_dirs:
        raise NoRepoConfiguredError(
            f"Ramble configuration contains no {singular_name} repositories."
        )

    path = RepoPath(*repo_dirs, object_type=obj_type)
    sys.meta_path.append(path)
    return path


def list_object_files(obj_inst, object_type):
    """List object file paths of the given object along the inheritance chain.

    This is currently used by `ramble deployment` to copy relevant files
    to create a self-contained repo.
    """
    type_def = type_definitions[object_type]
    base_type = ObjectTypes[f"base_{type_def['dir_name']}"]
    base_type_def = type_definitions[base_type]

    repo_path = paths[object_type]
    base_repo_path = paths[base_type]
    obj_file = obj_inst._file_path
    result = [(type_def["dir_name"], obj_file)]
    base_chain = obj_inst.__class__.__mro__[1:]

    for cls in base_chain:
        path = importlib.util.find_spec(cls.__module__).origin

        if not repo_path.in_path(path) and not base_repo_path.in_path(path):
            # Stop upon hitting a non-repo file
            break

        basename = os.path.basename(path)
        if basename == type_def["file_name"]:
            result.append((type_def["dir_name"], path))
        elif basename == base_type_def["file_name"]:
            result.append((base_type_def["dir_name"], path))
        else:
            break
    return result


def all_object_names(object_type=default_type):
    """Convenience wrapper around ``ramble.repository.all_object_names()``."""  # noqa: E501
    return paths[object_type].all_object_names()


def get(spec, object_type=default_type):
    """Convenience wrapper around ``ramble.repository.get()``."""
    return paths[object_type].get(spec)


def set_path(repo, object_type=default_type):
    """Set the path singleton to a specific value.

    Overwrite ``path`` and register it as an importer in
    ``sys.meta_path`` if it is a ``Repo`` or ``RepoPath``.
    """
    global paths
    paths[object_type] = repo

    # make the new repo_path an importer if needed
    append = isinstance(repo, (Repo, RepoPath))
    if append:
        sys.meta_path.append(repo)
    return append


@contextlib.contextmanager
def additional_repository(repository, object_type=default_type):
    """Adds temporarily a repository to the default one.

    Args:
        repository: repository to be added
    """
    paths[object_type].put_first(repository)
    yield
    paths[object_type].remove(repository)


@contextlib.contextmanager
def use_repositories(*paths_and_repos, object_type=default_type):
    """Use the repositories passed as arguments within the context manager.

    Args:
        *paths_and_repos: paths to the repositories to be used, or
            already constructed Repo objects

    Returns:
        Corresponding RepoPath object
    """
    global paths

    # Construct a temporary RepoPath object from
    temporary_repositories = RepoPath(*paths_and_repos, object_type=object_type)

    # Swap the current repository out
    saved = paths[object_type]
    remove_from_meta = set_path(temporary_repositories, object_type=object_type)

    yield temporary_repositories

    # Restore _path and sys.meta_path
    if remove_from_meta:
        sys.meta_path.remove(temporary_repositories)
    paths[object_type] = saved


def autospec(function):
    """Decorator that automatically converts the first argument of a
    function to a Spec.
    """

    @functools.wraps(function)
    def converter(self, spec_like, *args, **kwargs):
        if not isinstance(spec_like, ramble.spec.Spec):
            spec_like = ramble.spec.Spec(spec_like)
        return function(self, spec_like, *args, **kwargs)

    return converter


class ObjectNamespace(types.ModuleType):
    """Allow lazy loading of modules."""

    def __init__(self, namespace):
        super().__init__(namespace)
        self.__file__ = "(ramble namespace)"
        self.__path__ = []
        self.__name__ = namespace
        self.__application__ = namespace
        self.__modules = {}

    def __getattr__(self, name):
        """Getattr lazily loads modules if they're not already loaded."""
        submodule = self.__application__ + "." + name
        setattr(self, name, __import__(submodule))
        return getattr(self, name)


class FastObjectChecker(Mapping):
    """Cache that maps object names to the stats obtained on the
    '.py' files associated with them.

    For each repository a cache is maintained at class level, and shared among
    all instances referring to it. Update of the global cache is done lazily
    during instance initialization.
    """

    #: Global cache, reused by every instance
    _paths_cache = {}

    def __init__(self, objects_path, object_file_name, object_type):
        # The path of the repository managed by this instance
        self.objects_path = objects_path
        self.object_file_name = object_file_name
        self.object_type = object_type

        # If the cache we need is not there yet, then build it appropriately
        if objects_path not in self._paths_cache:
            self._paths_cache[objects_path] = self._create_new_cache()

        #: Reference to the appropriate entry in the global cache
        self._objects_to_stats = self._paths_cache[objects_path]

    def invalidate(self):
        """Regenerate cache for this checker."""
        self._paths_cache[self.objects_path] = self._create_new_cache()
        self._objects_to_stats = self._paths_cache[self.objects_path]

    def _create_new_cache(self):
        """Create a new cache for objects in a repo.

        The implementation here should try to minimize filesystem
        calls.  At the moment, it is O(number of objects) and makes
        about one stat call per object.  This is reasonably fast, and
        avoids actually importing objects in Ramble, which is slow.
        """
        # Create a dictionary that will store the mapping between a
        # object name and its stat info
        cache = {}
        for obj_name in os.listdir(self.objects_path):
            # Skip non-directories in the object root.
            obj_dir = os.path.join(self.objects_path, obj_name)

            # Warn about invalid names that look like objects.
            if not nm.valid_module_name(obj_name):
                if not obj_name.startswith(".") and not any(
                    obj_name in obj_info["accepted_configs"]
                    for obj_info in type_definitions.values()
                ):
                    logger.warn(
                        f"Skipping {self.object_type} "
                        f'at {obj_dir}. "{obj_name}" is not '
                        "a valid Ramble module name."
                    )
                continue

            # Construct the file name from the directory
            obj_file = os.path.join(self.objects_path, obj_name, self.object_file_name)

            # Use stat here to avoid lots of calls to the filesystem.
            try:
                sinfo = os.stat(obj_file)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # No application.py file here.
                    continue
                elif e.errno == errno.EACCES:
                    logger.warn(f"Can't read {self.object_type} file {obj_file}.")
                    continue
                raise e

            # If it's not a file, skip it.
            if stat.S_ISDIR(sinfo.st_mode):
                continue

            # If it is a file, then save the stats under the
            # appropriate key
            cache[obj_name] = sinfo

        return cache

    def last_mtime(self):
        return max(sinfo.st_mtime for sinfo in self._objects_to_stats.values())

    def __getitem__(self, item):
        return self._objects_to_stats[item]

    def __iter__(self):
        return iter(self._objects_to_stats)

    def __len__(self):
        return len(self._objects_to_stats)


class TagIndex(Mapping):
    """Maps tags to list of applications."""

    def __init__(self, object_type=default_type):
        self.object_type = object_type
        self._tag_dict = collections.defaultdict(list)

    def to_json(self, stream):
        sjson.dump({"tags": self._tag_dict}, stream)

    @staticmethod
    def from_json(stream, object_type):
        d = sjson.load(stream)

        r = TagIndex(object_type=object_type)

        for tag, list in d["tags"].items():
            r[tag].extend(list)

        return r

    def __getitem__(self, item):
        return self._tag_dict[item]

    def __iter__(self):
        return iter(self._tag_dict)

    def __len__(self):
        return len(self._tag_dict)

    def update_object(self, obj_name):
        """Updates an object in the tag index.

        Args:
            obj_name (str): name of the object to be removed from the
            index

        """
        obj = paths[self.object_type].get(obj_name)

        # Remove the object from the list of objects, if present
        for obj_list in self._tag_dict.values():
            if obj_name in obj_list:
                obj_list.remove(obj_name)

        # Add it again under the appropriate tags
        for tag in getattr(obj, "tags", []):
            tag = tag.lower()
            self._tag_dict[tag].append(obj.name)


class Indexer(metaclass=abc.ABCMeta):
    """Adaptor for indexes that need to be generated when repos are updated."""

    def __init__(self, object_type=default_type):
        self.object_type = object_type

    def create(self):
        self.index = self._create()

    def set_object_type(self, object_type):
        self.object_type = object_type

    @abc.abstractmethod
    def _create(self):
        """Create an empty index and return it."""

    def needs_update(self, pkg):
        """Whether an update is needed when the application file hasn't changed.

        Returns:
            (bool): ``True`` if this application needs its index
                updated, ``False`` otherwise.

        We already automatically update indexes when object files
        change, but other files (like patches) may change underneath the
        object file. This method can be used to check additional
        object-specific files whenever they're loaded, to tell the
        RepoIndex to update the index *just* for that object.

        """
        return False

    @abc.abstractmethod
    def read(self, stream):
        """Read this index from a provided file object."""

    @abc.abstractmethod
    def update(self, obj_fullname):
        """Update the index in memory with information about an object."""

    @abc.abstractmethod
    def write(self, stream):
        """Write the index to a file object."""


class TagIndexer(Indexer):
    """Lifecycle methods for a TagIndex on a Repo."""

    def _create(self):
        return TagIndex(object_type=self.object_type)

    def read(self, stream):
        self.index = TagIndex.from_json(stream, self.object_type)

    def update(self, obj_fullname):
        self.index.update_object(obj_fullname)

    def write(self, stream):
        self.index.to_json(stream)


class RepoIndex:
    """Container class that manages a set of Indexers for a Repo.

    This class is responsible for checking objects in a repository for
    updates (using ``FastObjectChecker``) and for regenerating indexes
    when they're needed.

    ``Indexers`` should be added to the ``RepoIndex`` using
    ``add_index(name, indexer)``, and they should support the interface
    defined by ``Indexer``, so that the ``RepoIndex`` can read, generate,
    and update stored indices.

    Generated indexes are accessed by name via ``__getitem__()``.

    """

    def __init__(self, object_checker, namespace, object_type=default_type):
        self.checker = object_checker
        self.objects_path = self.checker.objects_path
        self.namespace = namespace
        self.object_type = object_type

        self.indexers = {}
        self.indexes = {}

    def add_indexer(self, name, indexer):
        """Add an indexer to the repo index.

        Arguments:
            name (str): name of this indexer

            indexer (object): an object that supports create(), read(),
                write(), and get_index() operations

        """
        self.indexers[name] = indexer

    def __getitem__(self, name):
        """Get the index with the specified name, reindexing if needed."""
        indexer = self.indexers.get(name)
        if not indexer:
            raise KeyError("no such index: %s" % name)

        if name not in self.indexes:
            self._build_all_indexes()

        return self.indexes[name]

    def _build_all_indexes(self):
        """Build all the indexes at once.

        We regenerate *all* indexes whenever *any* index needs an update,
        because the main bottleneck here is loading all the objects. It
        can take tens of seconds to regenerate sequentially, and we'd rather
        only pay that cost once rather than on several invocations.

        """
        for name, indexer in self.indexers.items():
            self.indexes[name] = self._build_index(name, indexer)

    def _build_index(self, name, indexer):
        """Determine which objects need an update, and update indexes."""

        # Filename of the provider index cache (we assume they're all json)
        cache_filename = f"{name}/{self.namespace}-index.json"

        # Compute which objects needs to be updated in the cache
        misc_cache = ramble.caches.misc_cache
        index_mtime = misc_cache.mtime(cache_filename)

        needs_update = [x for x, sinfo in self.checker.items() if sinfo.st_mtime > index_mtime]

        index_existed = misc_cache.init_entry(cache_filename)
        if index_existed and not needs_update:
            # If the index exists and doesn't need an update, read it
            with misc_cache.read_transaction(cache_filename) as f:
                indexer.read(f)

        else:
            # Otherwise update it and rewrite the cache file
            with misc_cache.write_transaction(cache_filename) as (old, new):
                indexer.read(old) if old else indexer.create()

                for obj_name in needs_update:
                    namespaced_name = f"{self.namespace}.{obj_name}"
                    indexer.update(namespaced_name)

                indexer.write(new)

        return indexer.index


class RepoPath:
    """A RepoPath is a list of repos that function as one.

    It functions exactly like a Repo, but it operates on the combined
    results of the Repos in its list instead of on a single object
    repository.

    Args:
        repos (list): list Repo objects or paths to put in this RepoPath
    """

    def __init__(self, *repos, object_type=default_type):
        self.repos = []
        self.by_namespace = nm.NamespaceTrie()
        self.object_abbrev = type_definitions[object_type]["abbrev"]

        self.base_namespace = f"{global_namespace}.{self.object_abbrev}"

        self._all_object_names = None

        # Add each repo to this path.
        for repo in repos:
            try:
                if isinstance(repo, str):
                    repo = Repo(repo, object_type=object_type)
                self.put_last(repo)
            except RepoError as e:
                logger.warn(
                    "Failed to initialize repository: '%s'." % repo,
                    e.message,
                    "To remove the bad repository, run this command:",
                    "    ramble repo rm %s" % repo,
                )

    def put_first(self, repo):
        """Add repo first in the search path."""
        if isinstance(repo, RepoPath):
            for r in reversed(repo.repos):
                self.put_first(r)
            return

        self.repos.insert(0, repo)
        self.by_namespace[repo.full_namespace] = repo

    def put_last(self, repo):
        """Add repo last in the search path."""
        if isinstance(repo, RepoPath):
            for r in repo.repos:
                self.put_last(r)
            return

        self.repos.append(repo)

        # don't mask any higher-precedence repos with same namespace
        if repo.full_namespace not in self.by_namespace:
            self.by_namespace[repo.full_namespace] = repo

    def remove(self, repo):
        """Remove a repo from the search path."""
        if repo in self.repos:
            self.repos.remove(repo)

    def get_full_namespace(self, namespace):
        """Returns the full namespace of a repository, given its relative one."""
        return f"{self.base_namespace}.{namespace}"

    def get_repo(self, namespace, default=NOT_PROVIDED):
        """Get a repository by namespace.

        Arguments:

            namespace:

                Look up this namespace in the RepoPath, and return it if found.

        Optional Arguments:

            default:

                If default is provided, return it when the namespace
                isn't found.  If not, raise an UnknownNamespaceError.
        """
        full_namespace = self.get_full_namespace(namespace)
        if full_namespace not in self.by_namespace:
            if default == NOT_PROVIDED:
                raise UnknownNamespaceError(namespace)
            return default
        return self.by_namespace[full_namespace]

    def first_repo(self):
        """Get the first repo in precedence order."""
        return self.repos[0] if self.repos else None

    def all_object_names(self):
        """Return all unique object names in all repositories."""
        if self._all_object_names is None:
            all_objs = set()
            for repo in self.repos:
                for name in repo.all_object_names():
                    all_objs.add(name)
            self._all_object_names = sorted(all_objs, key=lambda n: n.lower())
        return self._all_object_names

    def objects_with_tags(self, *tags):
        r = set()
        for repo in self.repos:
            r |= set(repo.objects_with_tags(*tags))
        return sorted(r)

    def all_objects(self):
        for name in self.all_object_names():
            yield self.get(name)

    def all_object_classes(self):
        for name in self.all_object_names():
            yield self.get_obj_class(name)

    def find_module(self, fullname, path=None):
        """Implements precedence for overlaid namespaces.

        Loop checks each namespace in self.repos for objects, and
        also handles loading empty containing namespaces.

        """
        # namespaces are added to repo, and object modules are leaves.
        namespace, dot, module_name = fullname.rpartition(".")

        # If it's a module in some repo, or if it is the repo's
        # namespace, let the repo handle it.
        for repo in self.repos:
            if namespace == repo.full_namespace:
                if repo.real_name(module_name):
                    return repo
            elif fullname == repo.full_namespace:
                return repo

        # No repo provides the namespace, but it is a valid prefix of
        # something in the RepoPath.
        if self.by_namespace.is_prefix(fullname):
            return self

        return None

    def load_module(self, fullname):
        """Handles loading container namespaces when necessary.

        See ``Repo`` for how actual object modules are loaded.
        """
        if fullname in sys.modules:
            return sys.modules[fullname]

        if not self.by_namespace.is_prefix(fullname):
            raise ImportError("No such ramble repo: %s" % fullname)

        module = ObjectNamespace(fullname)
        module.__loader__ = self
        sys.modules[fullname] = module
        return module

    def last_mtime(self):
        """Time a object file in this repo was last updated."""
        return max(repo.last_mtime() for repo in self.repos)

    def repo_for_obj(self, spec):
        """Given a spec, get the repository for its object."""
        # We don't @_autospec this function b/c it's called very frequently
        # and we want to avoid parsing str's into Specs unnecessarily.
        logger.debug(f"Getting repo for obj {spec}")
        namespace = None
        if isinstance(spec, ramble.spec.Spec):
            namespace = spec.namespace
            name = spec.name
        else:
            # handle strings directly for speed instead of @_autospec'ing
            namespace, _, name = spec.rpartition(".")

        logger.debug(f" Name and namespace = {namespace} - {name}")
        # If the spec already has a namespace, then return the
        # corresponding repo if we know about it.
        if namespace:
            fullspace = self.get_full_namespace(namespace)
            if fullspace not in self.by_namespace:
                raise UnknownNamespaceError(spec.namespace)
            return self.by_namespace[fullspace]

        # If there's no namespace, search in the RepoPath.
        for repo in self.repos:
            if name in repo:
                logger.debug("Found repo...")
                return repo

        # If the object isn't in any repo, return the one with
        # highest precedence.  This is for commands like `ramble edit`
        # that can operate on objects that don't exist yet.
        return self.first_repo()

    @autospec
    def get(self, spec):
        """Returns the object associated with the supplied spec."""
        return self.repo_for_obj(spec).get(spec)

    def get_obj_class(self, obj_name):
        """Find a class for the spec's object and return the class object."""  # noqa: E501
        return self.repo_for_obj(obj_name).get_obj_class(obj_name)

    @autospec
    def dump_provenance(self, spec, path):
        """Dump provenance information for a spec to a particular path.

        This dumps the object file and any associated patch files.
        Raises UnknownObjectError if not found.
        """
        return self.repo_for_obj(spec).dump_provenance(spec, path)

    def dirname_for_object_name(self, obj_name):
        return self.repo_for_obj(obj_name).dirname_for_object_name(obj_name)

    def filename_for_object_name(self, obj_name):
        return self.repo_for_obj(obj_name).filename_for_object_name(obj_name)

    def exists(self, obj_name):
        """Whether object with the give name exists in the path's repos.

        Note that virtual objects do not "exist".
        """
        return any(repo.exists(obj_name) for repo in self.repos)

    def in_path(self, maybe_obj_path):
        """Whether the path belongs to any of the repos."""
        return any(os.path.commonprefix([maybe_obj_path, r.root]) == r.root for r in self.repos)

    # TODO: DWJ - Maybe we don't need this? Are we going to have virtual
    #             objects
    # def is_virtual(self, obj_name, use_index=True):
    #     """True if the object with this name is virtual,
    #        False otherwise.
    #
    #     Set `use_index` False when calling from a code block that could
    #     be run during the computation of the provider index."""
    #     have_name = obj_name is not None
    #     if have_name and not isinstance(obj_name, str):
    #         raise ValueError(
    #             "is_virtual(): expected object name, got %s" %
    #             type(obj_name))
    #     if use_index:
    #         return have_name and app_name in self.provider_index
    #     else:
    #         return have_name and (not self.exists(app_name) or
    #                               self.get_app_class(app_name).virtual)

    def __contains__(self, obj_name):
        return self.exists(obj_name)


class Repo:
    """Class representing a object repository in the filesystem.

    Each object repository must have a top-level configuration file
    called `repo.yaml`.

    Currently, `repo.yaml` this must define:

    `namespace`:
        A Python namespace where the repository's objects should live.

    """

    def __init__(self, root, object_type=default_type):
        """Instantiate an object repository from a filesystem path.

        Args:
            root: the root directory of the repository
        """
        # Root directory, containing _repo.yaml and object dirs
        # Allow roots to be ramble-relative by starting with '$ramble'
        self.root = ramble.util.path.canonicalize_path(root)
        self.object_file_name = type_definitions[object_type]["file_name"]
        self.object_type = object_type
        self.object_abbrev = type_definitions[object_type]["abbrev"]
        self.base_namespace = f"{global_namespace}.{self.object_abbrev}"

        # check and raise BadRepoError on fail.
        def check(condition, msg):
            if not condition:
                raise BadRepoError(msg)

        # Validate repository layout.
        self.config_name = None
        self.config_file = None
        for config in type_definitions[object_type]["accepted_configs"]:
            config_file = os.path.join(self.root, config)
            if os.path.exists(config_file):
                self.config_name = config
                self.config_file = config_file
        check(self.config_file, "No valid config file found")
        check(os.path.isfile(self.config_file), f"No {self.config_name} found in '{root}'")

        # Read configuration and validate namespace
        config = self._read_config()
        check(
            "namespace" in config,
            "%s must define a namespace." % os.path.join(root, self.config_name),
        )

        self.namespace = config["namespace"]
        check(
            re.match(r"[a-zA-Z][a-zA-Z0-9_.]+", self.namespace),
            (f"Invalid namespace '{self.namespace}' in repo '{self.root}'. ")
            + "Namespaces must be valid python identifiers separated by '.'",
        )

        objects_dir = (
            config["subdirectory"]
            if "subdirectory" in config
            else type_definitions[object_type]["dir_name"]
        )

        self.objects_path = os.path.join(self.root, objects_dir)
        check(
            os.path.isdir(self.objects_path),
            f"No directory '{objects_dir}' found in '{root}'",
        )

        # Set up 'full_namespace' to include the super-namespace
        self.full_namespace = f"{self.base_namespace}.{self.namespace}"

        # Keep name components around for checking prefixes.
        self._names = self.full_namespace.split(".")

        # These are internal cache variables.
        self._modules = {}
        self._classes = {}
        self._instances = {}

        # Maps that goes from object name to corresponding file stat
        self._fast_object_checker = None

        # Indexes for this repository, computed lazily
        self._repo_index = None

        # make sure the namespace for objects in this repo exists.
        self._create_namespace()

    def _create_namespace(self):
        """Create this repo's namespace module and insert it into sys.modules.

        Ensures that modules loaded via the repo have a home, and that
        we don't get runtime warnings from Python's module system.

        """
        parent = None
        for i in range(1, len(self._names) + 1):
            ns = ".".join(self._names[:i])

            if ns not in sys.modules:
                module = ObjectNamespace(ns)
                module.__loader__ = self
                sys.modules[ns] = module

                # TODO: DWJ - Do we need this?
                # Ensure the namespace is an attribute of its parent,
                # if it has not been set by something else already.
                #
                # This ensures that we can do things like:
                #    import ramble.app.builtin.mpich as mpich
                if parent:
                    modname = self._names[i - 1]
                    setattr(parent, modname, module)
            else:
                # no need to set up a module
                module = sys.modules[ns]

            # but keep track of the parent in this loop
            parent = module

    def real_name(self, import_name):
        """Allow users to import Ramble objects using Python identifiers.

        A python identifier might map to many different Ramble object
        names due to hyphen/underscore ambiguity.

        Easy example:
            num3proxy   -> 3proxy

        Ambiguous:
            foo_bar -> foo_bar, foo-bar

        More ambiguous:
            foo_bar_baz -> foo_bar_baz, foo-bar-baz, foo_bar-baz, foo-bar_baz
        """
        if import_name in self:
            return import_name

        options = nm.possible_ramble_module_names(import_name)
        options.remove(import_name)
        for name in options:
            if name in self:
                return name
        return None

    def is_prefix(self, fullname):
        """True if fullname is a prefix of this Repo's namespace."""
        parts = fullname.split(".")
        return self._names[: len(parts)] == parts

    def find_module(self, fullname, path=None):
        """Python find_module import hook.

        Returns this Repo if it can load the module; None if not.
        """
        if self.is_prefix(fullname):
            return self

        namespace, dot, module_name = fullname.rpartition(".")
        if namespace == self.full_namespace:
            if self.real_name(module_name):
                return self

        return None

    def load_module(self, fullname):
        """Python importer load hook.

        Tries to load the module; raises an ImportError if it can't.
        """
        if fullname in sys.modules:
            return sys.modules[fullname]

        namespace, dot, module_name = fullname.rpartition(".")

        if self.is_prefix(fullname):
            module = ObjectNamespace(fullname)

        elif namespace == self.full_namespace:
            real_name = self.real_name(module_name)
            if not real_name:
                raise ImportError(f"No module {module_name} in {self}")
            module = self._get_obj_module(real_name)

        else:
            raise ImportError(f"No module {fullname} in {self}")

        module.__loader__ = self
        sys.modules[fullname] = module
        if namespace != fullname:
            parent = sys.modules[namespace]
            if not hasattr(parent, module_name):
                setattr(parent, module_name, module)

        return module

    def _read_config(self):
        """Check for a YAML config file in this db's root directory."""
        try:
            with open(self.config_file) as reponame_file:
                yaml_data = yaml.load(reponame_file)

                if (
                    not yaml_data
                    or "repo" not in yaml_data
                    or not isinstance(yaml_data["repo"], dict)
                ):
                    logger.die(f"Invalid {self.config_name} in repository {self.root}")

                return yaml_data["repo"]

        except OSError:
            logger.die(f"Error reading {self.config_file} when opening {self.root}")

    @autospec
    def get(self, spec):
        """Returns the object associated with the supplied spec."""
        # NOTE: we only check whether the object is None here, not whether
        # it actually exists, because we have to load it anyway, and that ends
        # up checking for existence. We avoid constructing
        # FastObjectChecker, which will stat all objects.
        logger.debug(f"Getting obj {spec} from repo")
        if spec.name is None:
            raise UnknownObjectError(None, self)

        if spec.namespace and spec.namespace != self.namespace:
            raise UnknownObjectError(spec.name, self.namespace)

        object_class = self.get_obj_class(spec.name)
        try:
            return object_class(self.object_path(spec))
        except ramble.error.RambleError:
            # pass these through as their error messages will be fine.
            raise
        except Exception as e:
            logger.debug(e)

            # Make sure other errors in constructors hit the error
            # handler by wrapping them
            if ramble.config.get("config:debug"):
                sys.excepthook(*sys.exc_info())
            raise FailedConstructorError(spec.fullname, *sys.exc_info())

    @autospec
    def dump_provenance(self, spec, path):
        """Dump provenance information for a spec to a particular path.

        This dumps the object file.
        Raises UnknownObjectError if not found.
        """
        if spec.namespace and spec.namespace != self.namespace:
            raise UnknownObjectError(
                f"Repository {self.namespace} does not "
                f"contain {self.object_type.name} {spec.fullname}."
            )

        # Install the object's .py file itself.
        fs.install(self.filename_for_object_name(spec.name), path)

    def purge(self):
        """Clear entire object instance cache."""
        self._instances.clear()

    @property
    def index(self):
        """Construct the index for this repo lazily."""
        if self._repo_index is None:
            self._repo_index = RepoIndex(self._obj_checker, self.namespace, self.object_type)
            self._repo_index.add_indexer("tags", TagIndexer(self.object_type))
        return self._repo_index

    @property
    def tag_index(self):
        """Index of tags and which objects they're defined on."""
        return self.index["tags"]

    def dirname_for_object_name(self, obj_name):
        """Get the directory name for a particular object.  This is the
        directory that contains its object.py file."""
        return os.path.join(self.objects_path, obj_name)

    def filename_for_object_name(self, obj_name):
        """Get the filename for the module we should load for a particular
        object.  objects for a Repo live in
        ``$root/<object_name>/<object_type>.py``

        This will return a proper <object_type>.py path even if the
        object doesn't exist yet, so callers will need to ensure
        the object exists before importing.
        """
        obj_dir = self.dirname_for_object_name(obj_name)
        return os.path.join(obj_dir, self.object_file_name)

    @autospec
    def object_path(self, spec):
        return os.path.join(
            self.objects_path,
            self.dirname_for_object_name(spec.name),
            self.filename_for_object_name(spec.name),
        )

    @property
    def _obj_checker(self):
        if self._fast_object_checker is None:
            self._fast_object_checker = FastObjectChecker(
                self.objects_path, self.object_file_name, self.object_type.name
            )
        return self._fast_object_checker

    def all_object_names(self):
        """Returns a sorted list of all object names in the Repo."""
        names = sorted(self._obj_checker.keys())
        return names

    def objects_with_tags(self, *tags):
        v = set(self.all_object_names())
        index = self.tag_index

        for t in tags:
            t = t.lower()
            v &= set(index[t])

        return sorted(v)

    def all_objects(self):
        """Iterator over all objects in the repository.

        Use this with care, because loading objects is slow.

        """
        for name in self.all_object_names():
            yield self.get(name)

    def all_object_classes(self):
        """Iterator over all object *classes* in the repository.

        Use this with care, because loading objects is slow.
        """
        for name in self.all_object_names():
            yield self.get_obj_class(name)

    def exists(self, obj_name):
        """Whether a object with the supplied name exists."""
        if obj_name is None:
            return False

        # if the FastObjectChecker is already constructed, use it
        if self._fast_object_checker:
            return obj_name in self._obj_checker

        # if not, check for the object.py file
        path = self.filename_for_object_name(obj_name)
        return os.path.exists(path)

    def last_mtime(self):
        """Time a object file in this repo was last updated."""
        return self._obj_checker.last_mtime()

    def _get_obj_module(self, obj_name):
        """Create a module for a particular object.

        This caches the module within this Repo *instance*.  It does
        *not* add it to ``sys.modules``.  So, you can construct
        multiple Repos for testing and ensure that the module will be
        loaded once per repo.

        """
        if obj_name not in self._modules:
            file_path = self.filename_for_object_name(obj_name)

            if not os.path.exists(file_path):
                raise UnknownObjectError(obj_name, self)

            if not os.path.isfile(file_path):
                logger.die(f"Something's wrong. '{file_path}' is not a file!")

            if not os.access(file_path, os.R_OK):
                logger.die(f"Cannot read '{file_path}'!")

            # e.g., ramble.app.builtin.mpich
            fullname = f"{self.full_namespace}.{obj_name}"

            try:
                module = ramble.util.imp.load_source(fullname, file_path)
            except SyntaxError as e:
                # SyntaxError strips the path from the filename so we need to
                # manually construct the error message in order to give the
                # user the correct .py where the syntax error is
                # located
                raise SyntaxError(f"invalid syntax in {file_path}, line {e.lineno}")

            module.__object__ = self.full_namespace
            module.__loader__ = self
            self._modules[obj_name] = module

        return self._modules[obj_name]

    def get_obj_class(self, obj_name):
        """Get the class for the object out of its module.

        First loads (or fetches from cache) a module for the
        object. Then extracts the object class from the module
        according to Ramble's naming convention.
        """
        namespace, _, obj_name = obj_name.rpartition(".")
        if namespace and (namespace != self.namespace):
            raise InvalidNamespaceError(
                f"Invalid namespace for {self.namespace} repo: {namespace}"
            )

        class_name = nm.mod_to_class(obj_name)
        logger.debug(f" Class name = {class_name}")
        module = self._get_obj_module(obj_name)

        cls = getattr(module, class_name)
        if not inspect.isclass(cls):
            logger.die(f"{obj_name}.{class_name} is not a class")

        return cls

    def __str__(self):
        return f"[Repo '{self.namespace}' at '{self.root}']"

    def __repr__(self):
        return self.__str__()

    def __contains__(self, obj_name):
        return self.exists(obj_name)


def create_repo(
    root,
    namespace=None,
    subdir=type_definitions[default_type]["dir_name"],
    object_type=default_type,
    unified_repo=True,
):
    """Create a new repository in root with the specified namespace.

    If the namespace is not provided, use basename of root.
    Return the canonicalized path and namespace of the created repository.
    """
    root = ramble.util.path.canonicalize_path(root)
    if not namespace:
        namespace = os.path.basename(root)

    if not re.match(r"\w[\.\w-]*", namespace):
        raise InvalidNamespaceError("'%s' is not a valid namespace." % namespace)

    existed = False
    if os.path.exists(root):
        if os.path.isfile(root):
            raise BadRepoError("File %s already exists and is not a directory" % root)
        elif os.path.isdir(root):
            if not os.access(root, os.R_OK | os.W_OK):
                raise BadRepoError("Cannot create new repo in %s: cannot access directory." % root)
            if os.listdir(root):
                raise BadRepoError("Cannot create new repo in %s: directory is not empty." % root)
        existed = True

    full_path = os.path.realpath(root)
    parent = os.path.dirname(full_path)
    if not os.access(parent, os.R_OK | os.W_OK):
        raise BadRepoError("Cannot create repository in %s: can't access parent!" % root)

    try:
        object_dirs = []
        if unified_repo:
            # If unified, and no subdir, create obj dirs
            # If unified and subdir, create subdir
            # If not unified and no subdir, create obj dir
            # If not unified and subdir, create subdir
            config_name = unified_config
            for obj_type in type_definitions.values():
                objects_path = os.path.join(root, obj_type["dir_name"])
                object_dirs.append(objects_path)
        else:
            config_name = type_definitions[object_type]["accepted_configs"][0]
            objects_path = os.path.join(root, type_definitions[object_type]["dir_name"])
            object_dirs.append(objects_path)

        if subdir is not None:
            object_dirs = [os.path.join(root, subdir)]

        for objects_path in object_dirs:
            fs.mkdirp(objects_path)

        config_path = os.path.join(root, config_name)
        with open(config_path, "w") as config:
            config.write("repo:\n")
            config.write(f"  namespace: '{namespace}'\n")
            if subdir is not None:
                config.write(f"  subdirectory: '{subdir}'\n")

    except OSError as e:
        # try to clean up.
        if existed:
            shutil.rmtree(config_path, ignore_errors=True)
            if unified_repo:
                for obj_type in type_definitions.values():
                    objects_path = os.path.join(root, obj_type["dir_name"])
                    shutil.rmtree(objects_path, ignore_errors=True)
            else:
                shutil.rmtree(objects_path, ignore_errors=True)
        else:
            shutil.rmtree(root, ignore_errors=True)

        raise BadRepoError(
            "Failed to create new repository in %s." % root, f"Caused by {type(e)}: {e}"
        )

    return full_path, namespace


def create_or_construct(path, namespace=None):
    """Create a repository, or just return a Repo if it already exists."""
    if not os.path.exists(path):
        fs.mkdirp(path)
        create_repo(path, namespace)
    return Repo(path)


def create(configuration, object_type=default_type):
    """Create a RepoPath from a configuration object.

    Args:
        configuration (ramble.config.Configuration): configuration object
    """
    repo_dirs = configuration.get(type_definitions[object_type]["config_section"])
    if not repo_dirs:
        raise NoRepoConfiguredError(
            "Ramble configuration contains no "
            f'{type_definitions[object_type]["singular"]} repositories.'
        )
    return RepoPath(*repo_dirs, object_type=object_type)


class RepositoryNamespace(types.ModuleType):
    """Allow lazy loading of modules."""

    def __init__(self, namespace):
        super().__init__(namespace)
        self.__file__ = "(repository namespace)"
        self.__path__ = []
        self.__name__ = namespace
        self.__package__ = namespace
        self.__modules = {}

    def __getattr__(self, name):
        """Getattr lazily loads modules if they're not already loaded."""
        submodule = self.__package__ + "." + name
        try:
            setattr(self, name, __import__(submodule))
        except ImportError:
            msg = "'{0}' object has no attribute {1}"
            raise AttributeError(msg.format(type(self), name))
        return getattr(self, name)


class _PrependFileLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname, path, prepend=None):
        super().__init__(fullname, path)
        self.prepend = prepend

    def path_stats(self, path):
        stats = super().path_stats(path)
        if self.prepend:
            stats["size"] += len(self.prepend) + 1
        return stats

    def get_data(self, path):
        data = super().get_data(path)
        if path != self.path or self.prepend is None:
            return data
        else:
            return self.prepend.encode() + b"\n" + data


class RepoLoader(_PrependFileLoader):
    """Loads a Python module associated with a object in specific repository"""

    #: Code in ``_object_prepend`` is prepended to imported objects.
    _object_prepend = "from __future__ import absolute_import;"

    def __init__(self, fullname, repo, object_name):
        self.repo = repo
        self.object_name = object_name
        self.object_py = repo.filename_for_object_name(object_name)
        self.fullname = fullname
        super().__init__(self.fullname, self.object_py, prepend=self._object_prepend)


class RepositoryNamespaceLoader:
    def create_module(self, spec):
        return RepositoryNamespace(spec.name)

    def exec_module(self, module):
        module.__loader__ = self


class ReposFinder:
    """MetaPathFinder class that loads a Python module corresponding to an object

    Return a loader based on the inspection of the current global repository list.
    """

    def __init__(self, object_type=default_type):
        self.object_type = object_type

    def find_spec(self, fullname, python_path, target=None):
        # "target" is not None only when calling importlib.reload()
        if target is not None:
            raise RuntimeError(f'cannot reload module "{fullname}"')

        # Preferred API from https://peps.python.org/pep-0451/
        if not fullname.startswith("ramble."):
            return None

        loader = self.compute_loader(fullname)
        if loader is None:
            return None
        return importlib.util.spec_from_loader(fullname, loader)

    def compute_loader(self, fullname):
        # namespaces are added to repo, and object modules are leaves.
        namespace, dot, module_name = fullname.rpartition(".")

        # If it's a module in some repo, or if it is the repo's
        # namespace, let the repo handle it.
        for repo in paths[self.object_type].repos:
            # We are using the namespace of the repo and the repo contains the object
            if namespace == repo.full_namespace:
                # With 2 nested conditionals we can call "repo.real_name" only once
                object_name = repo.real_name(module_name)
                if object_name:
                    return RepoLoader(fullname, repo, object_name)

            # We are importing a full namespace like 'spack.pkg.builtin'
            if fullname == repo.full_namespace:
                return RepositoryNamespaceLoader()

        # No repo provides the namespace, but it is a valid prefix of
        # something in the RepoPath.
        if paths[self.object_type].by_namespace.is_prefix(fullname):
            return RepositoryNamespaceLoader()

        return None


# Add the finders to sys.meta_path
for obj in ObjectTypes:
    obj_finder = ReposFinder(object_type=obj)
    sys.meta_path.append(obj_finder)


class RepoError(ramble.error.RambleError):
    """Superclass for repository-related errors."""


class NoRepoConfiguredError(RepoError):
    """Raised when there are no repositories configured."""


class InvalidNamespaceError(RepoError):
    """Raised when an invalid namespace is encountered."""


class BadRepoError(RepoError):
    """Raised when repo layout is invalid."""


class UnknownEntityError(RepoError):
    """Raised when we encounter a object ramble doesn't have."""


class IndexError(RepoError):
    """Raised when there's an error with an index."""


class UnknownObjectError(UnknownEntityError):
    """Raised when we encounter an object ramble doesn't have."""

    def __init__(self, name, repo=None, object_type="Object"):
        msg = None
        long_msg = None

        if name:
            if repo:
                msg = f"{object_type} '{name}' not found in repository '{repo.root}'"
            else:
                msg = f"{object_type} '{name}' not found."

            # Special handling for specs that may have been intended as
            # filenames: prompt the user to ask whether they intended to write
            # './<name>'.
            if name.endswith(".yaml"):
                long_msg = "Did you mean to specify a filename with './{0}'?"
                long_msg = long_msg.format(name)
        else:
            msg = f"Attempting to retrieve anonymous {object_type}."

        super().__init__(msg, long_msg)
        self.name = name


class UnknownNamespaceError(UnknownEntityError):
    """Raised when we encounter an unknown namespace"""

    def __init__(self, namespace):
        super().__init__("Unknown namespace: %s" % namespace)


class FailedConstructorError(RepoError):
    """Raised when an object's class constructor fails."""

    def __init__(self, name, exc_type, exc_obj, exc_tb, object_type=None):
        super().__init__(
            f"Class constructor failed for {object_type} '%s'." % name,
            "\nCaused by:\n"
            + (f"{exc_type.__name__}: {exc_obj}\n")
            + "".join(traceback.format_tb(exc_tb)),
        )
        self.name = name
