import inspect
import logging
import os
from typing import List, Optional, Union

from allensdk.brain_observatory.behavior.visualcoding_session import (
    VisualCodingSession,
)
from allensdk.brain_observatory.behavior.data_files.stimulus_file import (
    _StimulusFile,
)
from allensdk.brain_observatory.behavior.data_objects.metadata.behavior_metadata.date_of_acquisition import (  # noqa: E501
    DateOfAcquisition,
)
from allensdk.brain_observatory.behavior.image_api import Image, ImageApi
from allensdk.brain_observatory.session_api_utils import sessions_are_equal
from allensdk.core import (
    DataObject,
    JsonReadableInterface,
    NwbReadableInterface,
    NwbWritableInterface,
)
from allensdk.core.auth_config import LIMS_DB_CREDENTIAL_MAP
from allensdk.internal.api import db_connection_creator
from pynwb import NWBHDF5IO, NWBFile, ProcessingModule
from pynwb.base import Images
from pynwb.image import GrayscaleImage

class VisualCodingNWBWriter:
    """Base class for writing NWB files"""

    def __init__(
        self,
        nwb_filepath: str,
        session_data: dict,
        serializer: Union[
            JsonReadableInterface, NwbReadableInterface, NwbWritableInterface
        ],
    ):
        """

        Parameters
        ----------
        nwb_filepath: path to write nwb
        session_data: dict representation of data to instantiate `serializer`
            and write nwb
        serializer: The class to use to read `session_data` and write nwb.
            Must implement `JsonReadableInterface`, `NwbReadableInterface`,
            `NwbWritableInterface`
        """
        self._serializer = serializer
        self._session_data = session_data
        self._nwb_filepath = nwb_filepath
        self.nwb_filepath_inprogress = nwb_filepath + ".inprogress"
        self._nwb_filepath_error = nwb_filepath + ".error"

        logging.basicConfig(
            format="%(asctime)s - %(process)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )

        # Clean out files from previous runs:
        for filename in [
            self.nwb_filepath_inprogress,
            self._nwb_filepath_error,
            nwb_filepath,
        ]:
            if os.path.exists(filename):
                os.remove(filename)

    @property
    def nwb_filepath(self) -> str:
        """Path to write nwb file"""
        return self._nwb_filepath

    def write_nwb(
        self,
        id_column_name: str = "behavior_session_id",
        skip_metadata: Optional[List[str]] = None,
        skip_stim: Optional[List[str]] = None,
        **kwargs,
    ):
        """Tries to write nwb to disk. If it fails, the filepath has ".error"
        appended

        Parameters
        ----------
        id_column_name : str
            Name of the id column to pull from metadata.
        skip_metadata : list of str
            Name of key in session_data to skip when comparing to session.
        skip_stim : list of str
            Name of key in stimulus file to skip when comparing to session.
        kwargs: kwargs sent to `from_nwb`, `to_nwb`

        """
        from_lims_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k in inspect.signature(self._serializer.from_lims).parameters
        }
        lims_session = self._serializer.from_lims(
            self._session_data[id_column_name], **from_lims_kwargs
        )
        lims_session = self._update_session(lims_session, **kwargs)

        try:
            nwbfile = self._write_nwb(session=lims_session, **kwargs)
            self._compare_metadata(
                input_id=self._session_data[id_column_name],
                input_session=lims_session,
                skip_metadata=skip_metadata,
            )
            #self._compare_stimulus_file(
            #    input_id=self._session_data[id_column_name],
            #    input_session=lims_session,
            #    skip_stim=skip_stim,
            #)
            #self._compare_sessions(
            #    nwbfile=nwbfile, loaded_session=lims_session, **kwargs
            #)
            os.rename(self.nwb_filepath_inprogress, self._nwb_filepath)
        except Exception as e:
            if os.path.isfile(self.nwb_filepath_inprogress):
                os.rename(
                    self.nwb_filepath_inprogress, self._nwb_filepath_error
                )
            raise e

    def _update_session(
        self, lims_session: VisualCodingSession, **kwargs
    ) -> VisualCodingSession:
        """Call session methods to update certain values within the session.

        Should be used as part of a datarelease to resolve known data issues.
        """
        return lims_session

    def _write_nwb(self, session: VisualCodingSession, **kwargs) -> NWBFile:
        """

        Parameters
        ----------
        session_data
        kwargs: kwargs to pass to `to_nwb`

        Returns
        -------

        """
        to_nwb_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k in inspect.signature(self._serializer.to_nwb).parameters
        }
        nwbfile = session.to_nwb(**to_nwb_kwargs)

        with NWBHDF5IO(self.nwb_filepath_inprogress, "w") as nwb_file_writer:
            nwb_file_writer.write(nwbfile)
        return nwbfile

    def _compare_metadata(
        self,
        input_id: int,
        input_session: VisualCodingSession,
        skip_metadata: List[str],
    ):
        """Compare data in the metadata table and behavior/experiment session
        to each other. Raise on conflicts.

        Parameters
        ----------
        input_id : int
            Id of the session/experiment to compare.
        input_session : BehaviorSession or BehaviorOphysExperiment
            Session object we are creating an NWB file for.
        skip_metadata : list of strings
            Names of metadata keys to skip during comparison.
        """
        if skip_metadata is None:
            skip_metadata = []
        error_message = ""
        # Test BehaviorSession object metadata against the metadata from the
        # behavior session table.
        bs_metadata = input_session.metadata
        for key, bs_val in self._session_data.items():
            if key in skip_metadata:
                logging.info(f"Skipping metadata table {key} comparison...")
                continue
            if bs_val != type(bs_val)(bs_metadata[key]):
                error_message += (
                    f"Value for {key} does not match for id={input_id} "
                    f"when comparing session object metadata and associated "
                    "metadata table.\n"
                    f"\tObject data={bs_metadata[key]} and type is {type(bs_metadata[key])};\n"
                    f"\tTable data={bs_val} and type is {type(bs_val)}.\n"
                )
        if len(error_message) > 0:
            raise ValueError(error_message)

    def _compare_stimulus_file(
        self,
        input_id: int,
        input_session: VisualCodingSession,
        skip_stim: List[str],
    ):
        """Compare data in the stimulus file and loaded session/experiment to
        each other. Raise on conflicts.

        Parameters
        ----------
        input_id : int
            Id of the session/experiment to compare.
        input_session : BehaviorSession or BehaviorOphysExperiment
            Session object we are creating an NWB file for.
        skip_stim : list of strings
            Names of stimulus file keys to skip during comparison.
        """
        if skip_stim is None:
            skip_stim = []
        error_message = ""
        ophys_session_id = input_session.ophys_session_id
        db_conn = db_connection_creator(
            fallback_credentials=LIMS_DB_CREDENTIAL_MAP
        )
        stimulus_file = _StimulusFile.from_lims_for_ophys_session(
            db=db_conn, ophys_session_id=ophys_session_id
        )
        stim_file_methods = dir(stimulus_file)
        for key, bs_val in input_session.metadata.items():
            if key in skip_stim:
                logging.info(f"Skipping stimulus file {key} comparison...")
                continue
            if key in stim_file_methods:
                stim_value = getattr(stimulus_file, key)
                if key == "date_of_acquisition":
                    stim_value = DateOfAcquisition(stim_value).value
                if bs_val != stim_value:
                    error_message += (
                        f"Value for {key} does not match for id={input_id} "
                        "when comparing session object metadata and data from "
                        "the behavior stimulus pickle file.\n"
                        f"\tObject data={bs_val};\n"
                        f"\tStim data={stim_value}\n"
                    )
        if len(error_message) > 0:
            raise ValueError(error_message)

    def _compare_sessions(
        self, nwbfile: NWBFile, loaded_session: DataObject, **kwargs
    ):
        kwargs = {
            k: v
            for k, v in kwargs.items()
            if k in inspect.signature(self._serializer.from_nwb).parameters
        }
        nwb_session = self._serializer.from_nwb(nwbfile, **kwargs)
        assert sessions_are_equal(loaded_session, nwb_session, reraise=True)