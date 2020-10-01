import numpy as np
from typing import Callable, Tuple, List
from .mappings import *
from uuid import uuid4

_KNOWN_SURVEY_CODES = [7, 10, 21, 22,  23, 24,  25, 26]
_MIN_ROWS_TOT = 10
_SURVEY_CODE_TO_TEXT = {
    25: "tot",
    7: "cpt"
}

_DATETIME_FMTS = [
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%Y%m0%d",
    "%d.%m.%y",
    "%Y-%d-%m"
]


_CODES = {
    "": 0,
    "berg": 1,
    "BelBl": 40,
    "block": 2,
    "friktjord": 36,
    "fyllning": 13,
    "grus": 32,
    "gyttja": 8,
    "mylla": 19,
    "kvicklera": 34,
    "lera": 11,
    "moraen": 35,
    "sand": 20,
    "silt": 21,
    "sten": 39,
    "torrskorpa": 33,
    "torv": 27,
}

def _parse_metadata_block(block: list, mapping: dict) -> dict:
    block_parsed = {}
    for key1, value1 in mapping.items():
        if "nested" in value1.keys():
            for key2, value2 in value1["nested"].items():
                try:
                    line_vals = block[value1["index"]].split()
                    block_parsed[key2] = value2["dtype"](line_vals[value2["index"]])
                except (IndexError, ValueError):
                    block_parsed[key2] = np.nan
        else:
            try:
                block_parsed[key1] = value1["dtype"](block[value1["index"]])
            except IndexError:
                block_parsed[key1] = np.nan
    return block_parsed


def _parse_data_block(block: List[str], mapping: dict, line_split_func: Callable) -> List[dict]:
    parsed_lines = []
    for line in block:
        row = {}
        line_vals = line_split_func(line)
        for key, value in mapping.items():
            try:
                row[key] = value["dtype"](line_vals[value["index"]])
            except (IndexError, ValueError):
                row[key] = np.nan
        parsed_lines.append(row)
    return parsed_lines


def _tot_split_func(line: str) -> List[str]:
    return line.split()


def _prv_split_func(line: str) -> List[str]:
    return line.split()


def _cpt_split_func(line: str, comment_char_length: int=25) -> list:
    # split line on whitespace to get four first values
    first_values = line.split()[:4]
    # find index of the fourth value in string
    index_str = f" {first_values[-1]} "
    fourth_index = line.index(index_str)
    # Extract the comment with fixed max character length
    start_index_comment = fourth_index + len(first_values[-1]) + 1
    stop_index_comment = start_index_comment + comment_char_length
    comment = line[start_index_comment:stop_index_comment]
    #split the last potential four values in the same way as the first
    last_values = line[stop_index_comment:].split()
    # concatenate the lists to one list
    return list(first_values) + [str(comment).strip()] + list(last_values)


def _parse_unknown_data_block(block: list) -> Tuple[dict, list]:
    # We know that data blocks has metadata in the two first lines
    metadata_lines = block[:2]
    # The data is contained in the remaining lines
    data_lines = block[2:]

    # Get metadata
    metadata = _parse_metadata_block(metadata_lines, data_block_metadata_mapping)
    # Find out which type of data block it is
    survey_type = _get_data_block_survey_type(metadata)
    
    # Total soundings (code 25)
    if survey_type == 25:
        data = _parse_data_block(data_lines, tot_data_mapping, _tot_split_func)
    # CPT (code 7)
    elif survey_type == 7:
        data = _parse_data_block(data_lines, cpt_data_mapping, _cpt_split_func)
    else:
        msg = f"Unknown survey_type {survey_type}" 
        raise ValueError(msg)
    
    if not data:
        msg = f"No data found"
        raise ValueError(msg)

    return metadata, data


