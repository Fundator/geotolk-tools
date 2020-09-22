from collections import defaultdict
import sys
import os
import re
from typing import List, Tuple
from .parser import parse_snd_file, parse_tlk_file, parse_prv_file, path_to_lines
import pandas as pd

_VALID_FILETYPES = [".snd", ".tlk", ".prv"]
_PR_PATTERN = re.compile(".*PR([^\-]).*(SND|snd)")


if sys.platform == "linux" or sys.platform == "linux2":
    _os = "linux"
    _SEPARATOR = "/"
elif sys.platform == "win32":
    _os = "win"
    _SEPARATOR = "\\"


def _find_filenames_in_folder(path: str) -> List[str]:
    return os.listdir(path)


def _remove_filenames_without_snd_file(files: List[str]) -> List[str]:
    # If none of the files ends with .snd, ignore the rest of the files
    for filename in files:
        if filename[-4:].lower() == ".snd":
            return files
    return []

def _prune_filetypes(files: List[str]) -> List[str]:
    # Remove files with invalid filetypes from the list
    return [f for f in files if f[-4:].lower() in _VALID_FILETYPES]

def _remove_incomplete_files(files: List[str]) -> List[str]:
    # Remove files containing PR.SND (except PR-*.SND for some reason...)
    return [f for f in files if not _PR_PATTERN.match(f)]

def _remove_CPTU_files(files: List[str]) -> List[str]:
    # Remove CPTU files. They can be found by having CPTU in their name
    return [f for f in files if "cptu" not in f.lower()]


def _get_oppdragsnr(oppdragsnr: str) -> int:
    return int(oppdragsnr.split("_")[-1])

def _sanitize_filename(filename: str) -> str:
    # First remove file ending
    prefix = filename[:-4]
    # Then remove special filename conventions from old versions
    for code in ["cpt", "prv", "pr", "tot"]:
        if code in prefix.lower():
            # remove special characters 
            prefix = "".join(e for e in prefix if e.isalnum())
            # remove upper and lower case versions of the code
            prefix = prefix.replace(code.lower(), "")
            prefix = prefix.replace(code.upper(), "")
    return prefix

def _create_id(path: str) -> dict:
    split_str = path.split(_SEPARATOR)
    filename = split_str[-1]
    oppdragsnr_raw = split_str[-3]
    oppdragsnr = _get_oppdragsnr(oppdragsnr_raw)
    borehole_id = _sanitize_filename(filename)
    return {"oppdragsnr": oppdragsnr, "borehole_id": borehole_id, "filename": filename}

_FILEPARSER = {
    "snd": parse_snd_file,
    "prv": parse_prv_file,
    "tlk": parse_tlk_file
}

def load_folder(folder_path: str) -> dict:
    """Loads all valid files from the given folder path

    Args:
        folder_path (str): Path to the folder with the files. Usually this is the AUTOGRAF.DBF-folder

    Returns:
        dict: File dict containing all the metadata and data of the valid files in the folder
    """
    # Find all filenams in the folder
    filenames = _find_filenames_in_folder(folder_path)

    # Remove unwanted files
    filenames = _remove_CPTU_files(filenames)
    filenames = _prune_filetypes(filenames)
    filenames = _remove_incomplete_files(filenames)
    # Initialize dict to hold all files with a defaultdict with lists
    folder_data = defaultdict(list)

    # Loop through each file
    for file in filenames:
        # Get absolute path
        abspath = os.path.join(folder_path, file)
        # Create ID
        _id = _create_id(abspath)
        # Create unique identifier by joining oppdragsnr and borehole id
        uid = f"{_id['oppdragsnr']}_{_id['borehole_id']}"
        # Read the lines
        lines = path_to_lines(abspath)
        # Get filetype
        file_type = file[-3:].lower()
        # Use the defined file parser for the specific file type
        parsed = _FILEPARSER[file_type](lines)
        parsed = {**_id, **parsed}
        folder_data[uid].append(parsed)
    return folder_data


def _convert_to_df_and_add_id(data: List[dict], _id: str) -> pd.DataFrame:
    df = pd.DataFrame(data)
    df["borehole_id"] = _id
    return df


def get_data_from_filedict(file_dict: dict) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Orders the different survey types into dataframes

    Args:
        file_dict (dict): file_dict containing metadata and data

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]: returns (tot, cpt, tlk, prv)
    """
    tot = []
    cpt = []
    tlk = []
    prv = []
    for _id, borehole in file_dict.items():
        for item in borehole:
            filetype = item["type"]
            if filetype == "snd":
                block_key = "blocks"
                blocks = item[block_key]
                for block in blocks:
                    blocktype = block["type"]
                    if blocktype == "tot" and block["data"]:
                        tot.append((block["data"], _id))
                    elif blocktype == "cpt" and block["data"]:
                        cpt.append((block["data"], _id))

            elif filetype == "prv":
                if "data" in item and item["data"]:
                    prv.append((item["data"], _id))
            elif filetype == "tlk":
                if "data" in item and item["data"]:
                    tlk.append((item["data"], _id))

    tot_list = [_convert_to_df_and_add_id(df, _id) for (df, _id) in tot]
    cpt_list = [_convert_to_df_and_add_id(df, _id) for (df, _id) in cpt]
    tlk_list = [_convert_to_df_and_add_id(df, _id) for (df, _id) in tlk]
    prv_list = [_convert_to_df_and_add_id(df, _id) for (df, _id) in prv]

    tot = pd.concat(tot_list) if tot_list else None
    cpt = pd.concat(cpt_list) if cpt_list else None
    tlk = pd.concat(tlk_list) if tlk_list else None
    prv = pd.concat(prv_list) if prv_list else None
    return tot, cpt, tlk, prv