#! /usr/bin/env ruby

require 'json'

module SwiftDependency
	class FeatureExtractor
		private_class_method def structure(filename)
			parameters = ["sourcekitten", "structure", "--file", filename]
			structure_io = IO.popen(parameters)
			structure_json = JSON.load(structure_io)
			structure_io.close
			return structure_json
		end
	end
end