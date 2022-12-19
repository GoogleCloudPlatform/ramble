# Copyright 2022-2023 Google LLC
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
import inspect
import stat
import shutil
import errno

try:
    from collections.abc import Mapping  # novm
except ImportError:
    from collections import Mapping


import six

import ruamel.yaml as yaml

import llnl.util.lang
import llnl.util.tty as tty
import llnl.util.filesystem as fs

import ramble.caches
import ramble.config
import ramble.spec
import ramble.util.path
import ramble.util.naming as nm

import spack.util.spack_json as sjson
import ramble.util.imp

repo_namespace = 'ramble.app'


def get_full_namespace(namespace):
    """Returns the full namespace of a repository, given its relative one."""
    return '{0}.{1}'.format(repo_namespace, namespace)


# Top-level filename for repo config.
repo_config_name = 'repo.yaml'
# Top-level repo directory containing applcations
applications_dir_name = 'applications'
# Filename for applications in a repo.
application_file_name = 'application.py'

#: Guaranteed unused default value for some functions.
NOT_PROVIDED = object()

# TODO: DWJ - We can remove this, since we are making new applications. Then we
#       can *only* import ramble.appkit

#: Code in ``_application_prepend`` is prepended to imported applications.
#:
#: Ramble applications were originally expected to call `from ramble import *`
#: themselves, but it became difficult to manage and imports in the Ramble
#: core the top-level namespace polluted by application symbols this way.  To
#: solve this, the top-level ``ramble`` application contains very few symbols
#: of its own, and importing ``*`` is essentially a no-op.  The common
#: routines and directives that applications need are now in ``ramble.appkit``,
#: and the import system forces packages to automatically include
#: this. This way, old packages that call ``from ramble import *`` will
#: continue to work without modification, but it's no longer required.
_application_prepend = 'from ramble.appkit import *'


def is_application_file(filename):
    """Determine whether we are in an application file from a repo."""
    import ramble.application
    filename_noext = os.path.splitext(filename)[0]
    applicationbase_filename_no_ext = os.path.splitext(
        inspect.getfile(ramble.application.ApplicationBase))[0]
    return (filename_noext != applicationbase_filename_no_ext and
            os.path.basename(filename_noext) == 'application')


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


class RambleNamespace(types.ModuleType):
    """ Allow lazy loading of modules."""

    def __init__(self, namespace):
        super(RambleNamespace, self).__init__(namespace)
        self.__file__ = "(ramble namespace)"
        self.__path__ = []
        self.__name__ = namespace
        self.__application__ = namespace
        self.__modules = {}

    def __getattr__(self, name):
        """Getattr lazily loads modules if they're not already loaded."""
        submodule = self.__application__ + '.' + name
        setattr(self, name, __import__(submodule))
        return getattr(self, name)


