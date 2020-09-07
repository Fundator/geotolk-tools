from .load import process_file, get_id, find_files_in_autograf_dbf, make_dataframes
from .snd import process_snd
from .prv import process_prv
from .tlk import process_tlk
from .helpers import merge_dfs
import os

import pandas as pd

def process_multiple_by_path(path: str, location: str, project: str) -> dict:
    filenames = find_files_in_autograf_dbf(path)
    processed_files = {}
    
    for filename in filenames:
        proc = process_file(path, filename)
        if proc is not None:
            _id = get_id(location, project, filename)
            file_list = processed_files.get(_id, [])
            processed_files[_id] = file_list + [proc]

    return processed_files

def process_multiple_by_lines(list_of_lines: list, location: str, project: str) -> dict:
    processed_files = {}
    for file in list_of_lines:
        data = file["data"]
        filename = file["name"]
        proc = process_file_by_lines(data, filename)
        if proc is not None:
            _id = get_id(location, project, filename)
            file_list = processed_files.get(_id, [])
            processed_files[_id] = file_list + [proc]

    return processed_files

def process_file_by_path(path: str) -> dict:
    """
    Process 'filename' located at 'path' Must be either a .snd/SND, .PRV, or .TLK file.

    :param path: Path to file
    :type path: str
    :param filename: Name of file
    :type filename: str
    :return: Dict with data from the processed file.
    :rtype: dict
    """
    filetype = path[-3:].lower()

    with open(path, "r", errors="ignore") as in_file:
        lines = in_file.readlines()

    if filetype == "snd":
        try:
            file_dict = process_snd(lines)
        except Exception as e:
            file_dict = None
    elif filetype == "prv":
        try:
            file_dict = process_prv(lines)
        except Exception as e:
            file_dict = None
    elif filetype == "tlk":
        try:
            file_dict = process_tlk(lines)
        except Exception as e:
            file_dict = None
    else:
        raise ValueError("Invalid file type: {}".format(filetype))

    if file_dict is not None:
        file_dict["filename"] = path.split("\\")[-1]
    return file_dict

def process_file_by_lines(lines: list, filename: str) -> dict:
    filetype = filename[-3:].lower()

    if filetype == "snd":
        try:
            file_dict = process_snd(lines)
        except Exception as e:
            file_dict = None
    elif filetype == "prv":
        try:
            file_dict = process_prv(lines)
        except Exception as e:
            file_dict = None
    elif filetype == "tlk":
        try:
            file_dict = process_tlk(lines)
        except Exception as e:
            file_dict = None
    else:
        raise ValueError("Invalid file type: {}".format(filetype))

    if file_dict is not None:
        file_dict["filename"] = filename
    return file_dict



# Convenience functions to convert paths to lines (lines in a txt file)

def convert_multiple_to_lines(path: str) -> list:
    files = find_files_in_autograf_dbf(path)
    return [{"data": convert_file_to_lines(os.path.join(path, f)), "name": f} for f in files]
 
def convert_file_to_lines(path: str) -> list:
    with open(path, "r") as f:
        return f.readlines()


# Function to convert dictionary to dataframes

def dict_to_dataframes(file_dict: dict) -> pd.DataFrame:
    if "type" in file_dict.keys():
        if file_dict["type"] == "snd":
            return file_dict["blocks"][0]["data"]
        elif file_dict["type"] == "tlk":
            return file_dict["data"]
    else:
        return make_dataframes(file_dict)