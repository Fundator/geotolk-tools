"""
Functions for loading data from Geosuite archives (AUTOGRAF.DBF folders)
"""
import os
# from tqdm.auto import tqdm
import logging
import pandas as pd

#from src.config import NADAG_DIR, GEOARKIV_TXT, NORCONSULT_DIR_LOCAL, GEOVEST_DIR_LOCAL
from snd import process_snd
from prv import process_prv
from tlk import process_tlk
from helpers import merge_dfs

logger = logging.getLogger(__name__)


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
            logger.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    elif filetype == "prv":
        try:
            file_dict = process_prv(lines)
        except Exception as e:
            logger.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    elif filetype == "tlk":
        try:
            file_dict = process_tlk(lines)
        except Exception as e:
            logger.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    else:
        raise ValueError("Invalid file type: {}".format(filetype))

    if file_dict is not None:
        file_dict["filename"] = filename
    return file_dict

def process_single_file(lines: list, filename: str) -> dict:
    filetype = filename[-3:].lower()

    if filetype == "snd":
        try:
            file_dict = process_snd(lines)
        except Exception as e:
            logger.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    elif filetype == "prv":
        try:
            file_dict = process_prv(lines)
        except Exception as e:
            logger.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    elif filetype == "tlk":
        try:
            file_dict = process_tlk(lines)
        except Exception as e:
            logger.warning(f"Could not process file {filename}: {e}")
            file_dict = None
    else:
        raise ValueError("Invalid file type: {}".format(filetype))

    if file_dict is not None:
        file_dict["filename"] = filename
    return file_dict

def find_autograf_dbfs(nadag=True, norconsult="local", geovest=True):
    """
    Find all AUTOGRAF.DBF folders for the specified datasets
    :param nadag: Find folders in the NADAG dataset?
    :type nadag: bool
    :param norconsult: Find folders in the Norconsult dataset? Can be either "local" (Find folders in the local data-
                       directory), or "network" (loads data directly from the project folders on the X-drive, using
                       paths from 'config.SHAREPOINT_DATA_DIR/nc_geoarkiv.txt'). If norconsult=False, no Norconsult data
                       is loaded.
    :type norconsult: str or bool
    :param geovest: Find folders in the Geovest dataset?
    :type geovest: bool
    :return: List of paths to AUTOGRAF.DBF folders.
    :rtype: list of str
    """
    paths = []

    if nadag:
        for dirname in os.listdir(NADAG_DIR):
            path = os.path.join(NADAG_DIR, dirname, "AUTOGRAF.DBF")
            if os.path.isdir(path):
                paths.append((path, "nadag", dirname))

    if norconsult == "network":
        with open(GEOARKIV_TXT, "r") as index_file:
            for line in index_file:
                path = os.path.join(line.replace("\n", ""), "AUTOGRAF.DBF")
                if os.path.isdir(path):
                    split_path = path.split("\\")
                    location = split_path[3]
                    project = split_path[6]
                    paths.append((path, location, project))
    elif norconsult == "local":
        for dirname in os.listdir(NORCONSULT_DIR_LOCAL):
            path = os.path.join(NORCONSULT_DIR_LOCAL, dirname, "AUTOGRAF.DBF")
            if os.path.isdir(path):
                location, project = path.split("\\")[-2].split("_")
                paths.append((path, location, project))

    if geovest:
        for dirname in os.listdir(GEOVEST_DIR_LOCAL):
            path = os.path.join(GEOVEST_DIR_LOCAL, dirname, "AUTOGRAF.DBF")
            if os.path.isdir(path):
                project = path.split("\\")[-2]
                paths.append((path, "Geovest", project))

    return paths


def load(nadag=True, norconsult="local", geovest=True, max_autograf_dbf=None):
    """
    Load data from the specified datasets.

    :param nadag: Find folders in the NADAG dataset?
    :type nadag: bool
    :param norconsult: Find folders in the Norconsult dataset? Can be either "local" (Find folders in the local data-
                       directory), or "network" (loads data directly from the project folders on the X-drive, using
                       paths from 'config.SHAREPOINT_DATA_DIR/nc_geoarkiv.txt'). If norconsult=False, no Norconsult data
                       is loaded.
    :type norconsult: str or bool
    :param geovest: Find folders in the Geovest dataset?
    :type geovest: bool
    :param max_autograf_dbf: Modifier for the list of valid AUTOGRAF.DBF folders. If int, the first 'max_autograf_dbf'
                             will be loaded. If 'max_autograf_dbf' callable, it will be called with the list of valid
                             paths as its only argument. It is expected to return a list or tuple with the same format
                             as the input.
    :type max_autograf_dbf: int | callable
    :return: Dictionary with processed files. Keys are Bore-hole IDs and values are lists of dicts from processed files,
             e.g.:
             'nadag/130696-04 Vannforsyning Huseby utfo (62527)/02': [
                 {
                     'type': 'snd',
                     'xyz': (6649984.147438, 256829.340154, 16.612),
                     'guid': '4ddf32af-d5ab-4aef-a50e-aa6e80330f80',
                     'blocks': [{
                             'type': 'tot',
                             'date': datetime.datetime(2019, 3, 11, 0, 0),
                             'guid': '345a6d8f-b200-4152-8f70-0027966f6929',
                             'data': <pd.DataFrame>
                         }],
                     'filename': '02.SND'
                 },{
                     'type': 'tlk',
                     'xyz': [nan, nan, nan],
                     'guid': UUID('5f2f15ff-d70e-4583-8ebf-bc56bcf32bfb'),
                     'data': <pd.DataFrame>,
                     'filename': '02.TLK'
                 }
             ]
    :rtype: dict
    """
    autograf_paths = find_autograf_dbfs(nadag=nadag, norconsult=norconsult, geovest=geovest)

    if max_autograf_dbf is not None:
        if callable(max_autograf_dbf):
            autograf_paths = max_autograf_dbf(autograf_paths)
            assert isinstance(autograf_paths, (list, tuple)), "Expected list or tuple from callable 'max_autograf_dbf'."
        elif isinstance(max_autograf_dbf, int):
            autograf_paths = autograf_paths[:max_autograf_dbf]
        else:
            raise ValueError("Got invalid 'max_autograf_dbf'")

    out = {}
    # for path, location, project in tqdm(autograf_paths):
    for path, location, project in autograf_paths:

        files_dict = process_autograf_dbf(path, location, project)
        if files_dict is not None:
            out.update(files_dict)

    return out


def make_dataframes(files_dict):
    """
    Convert a dict with bore-holes (as returned by 'load') to dataframes.

    :param files_dict: Dict with data from bore-holes
    :type files_dict: dict
    :return: Dataframes containing data from total soundings, CPTs, ground samples, and interpretations, respectively.
    :rtype: tuple of pd.DataFrame
    """
    tot, cpt, prv, tlk = [], [], [], []

    # for file_id, file_list in tqdm(files_dict.items()):
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