class FastApplicationChecker(Mapping):
    """Cache that maps package names to the stats obtained on the
    'application.py' files associated with them.

    For each repository a cache is maintained at class level, and shared among
    all instances referring to it. Update of the global cache is done lazily
    during instance initialization.
    """
    #: Global cache, reused by every instance
    _paths_cache = {}

    def __init__(self, applications_path):
        # The path of the repository managed by this instance
        self.applications_path = applications_path

        # If the cache we need is not there yet, then build it appropriately
        if applications_path not in self._paths_cache:
            self._paths_cache[applications_path] = self._create_new_cache()

        #: Reference to the appropriate entry in the global cache
        self._applications_to_stats = self._paths_cache[applications_path]

    def invalidate(self):
        """Regenerate cache for this checker."""
        self._paths_cache[self.applications_path] = self._create_new_cache()
        self._applications_to_stats = self._paths_cache[self.applications_path]

    def _create_new_cache(self):
        """Create a new cache for applications in a repo.

        The implementation here should try to minimize filesystem
        calls.  At the moment, it is O(number of applications) and makes
        about one stat call per application.  This is reasonably fast, and
        avoids actually importing applications in Ramble, which is slow.
        """
        # Create a dictionary that will store the mapping between a
        # package name and its stat info
        cache = {}
        for app_name in os.listdir(self.applications_path):
            # Skip non-directories in the package root.
            app_dir = os.path.join(self.applications_path, app_name)

            # Warn about invalid names that look like applications.
            if not nm.valid_module_name(app_name):
                if not app_name.startswith('.'):
                    tty.warn('Skipping application at {0}. "{1}" is not '
                             'a valid Ramble module name.'.format(
                                 app_dir, app_name))
                continue

            # Construct the file name from the directory
            app_file = os.path.join(
                self.applications_path, app_name, application_file_name
            )

            # Use stat here to avoid lots of calls to the filesystem.
            try:
                sinfo = os.stat(app_file)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # No application.py file here.
                    continue
                elif e.errno == errno.EACCES:
                    tty.warn("Can't read application file %s." % app_file)
                    continue
                raise e

            # If it's not a file, skip it.
            if stat.S_ISDIR(sinfo.st_mode):
                continue

            # If it is a file, then save the stats under the
            # appropriate key
            cache[app_name] = sinfo

        return cache

    def last_mtime(self):
        return max(
            sinfo.st_mtime for sinfo in self._applications_to_stats.values())

    def __getitem__(self, item):
        return self._applications_to_stats[item]

    def __iter__(self):
        return iter(self._applications_to_stats)

    def __len__(self):
        return len(self._applications_to_stats)


class TagIndex(Mapping):
    """Maps tags to list of applications."""

    def __init__(self):
        self._tag_dict = collections.defaultdict(list)

    def to_json(self, stream):
        sjson.dump({'tags': self._tag_dict}, stream)

    @staticmethod
    def from_json(stream):
        d = sjson.load(stream)

        r = TagIndex()

        for tag, list in d['tags'].items():
            r[tag].extend(list)

        return r

    def __getitem__(self, item):
        return self._tag_dict[item]

    def __iter__(self):
        return iter(self._tag_dict)

    def __len__(self):
        return len(self._tag_dict)

    def update_application(self, app_name):
        """Updates an application in the tag index.

        Args:
            app_name (str): name of the application to be removed from the
            index

        """
        application = path.get(app_name)

        # Remove the application from the list of applications, if present
        for app_list in self._tag_dict.values():
            if app_name in app_list:
                app_list.remove(app_name)

        # Add it again under the appropriate tags
        for tag in getattr(application, 'tags', []):
            tag = tag.lower()
            self._tag_dict[tag].append(application.name)


@six.add_metaclass(abc.ABCMeta)
class Indexer(object):
    """Adaptor for indexes that need to be generated when repos are updated."""

    def create(self):
        self.index = self._create()

    @abc.abstractmethod
    def _create(self):
        """Create an empty index and return it."""

    def needs_update(self, pkg):
        """Whether an update is needed when the application file hasn't changed.

        Returns:
            (bool): ``True`` if this application needs its index
                updated, ``False`` otherwise.

        We already automatically update indexes when application files
        change, but other files (like patches) may change underneath the
        application file. This method can be used to check additional
        application-specific files whenever they're loaded, to tell the
        RepoIndex to update the index *just* for that application.

        """
        return False

    @abc.abstractmethod
    def read(self, stream):
        """Read this index from a provided file object."""

    @abc.abstractmethod
    def update(self, app_fullname):
        """Update the index in memory with information about an application."""

    @abc.abstractmethod
    def write(self, stream):
        """Write the index to a file object."""


class TagIndexer(Indexer):
    """Lifecycle methods for a TagIndex on a Repo."""
    def _create(self):
        return TagIndex()

    def read(self, stream):
        self.index = TagIndex.from_json(stream)

    def update(self, app_fullname):
        self.index.update_application(app_fullname)

    def write(self, stream):
        self.index.to_json(stream)


