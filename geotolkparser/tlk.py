"""
Loader for .TLK files.
"""
import re
import numpy as np
import pandas as pd
from uuid import uuid4

ROW_PATTERN = re.compile(r"([A-Za-z]*) *(\d*) *(\d*) *(\d*) *(.*)\n {1,2}(-?\d+\.\d*) *([\w ]*)\n")

CODES = {
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


def process_tlk(lines):
    """
    Process the lines from a .TLK file

    :param lines: Input lines from .TLK file
    :type lines: list of str
    :return: Dict with .TLK data
    :rtype: dict
    """
    all_lines = "".join(lines)

    # Ignore file if we have an "Autogenerert tolkning"
    if len(lines) < 3 or "Autogenerert tolkning" in all_lines:
        return None

    matches = ROW_PATTERN.findall(all_lines)

    rows = []
    for m in matches:
        if len(m) != 7:
            raise ValueError("Got invalid .TLK match: {}".format(m))
        row = {"material": m[0],
               "material_symbol": int(m[1]) if m[1] else CODES.get(m[0], 0),
               "vurdering": int(m[2]) if m[2] else np.nan,
               "klassifisering": int(m[3]) if m[3] else np.nan,
               "beskrivelse": m[4] if m[4] else np.nan,
               "kote": float(m[5]),
               "kommentar": m[6] if m[6] else np.nan}
        rows.append(row)

    if not rows:
        return None

    file_dict = {
        "type": "tlk",
        "xyz": 3 * [np.nan],
        "guid": uuid4(),
        "data": pd.DataFrame(rows)
    }
    return file_dict