def _try_parse_datetime(datestr: str) -> datetime:
    for fmt in _DATETIME_FMTS:
        try:
            return datetime.strptime(datestr, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse string as datetime {datestr}")


def _is_data_block(block: list) -> bool:
    # Data blocks is characterized by the first line containing the survey code and the date
    # Check the first line
    first_line = block[0]
    first_line_vals = first_line.split()
    if len(first_line_vals) != 2:
        return False
    survey_code = first_line_vals[0]
    date = first_line_vals[1]
    try:
        if survey_code.isdigit() and int(survey_code) in _KNOWN_SURVEY_CODES:
            _ = _try_parse_datetime(date)
            return True
    except Exception:
        if date.isdigit():
            return True
        return False
    return False


def _is_unknown_material(block):
    # if material is "Annet", no material_text1 is present
    # This is the last value in the first line
    material_text_2 = block[0].split()[-1]
    if material_text_2 == "Annet":
        return True
    return False


def _add_empty_value_as_material_text_1(block):
    #For the first line, we need to add a "None" in the start
    temp_block = block.copy()
    temp_block[0] = "None" + temp_block[0]
    return temp_block


def _extract_and_add_symbol_text(data: list) -> list:
    temp_data = data.copy()
    for row in temp_data:
        symbol = row["symbol"]
        soiltypes = _label_from_symbol(symbol)
        row["symbol_soiltype"] = " ".join(soiltypes)
    if not row["symbol_soiltype"]:
        row["symbol_soiltype"] = np.nan
    return temp_data


def _is_unknown_metadata_block(block: list) -> bool:
    try:
        _parse_metadata_block(block, cpt_unknown_block_mapping)
        return True
    except Exception:
        return False


def _get_data_block_survey_type(data_block_metadata: dict, survey_type_key: str="survey_type_code") -> int:
    if survey_type_key not in data_block_metadata.keys():
        raise IndexError(f"Key {survey_type_key} not found in the metadata")
    else:
        return data_block_metadata[survey_type_key]
    

def _split_tlk_to_blocks(lines: list) -> list:
    # Each interpretation in a .tlk file spans three lines. The file is always ended with a *
    blocks = []
    block = []
    c = 0
    for line in lines:
        if line == "*":
            break
        if c == 3:
            blocks.append(block)
            block = []
            c = 0
        block.append(line)
        c += 1
    blocks.append(block)
    return blocks


def path_to_lines(path: str) -> List[str]:
    """Opens, and converts the file located in path to a list of lines in the file

    Args:
        path (str): absolute path to the file

    Returns:
        List[str]: List where each element is a line in the file
    """
    with open(path, "r", encoding="latin-1") as f:
        lines = f.readlines()
    lines = [l.replace("\n", "") for l in lines]
    return lines


def _get_blocks(lines: list) -> list:
    blocks, current_block = [], []
    for line in lines:
        if line == "*":
            blocks.append(current_block)
            current_block = []
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)
    # Remove empty blocks
    return [b for b in blocks if b]


def _modify_indicator_by_code(code: int, indicators: dict) -> dict:
    if code in geosuite_code_to_label.keys():
        indicators["comment_label"].append(code)
    elif code == 70:
        indicators["okt_rotasjon"] = 1
    elif code == 71:
        indicators["okt_rotasjon"] = 0
    elif code == 72:
        indicators["spyling"] = 1
    elif code == 73:
        indicators["spyling"] = 0
    elif code == 74:
        indicators["slag"] = 1
    elif code == 75:
        indicators["slag"] = 0
    elif code == 76:
        indicators["slag"] = 1
        indicators["spyling"] = 1
    elif code == 77:
        indicators["slag"] = 0
        indicators["spyling"] = 0
    elif code == 78:
        indicators["pumping"] = 1
    elif code == 79:
        indicators["pumping"] = 0
    
    return indicators

def _merge_comments_to_single_label(comment_label: List[str]) -> int:
    # For now, return the highest code
    return max(comment_label)



def _convert_comment_codes_to_indicator_columns(parsed_snd_block: list) -> dict:
    # Go through the rows of the datablock
    temp_block = parsed_snd_block.copy()
    res = []
    for row in temp_block:
        
        # Initialize indicators
        indicators = {
            "okt_rotasjon": np.nan,
            "spyling": np.nan,
            "slag": np.nan,
            "pumping": np.nan,
            "comment_label": []
        }
        
        # If we have a comment
        comments = row["kommentar"]
        if isinstance(comments, str):
            # for each comment in comments
            for code in comments.split():
                # Convert textcodes to codes for convenience when going ahead
                if code in geosuite_textcode_to_code.keys():
                    code = geosuite_textcode_to_code[code]
                # Check if it is a valid code
                if code in geosuite_textcode_to_code.values():
                    # If it is, then do actions based on the code
                    indicators = _modify_indicator_by_code(int(code), indicators)
        if indicators["comment_label"]:
            indicators["comment_label"] = _merge_comments_to_single_label(indicators["comment_label"])
        else:
            indicators["comment_label"] = np.nan
        row = {**row, **indicators}
        res.append(row)
    return res