class RepoIndex(object):
    """Container class that manages a set of Indexers for a Repo.

    This class is responsible for checking packages in a repository for
    updates (using ``FastApplicationChecker``) and for regenerating indexes
    when they're needed.

    ``Indexers`` should be added to the ``RepoIndex`` using
    ``add_index(name, indexer)``, and they should support the interface
    defined by ``Indexer``, so that the ``RepoIndex`` can read, generate,
    and update stored indices.

    Generated indexes are accessed by name via ``__getitem__()``.

    """
    def __init__(self, application_checker, namespace):
        self.checker = application_checker
        self.applications_path = self.checker.applications_path
        self.namespace = namespace

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
            raise KeyError('no such index: %s' % name)

        if name not in self.indexes:
            self._build_all_indexes()

        return self.indexes[name]

    def _build_all_indexes(self):
        """Build all the indexes at once.

        We regenerate *all* indexes whenever *any* index needs an update,
        because the main bottleneck here is loading all the applications. It
        can take tens of seconds to regenerate sequentially, and we'd rather
        only pay that cost once rather than on several invocations.

        """
        for name, indexer in self.indexers.items():
            self.indexes[name] = self._build_index(name, indexer)

    def _build_index(self, name, indexer):
        """Determine which applications need an update, and update indexes."""

        # Filename of the provider index cache (we assume they're all json)
        cache_filename = '{0}/{1}-index.json'.format(name, self.namespace)

        # Compute which applications needs to be updated in the cache
        misc_cache = ramble.caches.misc_cache
        index_mtime = misc_cache.mtime(cache_filename)

        needs_update = [
            x for x, sinfo in self.checker.items()
            if sinfo.st_mtime > index_mtime
        ]

        index_existed = misc_cache.init_entry(cache_filename)
        if index_existed and not needs_update:
            # If the index exists and doesn't need an update, read it
            with misc_cache.read_transaction(cache_filename) as f:
                indexer.read(f)

        else:
            # Otherwise update it and rewrite the cache file
            with misc_cache.write_transaction(cache_filename) as (old, new):
                indexer.read(old) if old else indexer.create()

                for app_name in needs_update:
                    namespaced_name = '%s.%s' % (self.namespace, app_name)
                    indexer.update(namespaced_name)

                indexer.write(new)

        return indexer.index


