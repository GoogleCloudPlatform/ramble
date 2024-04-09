# Copyright 2022-2024 Google LLC and other Ramble developers
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function

import argparse
from collections import defaultdict

import llnl.util.tty.color as color
from llnl.util.tty.colify import colify

import ramble.repository
from ramble.util.logger import logger

description = "get information about object attributes"
section = "developer"
level = "long"

all_attrs = ['maintainers', 'tags']
default_attr = 'maintainers'


def setup_parser(subparser):
    defined_group = subparser.add_mutually_exclusive_group()
    defined_group.add_argument(
        "--defined",
        action="store_true",
        default=False,
        help="show names of objects with attributes",
    )

    defined_group.add_argument(
        "--undefined",
        action="store_true",
        default=False,
        help="show names of objects without attributes",
    )

    subparser.add_argument(
        "-a", "--all", action="store_true", default=False,
        help="show attributes for all objects"
    )

    subparser.add_argument(
        "--by-attribute",
        action="store_true",
        default=False,
        help="show objects for attributes instead of attributes for objects",
    )

    object_group = subparser.add_mutually_exclusive_group()
    for obj in ramble.repository.ObjectTypes:
        help_msg = f"show attributes for {obj.name}"
        if obj == ramble.repository.default_type:
            help_msg += " (default)"

        object_group.add_argument(
            f"--{obj.name}",
            action="store_true",
            default=False,
            help=help_msg,
        )

    attribute_group = subparser.add_mutually_exclusive_group()
    for attr in all_attrs:
        help_msg = f"use {attr} as the attribute."
        if attr == default_attr:
            help_msg += " (default)"
        attribute_group.add_argument(
            f"--{attr}",
            action="store_true",
            default=False,
            help=help_msg,
        )

    # options for commands that take object arguments
    subparser.add_argument(
        "object_or_attr",
        nargs=argparse.REMAINDER,
        help="names of objects or attributes to get info for",
    )


def objects_to_attributes(object_names=None, attr_name=default_attr,
                          object_type=ramble.repository.default_type):
    if not object_names:
        object_names = ramble.repository.paths[object_type].all_object_names()

    app_to_users = defaultdict(lambda: set())
    for name in object_names:
        cls = ramble.repository.paths[object_type].get_obj_class(name)
        for user in getattr(cls, attr_name):
            app_to_users[name].add(user)

    return app_to_users


def attributes_to_objects(users=None, attr_name=default_attr,
                          object_type=ramble.repository.default_type):
    user_to_apps = defaultdict(lambda: [])
    object_names = ramble.repository.paths[object_type].all_object_names()
    for name in object_names:
        cls = ramble.repository.paths[object_type].get_obj_class(name)
        for user in getattr(cls, attr_name):
            lower_users = [u.lower() for u in users]
            if not users or user.lower() in lower_users:
                user_to_apps[user].append(cls.name)

    return user_to_apps


def defined_objects(attr_name=default_attr, object_type=ramble.repository.default_type):
    defined = []
    undefined = []
    object_names = ramble.repository.paths[object_type].all_object_names()
    for name in object_names:
        cls = ramble.repository.paths[object_type].get_obj_class(name)
        if hasattr(cls, attr_name) and getattr(cls, attr_name):
            defined.append(name)
        else:
            undefined.append(name)

    return defined, undefined


def union_values(dictionary):
    """Given a dictionary with values that are Collections, return their union.

    Arguments:
        dictionary (dict): dictionary whose values are all collections.

    Return:
        (set): the union of all collections in the dictionary's values.
    """
    sets = [set(p) for p in dictionary.values()]
    return sorted(set.union(*sets)) if sets else set()


def attributes(parser, args):
    object_type = ramble.repository.default_type
    if args.modifiers:
        object_type = ramble.repository.ObjectTypes.modifiers

    attr_name = default_attr
    if args.tags:
        attr_name = 'tags'

    if args.defined or args.undefined:
        defined, undefined = defined_objects(attr_name=attr_name,
                                             object_type=object_type)
        apps = defined if args.defined else undefined
        colify(apps)
        return 0 if apps else 1

    if args.all:
        if args.by_attribute:
            attributes = attributes_to_objects(args.object_or_attr,
                                               attr_name=attr_name,
                                               object_type=object_type)
            for user, objects in sorted(attributes.items()):
                color.cprint("@c{%s}: %s" % (user, ", ".join(sorted(objects))))
            return 0 if attributes else 1

        else:
            objects = objects_to_attributes(args.object_or_attr,
                                            attr_name=attr_name,
                                            object_type=object_type)
            for app, attributes in sorted(objects.items()):
                color.cprint("@c{%s}: %s" % (app, ", ".join(sorted(attributes))))
            return 0 if objects else 1

    if args.by_attribute:
        if not args.object_or_attr:
            logger.die("ramble attributes --by-attribute requires an attribute or --all")

        objects = union_values(attributes_to_objects(args.object_or_attr,
                                                     attr_name=attr_name,
                                                     object_type=object_type))
        colify(objects)
        return 0 if objects else 1

    else:
        if not args.object_or_attr:
            logger.die("ramble attributes requires an object or --all")

        users = union_values(objects_to_attributes(args.object_or_attr,
                                                   attr_name=attr_name,
                                                   object_type=object_type))
        colify(users)
        return 0 if users else 1
