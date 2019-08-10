#!/usr/bin/env wolframscript
(* ::Package:: *)

indexFile = $ScriptCommandLine[[1]];
dependenciesFile = $ScriptCommandLine[[2]];


index = Import[indexFile, "Dataset", "HeaderLines" -> 1];
dependencies = Import[dependenciesFile, "Dataset", "HeaderLines" -> 1];


uniqueIndex = index[DeleteDuplicatesBy["name"]];
allObjects = uniqueIndex[All, "name"] // Normal;


TypenameCharacter = (WordCharacter|"_");
ExtractTypes[name_] := Select[allObjects, MemberQ[StringSplit, Except[TypenameCharacter]], #]&];
SplitToSubDependencies[dependency_, newDependencies_] := Append[dependency, "dependency" -> #]& /@ newDependencies;
RemoveSelfDependencies[dependencies_] := cleanedDependencies[Select[#object != #dependency&]];
CleanupDependencies[dependencies_] := RemoveSelfDependencies[Flatten[SplitToSubDependencies[#, ExtractTypes[#dependency]]& /@ dependencies]];


cleanedDependencies = CleanupDependencies[dependencies];


FileWithSuffix[name_, suffix_] := FileBaseName[name]<>"."<>suffix<>"."<>FileExtension[name];


Export[FileWithSuffix[indexFile, "clean"], uniqueIndex];
Export[FileWithSuffix[dependenciesFile, "clean"], cleanedDependencies];