class RepoPath(object):
    """A RepoPath is a list of repos that function as one.

    It functions exactly like a Repo, but it operates on the combined
    results of the Repos in its list instead of on a single application
    repository.

    Args:
        repos (list): list Repo objects or paths to put in this RepoPath
    """

    def __init__(self, *repos):
        self.repos = []
        self.by_namespace = nm.NamespaceTrie()

        self._all_application_names = None

        # Add each repo to this path.
        for repo in repos:
            try:
                if isinstance(repo, six.string_types):
                    repo = Repo(repo)
                self.put_last(repo)
            except RepoError as e:
                tty.warn("Failed to initialize repository: '%s'." % repo,
                         e.message,
                         "To remove the bad repository, run this command:",
                         "    ramble repo rm %s" % repo)

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
        full_namespace = get_full_namespace(namespace)
        if full_namespace not in self.by_namespace:
            if default == NOT_PROVIDED:
                raise UnknownNamespaceError(namespace)
            return default
        return self.by_namespace[full_namespace]

    def first_repo(self):
        """Get the first repo in precedence order."""
        return self.repos[0] if self.repos else None

    def all_application_names(self):
        """Return all unique application names in all repositories."""
        if self._all_application_names is None:
            all_apps = set()
            for repo in self.repos:
                for name in repo.all_application_names():
                    all_apps.add(name)
            self._all_application_names = sorted(all_apps,
                                                 key=lambda n: n.lower())
        return self._all_application_names

    def applications_with_tags(self, *tags):
        r = set()
        for repo in self.repos:
            r |= set(repo.applications_with_tags(*tags))
        return sorted(r)

    def all_applications(self):
        for name in self.all_application_names():
            yield self.get(name)

    def all_application_classes(self):
        for name in self.all_application_names():
            yield self.get_app_class(name)

    def find_module(self, fullname, path=None):
        """Implements precedence for overlaid namespaces.

        Loop checks each namespace in self.repos for applications, and
        also handles loading empty containing namespaces.

        """
        # namespaces are added to repo, and application modules are leaves.
        namespace, dot, module_name = fullname.rpartition('.')

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

        See ``Repo`` for how actual application modules are loaded.
        """
        if fullname in sys.modules:
            return sys.modules[fullname]

        if not self.by_namespace.is_prefix(fullname):
            raise ImportError("No such ramble repo: %s" % fullname)

        module = RambleNamespace(fullname)
        module.__loader__ = self
        sys.modules[fullname] = module
        return module

    def last_mtime(self):
        """Time a application file in this repo was last updated."""
        return max(repo.last_mtime() for repo in self.repos)

    def repo_for_app(self, spec):
        """Given a spec, get the repository for its application."""
        # We don't @_autospec this function b/c it's called very frequently
        # and we want to avoid parsing str's into Specs unnecessarily.
        tty.debug('Getting repo for app %s' % spec)
        namespace = None
        if isinstance(spec, ramble.spec.Spec):
            namespace = spec.namespace
            name = spec.name
        else:
            # handle strings directly for speed instead of @_autospec'ing
            namespace, _, name = spec.rpartition('.')

        tty.debug(' Name and namespace = %s - %s' % (namespace, name))
        # If the spec already has a namespace, then return the
        # corresponding repo if we know about it.
        if namespace:
            fullspace = get_full_namespace(namespace)
            if fullspace not in self.by_namespace:
                raise UnknownNamespaceError(spec.namespace)
            return self.by_namespace[fullspace]

        # If there's no namespace, search in the RepoPath.
        for repo in self.repos:
            if name in repo:
                tty.debug('Found repo...')
                return repo

        # If the application isn't in any repo, return the one with
        # highest precedence.  This is for commands like `ramble edit`
        # that can operate on applications that don't exist yet.
        return self.first_repo()

    @autospec
    def get(self, spec):
        """Returns the application associated with the supplied spec."""
        return self.repo_for_app(spec).get(spec)

    def get_app_class(self, app_name):
        """Find a class for the spec's application and return the class object."""  # noqa: E501
        return self.repo_for_app(app_name).get_app_class(app_name)

    @autospec
    def dump_provenance(self, spec, path):
        """Dump provenance information for a spec to a particular path.

           This dumps the package file and any associated patch files.
           Raises UnknownApplicationError if not found.
        """
        return self.repo_for_app(spec).dump_provenance(spec, path)

    def dirname_for_application_name(self, app_name):
        return self.repo_for_app(app_name).dirname_for_application_name(
            app_name)

    def filename_for_application_name(self, app_name):
        return self.repo_for_app(app_name).filename_for_application_name(
            app_name)

    def exists(self, app_name):
        """Whether application with the give name exists in the path's repos.

        Note that virtual applications do not "exist".
        """
        return any(repo.exists(app_name) for repo in self.repos)

    # TODO: DWJ - Maybe we don't need this? Are we going to have virtual
    #             applications
    # def is_virtual(self, app_name, use_index=True):
    #     """True if the application with this name is virtual,
    #        False otherwise.
    #
    #     Set `use_index` False when calling from a code block that could
    #     be run during the computation of the provider index."""
    #     have_name = app_name is not None
    #     if have_name and not isinstance(app_name, str):
    #         raise ValueError(
    #             "is_virtual(): expected package name, got %s" %
    #             type(app_name))
    #     if use_index:
    #         return have_name and app_name in self.provider_index
    #     else:
    #         return have_name and (not self.exists(app_name) or
    #                               self.get_app_class(app_name).virtual)

    def __contains__(self, app_name):
        return self.exists(app_name)