def _initialize_empty_mapping(mapping: dict) -> dict:
    block_parsed = {}
    for key1, value1 in mapping.items():
        if "nested" in value1.keys():
            for key2, _ in value1["nested"].items():
                    block_parsed[key2] = np.nan
        else:
                block_parsed[key1] = np.nan
    return block_parsed    

def _label_from_symbol(symbol: int) -> list:
    """
    Convert Geosuite's 'symbol' column to a list of labels.

    :param symbol: Symbol
    :type symbol: int | str
    :return: Label list
    :rtype: list of str | np.nan
    """

    symbol = int(symbol)
    if symbol < 0:
        bin_str = str(bin(abs(symbol)))[2:].zfill(13)
        label = [_SYMBOL_LABELS_NEG[pos] for pos, bit in enumerate(reversed(bin_str)) if bit == "1"]
    elif symbol > 0:
        label = [_SYMBOL_LABELS_POS[int(i)] for i in str(symbol)]
    else:
        label = []
    return label or []


def parse_tlk_file(lines: List[str]) -> dict:
    """Parses tlk-files

    Args:
        lines (List[str]): List of lines in the tlk file

    Returns:
        dict: data contained in the tlk-file
    """
    errors = []
    # Check for empty file (no lines)
    if not lines:
        errors.append("No lines found. Could not parse file")
        return {"type": "tlk", "data": [], "errors": errors}
    #First, split lines into blocks/rows
    blocks = _split_tlk_to_blocks(lines)
    #Then, go through each block and parse
    rows = []
    for block in blocks:
        try:
            #If we have "Annet" material we need to modify the data for parsing
            if _is_unknown_material(block):
                block = _add_empty_value_as_material_text_1(block)
            #Now we can parse the file according to the mapping
            row = _parse_metadata_block(block, tlk_data_mapping)
            # If we dont have a value for material_code, check if we can get one from material
            row["material_code"] = row["material_code"] if not np.isnan(row["material_code"]) else _CODES.get(row["material"], 0)
            rows.append(row)
        except Exception as e:
            errors.append(str(e))
    return {"type": "tlk", "data": rows, "errors": errors}


