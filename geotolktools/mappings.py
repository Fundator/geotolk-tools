from datetime import datetime
import numpy as np


# Waiting to fill these after feedback from geotechnicians
VALID_RANGES_TOT = {
    "dybde": {"min": 0, "max": np.inf},
    "trykk": {"min": -np.inf, "max": np.inf},
    "spyle": {"min": 0, "max": np.inf},
    "sek10": {"min": 0, "max": np.inf},
}


first_block_mapping = {
    "x": {"index": 0, "dtype": float},
    "y": {"index": 1, "dtype": float},
    "z": {"index": 2, "dtype": float},
    "profil": {"index": 3, "dtype": float},
    "avsett": {"index": 4, "dtype": float},
    "foi": {"index": 5, "nested": 
            {"forboret": {"index": 0, "dtype": float},
            "orientering": {"index": 1, "dtype": int},
            "inklinasjon": {"index": 2, "dtype": float}
            }
    }
}

second_block_mapping= {
    "second_block_unknown_1": {"index": 0, "dtype": int},
    "second_block_unknown_2": {"index": 1, "nested": {
        "second_block_unknown_2_1": {"index": 0, "dtype": int},
        "second_block_unknown_2_2": {"index": 1, "dtype": int}
        }
      }
}

third_block_mapping = {
    "third_block_unknown_1": {"index": 0, "dtype": int},
    "guid": {"index": 1, "nested": {"guid": {"index": 1, "dtype": str}
                                   }
            },
    "guid_2": {"index": 2, "dtype": str},
    "project_name": {"index": 3, "dtype": str},
    "original_filename": {"index": 4, "dtype": str}
}

data_block_metadata_mapping = {
    "data_block_first_line": {"index": 0, "nested": {
        "survey_type_code": {"index": 0, "dtype": int},
        "date": {"index": 1, "dtype": lambda x: str(datetime.strptime(x, "%d.%m.%Y"))},
        }
    },
    "data_block_second_line": {"index": 1, "nested": {
        "data_block_unknown_2_1": {"index": 0, "dtype": float},
        "stoppkode": {"index": 1, "dtype": int},
        "data_block_unknown_2_2": {"index": 2, "dtype": int},
        "data_block_unknown_2_3": {"index": 3, "dtype": int},
        "data_block_unknown_2_4": {"index": 4, "dtype": int},
        "lopenummer": {"index": 5, "dtype": int},
        "original_filename": {"index": 6, "dtype": lambda x: str(x).replace("*", " ") if x != "GUID" else np.nan},
        "guid": {"index": -1, "dtype": str}
        }
    }
}

tot_data_mapping = {
    "dybde": {"index": 0, "dtype": float},
    "trykk": {"index": 1, "dtype": int},
    "spyle": {"index": 2, "dtype": int},
    "sek10": {"index": 3, "dtype": int},
    "kommentar": {"index": slice(4, None), "dtype": lambda x: " ".join(list(x)) if (len(list(x)) > 0) else np.nan}
}

cpt_data_mapping = {
    "dybde": {"index": 0, "dtype": float},
    "spisstrykk": {"index": 1, "dtype": int},
    "poretrykk": {"index": 2, "dtype": int},
    "friksjon": {"index": 3, "dtype": int},
    "kommentar": {"index": 4, "dtype": lambda x: x if x != "" else np.nan},
    "trykk": {"index": 5, "dtype": int},
    "resistivitet": {"index": 6, "dtype": float},
    "helning": {"index": 7, "dtype": float},
    "temperatur": {"index": 8, "dtype": float}
}

tlk_data_mapping = {
    "line1": {
        "index": 0, "nested": {
            "material": {"index": 0, "dtype": lambda x: str(x) if x != "None" else np.nan},
            "material_code": {"index": 1, "dtype": int},
            "vurdering": {"index": 2, "dtype": int},
            "klassifisering": {"index": 3, "dtype": int},
            "Lagerbeskrivelse": {"index": 4, "dtype": str}
        }
    },
    "line2": {
        "index": 1, "nested": {
            "kote": {"index": 0, "dtype": float},
            "kommentar": {"index": 1, "dtype": str}
        }
    },  
    "line3": {
        "index": 2, "nested": {
            "unknown_tlk_1": {"index": 0, "dtype": float},
            "unknown_tlk_2": {"index": 1, "dtype": float},
            "unknown_tlk_3": {"index": 2, "dtype": float},
            "unknown_tlk_4": {"index": 3, "dtype": float},
            "unknown_tlk_5": {"index": 4, "dtype": float},
            "unknown_tlk_6": {"index": 5, "dtype": float}
        }
    }
}

cpt_unknown_block_mapping = {"unknown_unknown_1": {"index": 0, "dtype": int},
                         "NA1": {"index": 1, "nested": {"NA1": {"index": 1, "dtype": float}}},
                         "NB1": {"index": 2, "nested": {"NB1": {"index": 1, "dtype": float}}},
                         "NC1": {"index": 3, "nested": {"NC1": {"index": 1, "dtype": float}}},
                         "NA2": {"index": 4, "nested": {"NA2": {"index": 1, "dtype": float}}},
                         "NB2": {"index": 5, "nested": {"NB2": {"index": 1, "dtype": float}}},
                         "NC2": {"index": 6, "nested": {"NC2": {"index": 1, "dtype": float}}},
                         "HN": {"index": 7, "nested": {"HN": {"index": 1, "dtype": float}}},
                         "KF": {"index": 8, "nested": {"KF": {"index": 1, "dtype": float}}},
                         "KQ": {"index": 9, "nested": {"KQ": {"index": 1, "dtype": float}}},
                         "KU": {"index": 10, "nested": {"KU": {"index": 1, "dtype": float}}},
                         "MA": {"index": 11, "nested": {"MA": {"index": 1, "dtype": float}}},
                         "MB": {"index": 12, "nested": {"MB": {"index": 1, "dtype": float}}}
                        }