class Repo(object):
    """Class representing a package repository in the filesystem.

    Each application repository must have a top-level configuration file
    called `repo.yaml`.

    Currently, `repo.yaml` this must define:

    `namespace`:
        A Python namespace where the repository's applications should live.

    """

    def __init__(self, root):
        """Instantiate an application repository from a filesystem path.

        Args:
            root: the root directory of the repository
        """
        # Root directory, containing _repo.yaml and application dirs
        # Allow roots to be ramble-relative by starting with '$ramble'
        self.root = ramble.util.path.canonicalize_path(root)

        # check and raise BadRepoError on fail.
        def check(condition, msg):
            if not condition:
                raise BadRepoError(msg)

        # Validate repository layout.
        self.config_file = os.path.join(self.root, repo_config_name)
        check(os.path.isfile(self.config_file),
              "No %s found in '%s'" % (repo_config_name, root))

        self.applications_path = os.path.join(self.root, applications_dir_name)
        check(os.path.isdir(self.applications_path),
              "No directory '%s' found in '%s'" % (applications_dir_name,
                                                   root))

        # Read configuration and validate namespace
        config = self._read_config()
        check('namespace' in config, '%s must define a namespace.'
              % os.path.join(root, repo_config_name))

        self.namespace = config['namespace']
        check(re.match(r'[a-zA-Z][a-zA-Z0-9_.]+', self.namespace),
              ("Invalid namespace '%s' in repo '%s'. "
               % (self.namespace, self.root)) +
              "Namespaces must be valid python identifiers separated by '.'")

        # Set up 'full_namespace' to include the super-namespace
        self.full_namespace = get_full_namespace(self.namespace)

        # Keep name components around for checking prefixes.
        self._names = self.full_namespace.split('.')

        # These are internal cache variables.
        self._modules = {}
        self._classes = {}
        self._instances = {}

        # Maps that goes from application name to corresponding file stat
        self._fast_application_checker = None

        # Indexes for this repository, computed lazily
        self._repo_index = None

        # make sure the namespace for applications in this repo exists.
        self._create_namespace()

    def _create_namespace(self):
        """Create this repo's namespace module and insert it into sys.modules.

        Ensures that modules loaded via the repo have a home, and that
        we don't get runtime warnings from Python's module system.

        """
        parent = None
        for i in range(1, len(self._names) + 1):
            ns = '.'.join(self._names[:i])

            if ns not in sys.modules:
                module = RambleNamespace(ns)
                module.__loader__ = self
                sys.modules[ns] = module

                # TODO: DWJ - Do we need this?
                # Ensure the namespace is an atrribute of its parent,
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
        """Allow users to import Ramble applications using Python identifiers.

        A python identifier might map to many different Ramble application
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
        parts = fullname.split('.')
        return self._names[:len(parts)] == parts

    def find_module(self, fullname, path=None):
        """Python find_module import hook.

        Returns this Repo if it can load the module; None if not.
        """
        if self.is_prefix(fullname):
            return self

        namespace, dot, module_name = fullname.rpartition('.')
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

        namespace, dot, module_name = fullname.rpartition('.')

        if self.is_prefix(fullname):
            module = RambleNamespace(fullname)

        elif namespace == self.full_namespace:
            real_name = self.real_name(module_name)
            if not real_name:
                raise ImportError("No module %s in %s" % (module_name, self))
            module = self._get_app_module(real_name)

        else:
            raise ImportError("No module %s in %s" % (fullname, self))

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

                if (not yaml_data or 'repo' not in yaml_data or
                        not isinstance(yaml_data['repo'], dict)):
                    tty.die("Invalid %s in repository %s" % (
                        repo_config_name, self.root))

                return yaml_data['repo']

        except IOError:
            tty.die("Error reading %s when opening %s"
                    % (self.config_file, self.root))

    @autospec
    def get(self, spec):
        """Returns the application associated with the supplied spec."""
        # NOTE: we only check whether the application is None here, not whether
        # it actually exists, because we have to load it anyway, and that ends
        # up checking for existence. We avoid constructing
        # FastApplicationChecker, which will stat all applications.
        tty.debug('Getting app %s from repo' % spec)
        if spec.name is None:
            raise UnknownApplicationError(None, self)

        if spec.namespace and spec.namespace != self.namespace:
            raise UnknownApplicationError(spec.name, self.namespace)

        application_class = self.get_app_class(spec.name)
        try:
            return application_class(spec)
        except ramble.error.RambleError:
            # pass these through as their error messages will be fine.
            raise
        except Exception as e:
            tty.debug(e)

            # Make sure other errors in constructors hit the error
            # handler by wrapping them
            if ramble.config.get('config:debug'):
                sys.excepthook(*sys.exc_info())
            raise FailedConstructorError(spec.fullname, *sys.exc_info())

    @autospec
    def dump_provenance(self, spec, path):
        """Dump provenance information for a spec to a particular path.

           This dumps the application file.
           Raises UnknownApplicationError if not found.
        """
        if spec.namespace and spec.namespace != self.namespace:
            raise UnknownApplicationError(
                "Repository %s does not contain package %s."
                % (self.namespace, spec.fullname))

        # Install the application.py file itself.
        fs.install(self.filename_for_application_name(spec.name), path)

    def purge(self):
        """Clear entire application instance cache."""
        self._instances.clear()

    @property
    def index(self):
        """Construct the index for this repo lazily."""
        if self._repo_index is None:
            self._repo_index = RepoIndex(self._app_checker, self.namespace)
            self._repo_index.add_indexer('tags', TagIndexer())
        return self._repo_index

    @property
    def tag_index(self):
        """Index of tags and which applications they're defined on."""
        return self.index['tags']

    def dirname_for_application_name(self, app_name):
        """Get the directory name for a particular application.  This is the
           directory that contains its application.py file."""
        return os.path.join(self.applications_path, app_name)

    def filename_for_application_name(self, app_name):
        """Get the filename for the module we should load for a particular
           application.  applications for a Repo live in
           ``$root/<application_name>/application.py``

           This will return a proper application.py path even if the
           application doesn't exist yet, so callers will need to ensure
           the application exists before importing.
        """
        app_dir = self.dirname_for_application_name(app_name)
        return os.path.join(app_dir, application_file_name)

    @property
    def _app_checker(self):
        if self._fast_application_checker is None:
            self._fast_application_checker = \
                FastApplicationChecker(self.applications_path)
        return self._fast_application_checker

    def all_application_names(self):
        """Returns a sorted list of all application names in the Repo."""
        names = sorted(self._app_checker.keys())
        return names

    def applications_with_tags(self, *tags):
        v = set(self.all_application_names())
        index = self.tag_index

        for t in tags:
            t = t.lower()
            v &= set(index[t])

        return sorted(v)

    def all_applications(self):
        """Iterator over all applications in the repository.

        Use this with care, because loading applications is slow.

        """
        for name in self.all_application_names():
            yield self.get(name)

    def all_application_classes(self):
        """Iterator over all application *classes* in the repository.

        Use this with care, because loading applications is slow.
        """
        for name in self.all_application_names():
            yield self.get_app_class(name)

    def exists(self, app_name):
        """Whether a application with the supplied name exists."""
        if app_name is None:
            return False

        # if the FastApplicationChecker is already constructed, use it
        if self._fast_application_checker:
            return app_name in self._app_checker

        # if not, check for the application.py file
        path = self.filename_for_application_name(app_name)
        return os.path.exists(path)

    def last_mtime(self):
        """Time a application file in this repo was last updated."""
        return self._app_checker.last_mtime()

    def _get_app_module(self, app_name):
        """Create a module for a particular application.

        This caches the module within this Repo *instance*.  It does
        *not* add it to ``sys.modules``.  So, you can construct
        multiple Repos for testing and ensure that the module will be
        loaded once per repo.

        """
        if app_name not in self._modules:
            file_path = self.filename_for_application_name(app_name)

            if not os.path.exists(file_path):
                raise UnknownApplicationError(app_name, self)

            if not os.path.isfile(file_path):
                tty.die("Something's wrong. '%s' is not a file!" % file_path)

            if not os.access(file_path, os.R_OK):
                tty.die("Cannot read '%s'!" % file_path)

            # e.g., ramble.app.builtin.mpich
            fullname = "%s.%s" % (self.full_namespace, app_name)

            try:
                module = ramble.util.imp.load_source(fullname, file_path,
                                                     prepend=_application_prepend)
            except SyntaxError as e:
                # SyntaxError strips the path from the filename so we need to
                # manually construct the error message in order to give the
                # user the correct application.py where the syntax error is
                # located
                raise SyntaxError('invalid syntax in {0:}, line {1:}'
                                  .format(file_path, e.lineno))

            module.__application__ = self.full_namespace
            module.__loader__ = self
            self._modules[app_name] = module

        return self._modules[app_name]

    def get_app_class(self, app_name):
        """Get the class for the application out of its module.

        First loads (or fetches from cache) a module for the
        application. Then extracts the application class from the module
        according to Ramble's naming convention.
        """
        namespace, _, app_name = app_name.rpartition('.')
        if namespace and (namespace != self.namespace):
            raise InvalidNamespaceError('Invalid namespace for %s repo: %s'
                                        % (self.namespace, namespace))

        class_name = nm.mod_to_class(app_name)
        tty.debug(' Class name = %s' % class_name)
        module = self._get_app_module(app_name)

        cls = getattr(module, class_name)
        if not inspect.isclass(cls):
            tty.die("%s.%s is not a class" % (app_name, class_name))

        return cls

    def __str__(self):
        return "[Repo '%s' at '%s']" % (self.namespace, self.root)

    def __repr__(self):
        return self.__str__()

    def __contains__(self, app_name):
        return self.exists(app_name)


