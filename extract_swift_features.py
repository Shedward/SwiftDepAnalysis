#!/usr/bin/env python3

import subprocess
import argparse
import shutil
import json
import csv
import re
from itertools import takewhile
from enum import Enum
from pathlib import Path

# -- Utilities --

class Logger:
    class LogLevel(Enum):
        NONE = 0
        ERROR = 1
        MESSAGE = 2
        VERBOSE = 3
        DEBUG = 4

    def __init__(self, log_level):
        self.log_level = log_level

    def error(self, msg, *args, **kwargs):
        if (self.log_level.value >= Logger.LogLevel.ERROR.value):
            print(msg.format(*args, **kwargs))

    def message(self, msg, *args, **kwargs):
        if (self.log_level.value >= Logger.LogLevel.MESSAGE.value):
            print(msg.format(*args, **kwargs))

    def verbose(self, msg, *args, **kwargs):
        if (self.log_level.value >= Logger.LogLevel.VERBOSE.value):
            print(msg.format(*args, **kwargs))

    def debug(self, msg, *args, **kwargs):
        if (self.log_level.value >= Logger.LogLevel.DEBUG.value):
            print(msg.format(*args, **kwargs))

# -- Dependency extracting

class SwiftObject:
    def __init__(self, name, kind, path, size):
        self.name = name
        self.kind = kind
        self.path = path
        self.size = size

    def to_dict(self):
        return {
            "name": self.name,
            "kind": self.kind,
            "path": self.path,
            "size": self.size
        }

    @staticmethod
    def from_dict(dict):
        return SwiftObject(dict["name"], dict["kind"], dict["path"], dict["size"])

    def __eq__(self, other):
        return (self.name == other.name 
            and self.kind == other.kind 
            and self.path == other.path
            and self.size == other.size)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.kind, self.path, self.size, type(self)))

class SwiftDependency:
    def __init__(self, object, dependency, type, path):
        self.object = object 
        self.dependency = dependency
        self.type = type
        self.path = path

    def to_dict(self):
        return {
            "object": self.object,
            "dependency": self.dependency,
            "type": self.type,
            "path": self.path
        }

    @staticmethod
    def from_dict(dict):
        return SwiftDependency(dict["object"], dict["dependency"], dict["type"], dict["path"])

    def __eq__(self, other):
        return (self.object == other.object 
            and self.dependency == other.dependency 
            and self.type == other.type 
            and self.path == other.path)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.object, self.dependency, self.type, self.path, type(self)))

class ProcessingContext:
    def __init__(self, file, level, declaration):
        self.file = file
        self.level = level
        self.declaration = declaration

    def resolve_fullname(self, name):
        if self.declaration is None:
            return name
        else:
            return self.declaration + '.' + name

