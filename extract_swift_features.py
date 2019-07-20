#!/usr/bin/env python3

import shutil
from enum import Enum

# -- Utilities --

LOGGER = None

class Logger:
	class LogLevel(Enum):
		NONE = 0
		ERROR = 1
		MESSAGE = 1
		VERBOSE = 3

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

def fatal_error(msg=None):
	LOGGER.error("Fatal error {}", msg)
	exit(1)

# -- Feature extracting

def SwiftObject:
	def __init__():
		self.name = None
		self.kind = None
		self.path = None

def SwiftDependency:
	def __init__():
		self.object = None 
		self.dependency = None
		self.type = None
		self.path = None

class FeatureExtractor:
	def __init__():
		self._index = []
		self._dependencies = []

	def extract(filename):
		structure = self._structure(filename)
		self._process(
			ProcessingContext(declaration=None), 
			structure["key.substructure"]
		)


	def index(self):
		return self._index

	def dependencies(self):
		return self._dependencies

	def _structure(self, filename):
		pass

	class ProcessingContext:
		def __init__(declaration):
			self.declaration = declaration

	def _process(self, context, structure):
		pass



# -- Main --

def main():
	if shutil.which("sourcekiten") is None:
		fatal_error("SourceKitten not found. Please install from https://github.com/jpsim/SourceKitten.")

if __name__ == "__main__":
	LOGGER = Logger(Logger.LogLevel.MESSAGE)
	main()