def create_repo(root, namespace=None):
    """Create a new repository in root with the specified namespace.

       If the namespace is not provided, use basename of root.
       Return the canonicalized path and namespace of the created repository.
    """
    root = ramble.util.path.canonicalize_path(root)
    if not namespace:
        namespace = os.path.basename(root)

    if not re.match(r'\w[\.\w-]*', namespace):
        raise InvalidNamespaceError(
            "'%s' is not a valid namespace." % namespace)

    existed = False
    if os.path.exists(root):
        if os.path.isfile(root):
            raise BadRepoError('File %s already exists and is not a directory'
                               % root)
        elif os.path.isdir(root):
            if not os.access(root, os.R_OK | os.W_OK):
                raise BadRepoError(
                    'Cannot create new repo in %s: cannot access directory.'
                    % root)
            if os.listdir(root):
                raise BadRepoError(
                    'Cannot create new repo in %s: directory is not empty.'
                    % root)
        existed = True

    full_path = os.path.realpath(root)
    parent = os.path.dirname(full_path)
    if not os.access(parent, os.R_OK | os.W_OK):
        raise BadRepoError(
            "Cannot create repository in %s: can't access parent!" % root)

    try:
        config_path = os.path.join(root, repo_config_name)
        applications_path = os.path.join(root, applications_dir_name)

        fs.mkdirp(applications_path)
        with open(config_path, 'w') as config:
            config.write("repo:\n")
            config.write("  namespace: '%s'\n" % namespace)

    except (IOError, OSError) as e:
        # try to clean up.
        if existed:
            shutil.rmtree(config_path, ignore_errors=True)
            shutil.rmtree(applications_path, ignore_errors=True)
        else:
            shutil.rmtree(root, ignore_errors=True)

        raise BadRepoError('Failed to create new repository in %s.' % root,
                           "Caused by %s: %s" % (type(e), e))

    return full_path, namespace


