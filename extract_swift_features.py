#!/usr/bin/env python3

import subprocess
import argparse
import shutil
import json
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
		self.object = None 
		self.dependency = None
		self.type = None
		self.path = None

class ProcessingContext:
	def __init__(self, file, level, declaration):
		self.file = file
		self.level = level
		self.declaration = declaration

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

		self._procees_structure( 
			ProcessingContext(
				context.file,
				context.level + 1,
				new_declaration
			),
			node["key.substructure"]
		)

	def _process_node(self, context, node):
		kind = node.get("key.kind")
		name = node.get("key.name")

		LOGGER.debug("Process node {} {}", name, kind)

		def track_type(type):
			self._index.append(SwiftObject(name, type, context.file))
			LOGGER.verbose("Found {} {}", type, name)

		def track_dependency(dependency, type):
			dependency = SwiftDependency(context.declaration, dependency, type, context.file)
			self._dependencies.append(dependency)
			LOGGER.verbose("Found {} {} -> {}", dependency.type, dependency.object, dependency.dependency)

		declared_type_name = None
		if (kind == "source.lang.swift.decl.struct"):
			track_type("struct")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.class"):
			track_type("class")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.enum"):
			track_type("enum")
			declared_type_name = name
		elif (kind == "source.lang.swift.decl.protocol"):
			track_type("protocol")
			declared_type_name = name

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
	extract_features(log_level=Logger.LogLevel.DEBUG, path="test_data/test.swift")