class SwiftDependenciesExtractor:
    def __init__(self):
        self._index = set()
        self._dependencies = set()
        self.logger = Logger(Logger.LogLevel.NONE)

    def extract(self, filename):
        self.declarations_count = 0
        self.dependencies_count = 0
        self.logger.verbose("Started {}", filename)
        structure_bytes = self._structure(filename)
        structure_string = structure_bytes.decode("utf8")
        structure_json = json.loads(structure_string)
        self._procees_structure(
            ProcessingContext(filename, 0, None), 
            structure_json
        )
        self.logger.message("{}: {} defs/{} deps", filename, self.declarations_count, self.dependencies_count)


    def index(self):
        return self._index

    def dependencies(self):
        return self._dependencies

    def _structure(self, filename):
        return subprocess.Popen(
            ["sourcekitten", "structure", "--file", filename],
            stdout=subprocess.PIPE
        ).stdout.read()

    def _procees_structure(self, context, structure):
        if (isinstance(structure, list)):
            for item in structure:
                self._procees_structure(context, item)
        elif (isinstance(structure, object)):
            self._process_node(context, structure)

    def _process_substructure(self, context, node, new_declaration=None):
        if "key.substructure" not in node:
            return 

        if new_declaration is None:
            new_declaration = context.declaration
        else:
            new_declaration = context.resolve_fullname(new_declaration)

        self._procees_structure( 
            ProcessingContext(
                context.file,
                context.level + 1,
                new_declaration
            ),
            node["key.substructure"]
        )

    def _extract_longest_type_name(self, name):
        name_parts = name.split(".")
        type_parts = takewhile(lambda w: len(w) > 0 and w[0].isupper(), name_parts)
        return ".".join(type_parts)

    def _process_node(self, context, node):
        kind = node.get("key.kind")
        name = node.get("key.name")
        typename = node.get("key.typename")

        self.logger.debug("Process node {} {}", name, kind)

        def track_type(type):
            bodylength = node.get("key.bodylength")
            if bodylength is None:
                bodylength = 0
            swift_object = SwiftObject(context.resolve_fullname(name), type, context.file, bodylength)
            self._index.add(swift_object)
            self.logger.verbose("Declared {} {}", swift_object.kind, swift_object.name)
            self.declarations_count += 1

        def track_dependency(dependency, type, object=None):
            if object is None:
                object = context.declaration
            if dependency == object or object is None or dependency is None:
                return
            dependency = SwiftDependency(object, dependency, type, context.file)
            self._dependencies.add(dependency)
            self.logger.verbose("Dependency {} {} -> {}", dependency.type, dependency.object, dependency.dependency)
            self.dependencies_count += 1

        declared_type_name = None
        if kind == "source.lang.swift.decl.struct":
            track_type("struct")
            track_dependency(context.resolve_fullname(name), "nested")
            declared_type_name = name
        elif kind == "source.lang.swift.decl.class":
            track_type("class")
            track_dependency(context.resolve_fullname(name), "nested")
            declared_type_name = name
        elif kind == "source.lang.swift.decl.enum":
            track_dependency(context.resolve_fullname(name), "nested")
            track_type("enum")
            declared_type_name = name
        elif kind == "source.lang.swift.decl.protocol":
            track_type("protocol")
            declared_type_name = name
        elif kind == "source.lang.swift.decl.var.parameter":
            track_dependency(typename, "func_parameter")
        elif kind == "source.lang.swift.decl.var.instance":
            track_dependency(typename, "property")
        elif kind == "source.lang.swift.decl.var.static":
            track_dependency(typename, "static_property")
        elif kind == "source.lang.swift.expr.call":
            if name is not None:
                called_type = self._extract_longest_type_name(name)
                if len(called_type) > 0:
                    if called_type == name:
                        track_dependency(called_type, "called")
                    else:
                        track_dependency(called_type, "called_static")

        if "key.inheritedtypes" in node:
            inheritedtypes = node["key.inheritedtypes"]
            if isinstance(inheritedtypes, list):
                for inheritedtype in inheritedtypes:
                    if isinstance(inheritedtype, dict) and "key.name" in inheritedtype:
                        track_dependency(inheritedtype["key.name"], "inheritance", name)

        self._process_substructure(context, node, declared_type_name)

    def split_complex_dependencies_into_simple_types(self):
        clean_up_dependencies = set()
        for dependency in self._dependencies:
            subdependencies = list(self._split_types(dependency.dependency))
            for subdependency in subdependencies:
                new_dependency = SwiftDependency(dependency.object, subdependency, dependency.type, dependency.path)
                clean_up_dependencies.add(new_dependency)
        self._dependencies = clean_up_dependencies

    def remove_dependencies_outside_index(self):
        clean_up_dependencies = self._dependencies
        indexed_objects = list(map(lambda d: d.name, self._index))
        def dependency_is_in_index(dependency):
            return (dependency.object in indexed_objects 
                and dependency.dependency in indexed_objects)

        clean_up_dependencies = list(filter(dependency_is_in_index, clean_up_dependencies))
        self._dependencies = clean_up_dependencies

    def remove_self_dependencies(self):
        clean_up_dependencies = self._dependencies
        clean_up_dependencies = list(filter(lambda d: d.object != d.dependency, clean_up_dependencies))
        self._dependencies = clean_up_dependencies


    def _split_types(self, text):
        def is_class_name(string):
            if len(string) == 0:
                return False
            else:
                return string[0].isupper()

        return filter(is_class_name, re.compile("[^\w_\.]").split(text)) 

    def export_csv_to(self, prefix):
        with open(prefix + ".index.csv", mode="w") as csv_file:
            fieldnames = ["name", "kind", "path", "size"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for definition in self.index():
                writer.writerow(definition.to_dict())

        with open(prefix + ".deps.csv", mode="w") as csv_file:
            fieldnames = ["object", "dependency", "type", "path"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for dep in self.dependencies():
                writer.writerow(dep.to_dict())

    def import_csv_from(self, prefix):
        new_index = set()
        with open(prefix + ".index.csv", mode="r") as csv_file:
            fieldnames = ["name", "kind", "path", "size"]
            reader = csv.DictReader(csv_file, fieldnames=fieldnames)
            for definition in reader:
                new_index.add(SwiftObject.from_dict(definition))
        self._index = new_index

        new_dependencies = set()
        with open(prefix + ".deps.csv", mode="r") as csv_file:
            fieldnames = ["object", "dependency", "type", "path"]
            reader = csv.DictReader(csv_file, fieldnames=fieldnames)
            for dependency in reader:
                new_dependencies.add(SwiftDependency.from_dict(dependency))
        self._dependencies = new_dependencies


# -- Main --

def extract_features(log_level, path, destination):
    logger = Logger(log_level)
    if shutil.which("sourcekitten") is None:
        logger.error("SourceKitten not found. Please install from https://github.com/jpsim/SourceKitten.")
        exit(1)
    dependencies_extractor = SwiftDependenciesExtractor()
    dependencies_extractor.logger = logger

    path_obj = Path(path)
    if path_obj.is_file():
        dependencies_extractor.extract(path)
    elif path_obj.is_dir():
        for file_obj in path_obj.glob("**/*.swift"):
            file = file_obj.as_posix()
            dependencies_extractor.extract(file)
    else:
        logger.error("Wrong path {}", path)

    def dependency_statistic():
        return (len(dependencies_extractor.index()), len(dependencies_extractor.dependencies()))

    def stat_diff(old_statistic, new_statistic):
        def difference(statistic_values):
            return statistic_values[0] - statistic_values[1]

        return list(map(difference, zip(old_statistic, new_statistic)))

    def stat_description(dependency_statistic):
        return "{} defs/{} deps".format(*dependency_statistic)

    current_stat = dependency_statistic()
    logger.message("Extracted: {}", stat_description(current_stat))

    dependencies_extractor.split_complex_dependencies_into_simple_types()
    diff = stat_diff(current_stat, dependency_statistic())
    logger.message("Removed after splitting complex dependencies: {}", stat_description(diff))
    current_stat = dependency_statistic()

    dependencies_extractor.remove_dependencies_outside_index()
    diff = stat_diff(current_stat, dependency_statistic())
    logger.message("Removed dependencies outside index: {}", stat_description(diff))
    current_stat = dependency_statistic()

    dependencies_extractor.remove_self_dependencies()
    diff = stat_diff(current_stat, dependency_statistic())
    logger.message("Removed self dependencies: {}", stat_description(diff))
    current_stat = dependency_statistic()

    logger.message("Cleaned up: {}", stat_description(dependency_statistic()))
    dependencies_extractor.export_csv_to(destination)

if __name__ == "__main__":
    extract_features(
        log_level=Logger.LogLevel.MESSAGE, 
        path="/Users/shed/Projects/arameem/ToYou", 
        destination="/Users/shed/Desktop/ToYou"
    )
