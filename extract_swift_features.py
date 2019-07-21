#!/usr/bin/env python3

import subprocess
import argparse
import shutil
import json
from itertools import takewhile
from enum import Enum

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

LOGGER = Logger(Logger.LogLevel.NONE)

def fatal_error(msg=None):
	LOGGER.error("Fatal error {}", msg)
	exit(1)

# -- Feature extracting

class SwiftObject:
	def __init__(self, name, kind, path):
		self.name = name
		self.kind = kind
		self.path = path

class SwiftDependency:
	def __init__(self, object, dependency, type, path):
		self.object = object 
		self.dependency = dependency
		self.type = type
		self.path = path

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

class FeatureExtractor:
	def __init__(self):
		self._index = []
		self._dependencies = []

	def extract(self, filename):
		structure_bytes = self._structure(filename)
		structure_string = structure_bytes.decode("utf8")
		structure_json = json.loads(structure_string)
		self._procees_structure(
			ProcessingContext(filename, 0, None), 
			structure_json
		)


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

		LOGGER.debug("Process node {} {}", name, kind)

		def track_type(type):
			swift_object = SwiftObject(context.resolve_fullname(name), type, context.file)
			self._index.append(swift_object)
			LOGGER.verbose("Declared {} {}", swift_object.kind, swift_object.name)

		def track_dependency(dependency, type, object=None):
			if object is None:
				object = context.declaration
			if dependency == object or object is None or dependency is None:
				return
			dependency = SwiftDependency(object, dependency, type, context.file)
			self._dependencies.append(dependency)
			LOGGER.verbose("Dependency {} {} -> {}", dependency.type, dependency.object, dependency.dependency)

		declared_type_name = None
		if (kind == "source.lang.swift.decl.struct"):
			track_type("struct")
			track_dependency(context.resolve_fullname(name), "nested")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.class"):
			track_type("class")
			track_dependency(context.resolve_fullname(name), "nested")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.enum"):
			track_dependency(context.resolve_fullname(name), "nested")
			track_type("enum")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.protocol"):
			track_type("protocol")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.var.parameter"):
			track_dependency(typename, "func_parameter")
		elif (kind == "source.lang.swift.decl.var.instance"):
			track_dependency(typename, "property")
		elif (kind == "source.lang.swift.decl.var.static"):
			track_dependency(typename, "static_property")
		elif (kind == "source.lang.swift.expr.call"):
			called_type = self._extract_longest_type_name(name)
			if len(called_type) > 0:
				if called_type == name:
					track_dependency(called_type, "called")
				else:
					track_dependency(called_type, "called_static")

		if "key.inheritedtypes" in node:
			inheritedtypes = node["key.inheritedtypes"]
			if not isinstance(inheritedtypes, list):
				return

			for inheritedtype in inheritedtypes:
				if isinstance(inheritedtype, dict) and "key.name" in inheritedtype:
					track_dependency(inheritedtype["key.name"], "inheritance", name)

		self._process_substructure(context, node, declared_type_name)

# -- Main --

def extract_features(log_level, path):
	global LOGGER
	LOGGER = Logger(log_level)
	if shutil.which("sourcekitten") is None:
		fatal_error("SourceKitten not found. Please install from https://github.com/jpsim/SourceKitten.")
	feature_extractor = FeatureExtractor()
	feature_extractor.extract(path)

if __name__ == "__main__":
	extract_features(log_level=Logger.LogLevel.VERBOSE, path="test_data/test.swift")