def parse_snd_file(lines: List[str], min_blocks: int=3) -> dict:
    """Parses a snd file. These files may contain up to one tot-file and/or up to one cpt-file

    Args:
        lines (List[str]): snd-files as a list of lines
        min_blocks (int, optional): Minimum number of blocks in file, otherwise it gets discarded. Defaults to 3.

    Returns:
        dict: dictionary containing metadata and data from the snd file
    """
    # Initialize list of errors
    errors = []

    # Create index going through blocks
    block_index = 0
    # first, split the lines into blocks
    blocks = _get_blocks(lines)
    # Initialize empty metadata
    metadata ={
            **_initialize_empty_mapping(first_block_mapping),
            **_initialize_empty_mapping(second_block_mapping),
            **_initialize_empty_mapping(third_block_mapping)
            }

    # Check that we at least have 3 blocks. If we dont return the errors
    if len(blocks) < min_blocks:
        msg = f"File contains less than {min_blocks} blocks. Cannot parse"
        errors.append(msg)
        return {"type": "snd", **metadata, "blocks": [], "errors": errors}

    # We know that the first block is always present for .SND files
    first_block = _parse_metadata_block(blocks[block_index], first_block_mapping)
    block_index += 1
    # We also know that the second block is always present
    try:
        second_block = _parse_metadata_block(blocks[block_index], second_block_mapping)
        block_index += 1
    except ValueError:
        msg = f"File doesnt contain second metadatablock. Cannot parse"
        errors.append(msg)
        return {"type": "snd", **metadata, "blocks": [], "errors": errors}
    # In some old formats, the third metadata block containing guid is missing
    # We check if the third block can be parsed as data. If we can't we assume its a metadata block
    third_block = _initialize_empty_mapping(third_block_mapping)
    if not _is_data_block(blocks[block_index]):
        third_block = _parse_metadata_block(blocks[block_index], third_block_mapping)
        block_index += 1
    # Merge the three first blocks to one dictionary
    snd_metadata = {**first_block, **second_block, **third_block}
    # After this, we dont know what we get, we can get either a tot, a cpt, both or none, so we loop through the remaining blocks to see what we find
    data_blocks = []
    for current_block_index, block in enumerate(blocks[block_index:]):
        if _is_data_block(block):
            try:
                metadata, data = _parse_unknown_data_block(block)
                survey_type = metadata["survey_type_code"]
                metadata["type"] = _SURVEY_CODE_TO_TEXT[metadata["survey_type_code"]]
                if _is_valid_data(data, survey_type):
                    # If the survey type was CPT, we know that an unknown metadata file is attached at the end. We also suppose that the CPT is the last data block in the SND file, so we can finish up the file
                    if survey_type == 7:
                        try:
                            cpt_unknown_metadata_block = blocks[block_index + current_block_index + 1]
                            cpt_unknown_metadata = _parse_metadata_block(cpt_unknown_metadata_block, cpt_unknown_block_mapping)
                        except IndexError:
                            cpt_unknown_metadata = _initialize_empty_mapping(cpt_unknown_block_mapping)
                        metadata = {**metadata, **cpt_unknown_metadata}
                        data_blocks.append({**metadata, "data": data})
                        break

                    # For tot-files, we need to convert the comment codes to indicator columns
                    elif survey_type == 25:
                        data = _convert_comment_codes_to_indicator_columns(data)
                        data_blocks.append({**metadata, "data": data})

                    else:
                        msg = f"Unknown survey type {survey_type}"
                        errors.append(msg)
                else:
                    errors.append(f"File contains {len(data)} lines, must contain {_MIN_ROWS_TOT} to be able to be parsed")
                    data_blocks.append({**metadata, "data": []})
            except ValueError as e:
                errors.append(str(e))
        else:
            msg = "One or more of the data blocks is not valid"
            errors.append(msg)
    return {"type": "snd", **snd_metadata, "blocks": data_blocks, "errors": errors
           }


def _is_valid_data(data: dict, filetype:str) -> bool:
    if filetype == 25:
        # If the number of rows is less than a threshold, return false
        if len(data) < _MIN_ROWS_TOT:
            return False    
    elif filetype == 7:
        pass
    else:
        raise ValueError(f"Unknown filetype {filetype}")

    return True

def parse_prv_file(lines: List[str]) -> dict:
    """Parses a prv file

    Args:
        lines (list): prv file as lines

    Returns:
        dict: dictionary with data and metadata from the prv file
    """
    errors = []
    # First split lines into blocks
    blocks = _get_blocks(lines)
    # We know that the first block contains metadata
    metadata = _parse_metadata_block(blocks[0], prv_metadata_mapping)
    # If we have only one block, data is none
    if len(blocks) < 2:
        data = []
        errors.append("PRV contains less than 2 blocks. Cannot parse")
    else:
        # We know that the second block contains the data
        try:
            data = _parse_data_block(blocks[1], prv_data_mapping, _prv_split_func)
            # We want to translate the symbols to soil types
            data = _extract_and_add_symbol_text(data)
        except ValueError:
            data = []
    
    return {"type": "prv", **metadata, "data": data, "errors": errors}


_SYMBOL_LABELS_NEG = [
    'Leire',
    'Fyllemasse',
    'Grus',
    'Matjord',
    'Berg',
    'Sand',
    'Skjell',
    'Silt',
    'Stein & blokk',
    'Morene',
    'Torv',
    'Gytje, dy',
    'Trerester'
    'Kvikkleire'
]
_SYMBOL_LABELS_POS = [
    np.nan,
    "Leire",
    "Silt",
    "Sand",
    "Grus",
    "Stein",
    "Fyllemasse",
    "Matjord",
    "Trerester",
    "Skjell",
    "Kvikkleire"
]