def create_or_construct(path, namespace=None):
    """Create a repository, or just return a Repo if it already exists."""
    if not os.path.exists(path):
        fs.mkdirp(path)
        create_repo(path, namespace)
    return Repo(path)


def _path(repo_dirs=None):
    """Get the singleton RepoPath instance for Ramble.

    Create a RepoPath, add it to sys.meta_path, and return it.

    TODO: consider not making this a singleton.
    """
    repo_dirs = repo_dirs or ramble.config.get('repos')
    if not repo_dirs:
        raise NoRepoConfiguredError(
            "Ramble configuration contains no application repositories.")

    path = RepoPath(*repo_dirs)
    sys.meta_path.append(path)
    return path


#: Singleton repo path instance
path = llnl.util.lang.Singleton(_path)


def get(spec):
    """Convenience wrapper around ``ramble.repository.get()``."""
    return path.get(spec)


def all_application_names():
    """Convenience wrapper around ``ramble.repository.all_application_names()``."""  # noqa: E501
    return path.all_application_names()


def set_path(repo):
    """Set the path singleton to a specific value.

    Overwrite ``path`` and register it as an importer in
    ``sys.meta_path`` if it is a ``Repo`` or ``RepoPath``.
    """
    global path
    path = repo

    # make the new repo_path an importer if needed
    append = isinstance(repo, (Repo, RepoPath))
    if append:
        sys.meta_path.append(repo)
    return append


