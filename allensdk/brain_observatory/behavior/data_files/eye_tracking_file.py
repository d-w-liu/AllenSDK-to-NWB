from typing import Optional, Union
from pathlib import Path

import pandas as pd

from allensdk.brain_observatory.behavior.eye_tracking_processing import \
    load_eye_tracking_hdf
from allensdk.internal.api import PostgresQueryMixin, OneResultExpectedError
from allensdk.internal.core.lims_utilities import safe_system_path
from allensdk.internal.core import DataFile


class EyeTrackingFile(DataFile):
    """A DataFile which contains methods for accessing and loading
    eye tracking data.
    """

    def __init__(self, filepath: Union[str, Path]):
        super().__init__(filepath=filepath)

    @classmethod
    def from_json(cls, dict_repr: dict) -> "EyeTrackingFile":
        filepath = dict_repr["eye_tracking_filepath"]
        return cls(filepath=filepath)

    @classmethod
    def from_lims(
        cls, db: PostgresQueryMixin,
        behavior_session_id: Optional[Union[int, str]] = None,
        ophys_experiment_id: Optional[Union[int, str]] = None
    ) -> "EyeTrackingFile":
        if behavior_session_id is not None:
            query = f"""
                    SELECT wkf.storage_directory || wkf.filename AS eye_tracking_file
                    FROM behavior_sessions bs
                    JOIN ophys_sessions os ON os.id = bs.ophys_session_id
                    LEFT JOIN well_known_files wkf ON wkf.attachable_id = os.id
                    JOIN well_known_file_types wkft ON wkf.well_known_file_type_id = wkft.id
                    WHERE wkf.attachable_type = 'OphysSession'
                        AND wkft.name = 'EyeTracking Ellipses'
                        AND bs.id = {behavior_session_id};
                    """  # noqa E501
        elif ophys_experiment_id is not None:    
            query = f"""
                    SELECT wkf.storage_directory || wkf.filename AS eye_tracking_file
                    FROM ophys_experiments oe
                    LEFT JOIN well_known_files wkf ON wkf.attachable_id = oe.ophys_session_id
                    JOIN well_known_file_types wkft ON wkf.well_known_file_type_id = wkft.id
                    WHERE wkf.attachable_type = 'OphysSession'
                        AND wkft.name = 'EyeTracking Ellipses'
                        AND oe.id = {ophys_experiment_id};
                    """  # noqa E501
        else:
            raise RuntimeError(
                "Eye tracking file requires an ID"
            )
        try:
            filepath = db.fetchone(query, strict=True)
        except OneResultExpectedError:
            return None
        return cls(filepath=filepath)

    @staticmethod
    def load_data(filepath: Union[str, Path]) -> pd.DataFrame:
        filepath = safe_system_path(file_name=filepath)
        # TODO move the contents of this function here
        return load_eye_tracking_hdf(filepath)
