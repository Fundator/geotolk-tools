import sys
import os
from typing import List
from .parser import parse_snd_file, parse_tlk_file, parse_prv_file, path_to_lines

_VALID_FILETYPES = [".snd", ".tlk", ".prv"]

def _find_filenames_in_folder(path: str) -> List[str]:
    return os.listdir(path)

def _associate_filenames_in_folder(filenames: List[str]) -> dict:
    # Split filenames into prefix (filename) and suffix (.snd/.tlk/.prv etc)
    # Usually the last four characters is the suffix, and the previous is the prefix
    # Get all unique prefixes:
    prefixes = set([f[:-4] for f in filenames])

    #For each unique prefix, find all files with that prefix
    associated_files = {}

    for unique_filename in prefixes:
        grouped_filenames = []        
        for full_filename in filenames:
            full_filename_prefix = full_filename[:-4]
            if full_filename_prefix == unique_filename:
                grouped_filenames.append(full_filename)
        grouped_filenames = _prune_filetypes(grouped_filenames)
        grouped_filenames = _remove_filenames_without_snd_file(grouped_filenames)
        if grouped_filenames:            
            associated_files[unique_filename] = grouped_filenames

    return associated_files

def _remove_filenames_without_snd_file(files: List[str]) -> List[str]:
    # If none of the files ends with .snd, ignore the rest of the files
    for filename in files:
        if filename[-4:].lower() == ".snd":
            return files
    return []

def _prune_filetypes(files: List[str]) -> List[str]:
    # Remove files with invalid filetypes from the list
    return [f for f in files if f[-4:].lower() in _VALID_FILETYPES]

def load_folder(folder_path: str) -> dict:
    # Find all filenames in the folder
    filenames = _find_filenames_in_folder(folder_path)
    # Group the different files based on filename (before filetype)
    groups = _associate_filenames_in_folder(filenames)

    folder_data = {}
    # For each group
    for _, related_files in groups.items():
        # Each group needs to at least have one SND file
        snd = None
        prv = None
        tlk = None
        # For each file in group
        for file in related_files:
            # Get absolute path to file
            path = os.path.join(folder_path, file)

            # Read lines
            lines = path_to_lines(path)

            #Get suffix to get filetype
            file_type = file[-3:].lower()
            # Process file based on file type. We dont know the order of the files, so we merge them at the end
            if file_type == "snd":
                snd = parse_snd_file(lines)
            if file_type == "prv":
                prv = parse_prv_file(lines)
            if file_type == "tlk":
                tlk = parse_tlk_file(lines)

        if not snd:
            raise ValueError("No snd file found")
        
        if prv:
            snd["data_blocks"]["prv"] = prv
        if tlk:
            snd["data_blocks"]["tlk"] = tlk
        
        guid = snd["metadata"]["GUID_geosuite"]
        folder_data[guid] = snd
    return folder_data