@contextlib.contextmanager
def additional_repository(repository):
    """Adds temporarily a repository to the default one.

    Args:
        repository: repository to be added
    """
    path.put_first(repository)
    yield
    path.remove(repository)


@contextlib.contextmanager
def use_repositories(*paths_and_repos):
    """Use the repositories passed as arguments within the context manager.

    Args:
        *paths_and_repos: paths to the repositories to be used, or
            already constructed Repo objects

    Returns:
        Corresponding RepoPath object
    """
    global path

    # Construct a temporary RepoPath object from
    temporary_repositories = RepoPath(*paths_and_repos)

    # Swap the current repository out
    saved = path
    remove_from_meta = set_path(temporary_repositories)

    yield temporary_repositories

    # Restore _path and sys.meta_path
    if remove_from_meta:
        sys.meta_path.remove(temporary_repositories)
    path = saved


class RepoError(ramble.error.RambleError):
    """Superclass for repository-related errors."""


class NoRepoConfiguredError(RepoError):
    """Raised when there are no repositories configured."""


class InvalidNamespaceError(RepoError):
    """Raised when an invalid namespace is encountered."""


class BadRepoError(RepoError):
    """Raised when repo layout is invalid."""


class UnknownEntityError(RepoError):
    """Raised when we encounter a application ramble doesn't have."""


class IndexError(RepoError):
    """Raised when there's an error with an index."""


class UnknownApplicationError(UnknownEntityError):
    """Raised when we encounter a application ramble doesn't have."""

    def __init__(self, name, repo=None):
        msg = None
        long_msg = None
        if name:
            if repo:
                msg = "Application '{0}' not found in repository '{1.root}'"
                msg = msg.format(name, repo)
            else:
                msg = "Application '{0}' not found.".format(name)

            # Special handling for specs that may have been intended as
            # filenames: prompt the user to ask whether they intended to write
            # './<name>'.
            if name.endswith(".yaml"):
                long_msg = "Did you mean to specify a filename with './{0}'?"
                long_msg = long_msg.format(name)
        else:
            msg = "Attempting to retrieve anonymous Application."

        super(UnknownApplicationError, self).__init__(msg, long_msg)
        self.name = name


class UnknownNamespaceError(UnknownEntityError):
    """Raised when we encounter an unknown namespace"""

    def __init__(self, namespace):
        super(UnknownNamespaceError, self).__init__(
            "Unknown namespace: %s" % namespace)


class FailedConstructorError(RepoError):
    """Raised when an application's class constructor fails."""

    def __init__(self, name, exc_type, exc_obj, exc_tb):
        super(FailedConstructorError, self).__init__(
            "Class constructor failed for application '%s'." % name,
            '\nCaused by:\n' +
            ('%s: %s\n' % (exc_type.__name__, exc_obj)) +
            ''.join(traceback.format_tb(exc_tb)))
        self.name = name
