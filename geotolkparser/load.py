"""
Functions for loading data from Geosuite archives (AUTOGRAF.DBF folders)
"""
import os
import logging
import pandas as pd

from .snd import process_snd
from .prv import process_prv
from .tlk import process_tlk
from .helpers import merge_dfs


def filename_is_valid(path, f):
    """
    Check if the filename 'f' at 'path' should be loaded

    :param path: Path to file
    :type path: str
    :param f: Filename including extension
    :type f: str
    :return: Boolean indicating the validity of 'f'
    :rtype: bool
    """
    if len(f) < 4:
        return False
    if os.path.isdir(os.path.join(path, f)):
        return False
    return f[-4:].lower() in (".snd", ".prv", ".tlk")


def find_files_in_autograf_dbf(path):
    """
    Find all valid files in an AUTOGRAF.DBF folder

    :param path: Path to AUTOGRAF.DBF. Must include 'AUTOGRAF.DBF'
    :type path: str
    :return: List of valid filenames in 'path'
    :rtype: list of str
    """
    if not os.path.exists(path) or not os.path.isdir(path):
        return []
    files = os.listdir(path)
    files = [f for f in files if filename_is_valid(path, f)]
    return files


def sanitize_filename(filename):
    """
    Prepare the filename for ID-creation

    :param filename: Filename
    :type filename: str
    :return: Cleaned filename
    :rtype: str
    """
    f = filename.lower()[:-4]
    return f


def get_id(location, project, filename):
    """
    Get the id for 'filename' in 'project' at 'location'. ID's are constructed such that all files connected to a bore-
    hole get the same ID.

    :param location: Location identifier
    :type location: str
    :param project: Project identifier
    :type project: str
    :param filename: Name of file
    :type filename: str
    :return: Bore-hole ID
    :rtype: str
    """
    return "/".join([location, project, sanitize_filename(filename)])


def process_autograf_dbf(path, location, project):
    """
    Load all files in an AUTOGRAF.DBF folder.

    :param path: Path to AUTOGRAF.DBF
    :type path: str
    :param location: Location identifier
    :type location: str
    :param project: Project identifier
    :type project: str
    :return: Dictionary with processed files. Keys are Bore-hole IDs and values are lists of dicts from processed files.
    :rtype: dict
    """
    filenames = find_files_in_autograf_dbf(path)
    processed_files = {}
    
    for filename in filenames:
        proc = process_file(path, filename)
        if proc is not None:
            _id = get_id(location, project, filename)
            file_list = processed_files.get(_id, [])
            processed_files[_id] = file_list + [proc]

    return processed_files


def process_file(path, filename):
    """
    Process 'filename' located at 'path' Must be either a .snd/SND, .PRV, or .TLK file.

    :param path: Path to file
    :type path: str
    :param filename: Name of file
    :type filename: str
    :return: Dict with data from the processed file.
    :rtype: dict
    """
    filetype = filename[-3:].lower()
    filepath = os.path.join(path, filename)

    with open(filepath, "r", errors="ignore") as in_file:
        lines = in_file.readlines()

    if filetype == "snd":
        try:
            file_dict = process_snd(lines)
        except Exception as e:
            logging.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    elif filetype == "prv":
        try:
            file_dict = process_prv(lines)
        except Exception as e:
            logging.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    elif filetype == "tlk":
        try:
            file_dict = process_tlk(lines)
        except Exception as e:
            logging.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    else:
        raise ValueError("Invalid file type: {}".format(filetype))

    if file_dict is not None:
        file_dict["filename"] = filename
    return file_dict


def make_dataframes(files_dict):
    """
    Convert a dict with bore-holes (as returned by 'load') to dataframes.

    :param files_dict: Dict with data from bore-holes
    :type files_dict: dict
    :return: Dataframes containing data from total soundings, CPTs, ground samples, and interpretations, respectively.
    :rtype: tuple of pd.DataFrame
    """
    tot, cpt, prv, tlk = [], [], [], []

    for file_id, file_list in files_dict.items():

        for file_dict in file_list:
            if file_dict["type"] == "prv":
                df = file_dict["data"]
                df["id"] = file_id
                df["filename"] = file_dict["filename"]
                prv.append(df)
            elif file_dict["type"] == "tlk":
                df = file_dict["data"]
                df["id"] = file_id
                df["filename"] = file_dict["filename"]
                tlk.append(df)
            elif file_dict["type"] == "snd":
                for block in file_dict["blocks"]:
                    df = block["data"]
                    df["id"] = file_id
                    df["filename"] = file_dict["filename"]
                    df["x"], df["y"], df["z"] = file_dict["xyz"]
                    df["date"] = block["date"]
                    if block["type"] == "tot":
                        tot.append(df)
                    elif block["type"] == "cpt":
                        cpt.append(df)
                    else:
                        raise ValueError("Invalid block type: '{}' for ID '{}'".format(block["type"], file_id))
            else:
                raise ValueError("Invalid file type: '{}' for ID '{}'".format(file_dict["type"], file_id))

    tot = merge_dfs(tot) if tot else None
    cpt = merge_dfs(cpt) if cpt else None
    prv = merge_dfs(prv) if prv else None
    tlk = merge_dfs(tlk, sort_by=["id", "kote"]) if tlk else None
    return tot, cpt, prv, tlk