prv_metadata_mapping = {
    "metadata_line": {
        "index": 0, "nested": {
            "value1": {"index": 0, "dtype": str},
            "value2": {"index": 1, "dtype": float},
            "date": {"index": 2, "dtype": lambda x: str(datetime.strptime(x, "%d.%m.%Y")) if not x.isdigit() else np.nan},
            "value3": {"index": 3, "dtype": int},
            "guid": {"index": 5, "dtype": str}
            }
        }
    }


prv_data_mapping = {
    "prove_nr": {"index": 0, "dtype": str},
    "symbol": {"index": 1, "dtype": int},
    "dybde": {"index": 2, "dtype": float},
    "w": {"index": 3, "dtype": float},
    "wp": {"index": 4, "dtype": float},
    "wl": {"index": 5, "dtype": float},
    "suu": {"index": 6, "dtype": float},
    "suo": {"index": 7, "dtype": float},
    "sue": {"index": 8, "dtype": float},
    "bruddef_pct": {"index": 9, "dtype": int},
    "gamma": {"index": 10, "dtype": float},
    "glodetap": {"index": 11, "dtype": float},
    "jordart": {"index": slice(12,None), "dtype": lambda x: " ".join(x) if x else np.nan}
}

geosuite_textcode_to_code = {
    "Fy": "30",
    "Tø": "31",
    "Le": "32",
    "Si": "33",
    "Sa": "34",
    "Gr": "35",
    "Mo": "36",
    "To": "37",
    "Gy": "38",
    "St": "40",
    "B1": "41",
    "B2": "42",
    "F": "43",
    "@": "60",
    "GV": "61",
    "R1": "70",
    "R2": "71",
    "Y1": "72",
    "Y2": "73",
    "S1": "74",
    "S2": "75",
    "D1": "76",
    "D2": "77",
    "P1": "78",
    "P2": "79",
    "MY": "81"
}

geosuite_code_to_label = {
    10: "stoppkote_tidl_forsøk",
    11: "lengre_opphold",
    30: "fyllmasse",
    31: "torrskorpe",
    32: "leire",
    33: "silt",
    34: "sand",
    35: "grus",
    36: "morene",
    37: "torv",
    38: "gytje",
    40: "stein_blokk",
    41: "stein_gjennomboring",
    42: "sluttnivaa_stein",
    43: "fjell",
    60: "boyd_borstang",
    61: "antatt_grunnvannskote",
    81: "terrengoverflate"
}

#List of features for use in catboost-model
RAW_FEATURES = [    
    'dybde', 
    'trykk', 
    'sek10',
    'spyle',
    'spyling',
    'okt_rotasjon',
    'slag']

CALCULATED_FEATURES = [
    'trykk_rolling_median_10',
    'trykk_rolling_median_absolute_deviation_10',
    'trykk_rolling_sum_10', 
    'sek10_rolling_median_10',
    'sek10_rolling_median_absolute_deviation_10', 
    'sek10_rolling_sum_10',
    'spyle_rolling_median_10',
    'spyle_rolling_median_absolute_deviation_10',
    'spyle_rolling_sum_10', 
    'bortid_rolling_median_10',
    'bortid_rolling_median_absolute_deviation_10', 
    'bortid_rolling_sum_10',
    'okt_rotasjon_rolling_sum_10', 
    'spyling_rolling_sum_10',
    'slag_rolling_sum_10', 
    'trykk_rolling_median_50',
    'trykk_rolling_median_absolute_deviation_50',
    'trykk_rolling_sum_50', 
    'sek10_rolling_median_50',
    'sek10_rolling_median_absolute_deviation_50', 
    'sek10_rolling_sum_50',
    'spyle_rolling_median_50',
    'spyle_rolling_median_absolute_deviation_50',
    'spyle_rolling_sum_50', 
    'bortid_rolling_median_50',
    'bortid_rolling_median_absolute_deviation_50',
    'bortid_rolling_sum_50',
    'okt_rotasjon_rolling_sum_50', 
    'spyling_rolling_sum_50',
    'slag_rolling_sum_50', 
    'trykk_rolling_median_100',
    'trykk_rolling_median_absolute_deviation_100',
    'trykk_rolling_sum_100', 
    'sek10_rolling_median_100',
    'sek10_rolling_median_absolute_deviation_100', 
    'sek10_rolling_sum_100',
    'spyle_rolling_median_100',
    'spyle_rolling_median_absolute_deviation_100',
    'spyle_rolling_sum_100', 
    'bortid_rolling_median_100',
    'bortid_rolling_median_absolute_deviation_100',
    'bortid_rolling_sum_100', 
    'okt_rotasjon_rolling_sum_100',
    'spyling_rolling_sum_100', 
    'slag_rolling_sum_100', 
    'pressure_diff']

MODEL_FEATURES = RAW_FEATURES + CALCULATED_FEATURES
