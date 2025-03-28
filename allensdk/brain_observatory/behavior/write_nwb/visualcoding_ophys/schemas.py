import marshmallow as mm
import pandas as pd
from allensdk.brain_observatory.behavior.behavior_project_cache.tables.metadata_table_schemas import BehaviorSessionMetadataSchema
from allensdk.brain_observatory.behavior.write_nwb.behavior.schemas import (
    RaisingSchema,
)
from allensdk.brain_observatory.behavior.schemas import BehaviorMetadataSchema, OphysMetadataSchema
from argschema import ArgSchema
from argschema.fields import Int, List, Nested, OutputFile, LogLevel, Nested, OutputDir,String, Bool, Dict, Float

class VisualCodingInputSchema(ArgSchema):
    class Meta:
        unknown = mm.RAISE

    log_level = LogLevel(
        default="INFO", description="Logging level of the module"
    )
    skip_metadata_key = List(
        String,
        required=False,
        cli_as_single_argument=True,
        description="List of metadata table keys to skip. Can be used to "
        "override known data issues. Example: ['mouse_id']",
        default=[],
    )
    skip_stimulus_file_key = List(
        String,
        required=False,
        cli_as_single_argument=True,
        description="List of stimulus file keys to skip. Can be used to "
        "override known data issues. Example: ['mouse_id']",
        default=[],
    )
    output_dir_path = OutputDir(
        required=True,
        description="Path of output.json to be written",
    )
    include_experiment_description = Bool(
        required=False,
        description="If True, include experiment description in NWB file.",
        default=True
    )

class VisualCodingExperimentMetadataSchema(BehaviorSessionMetadataSchema):
    emission_lambda = Float(
        required=False,
        description="Emission wavelength in the experiment."
    )
    excitation_lambda = Float(
        required=False,
        description="Excitation wavelength in the experiment."
    )
    field_of_view_height = Int(
        required=False,
        description="Field of view height."
    )
    field_of_view_width = Int(
        required=False,
        description="Field of view width."
    )
    imaging_depth = Int(
        required=True, description="Imaging depth of the OphysExperiment."
    )
    imaging_plane_group = Int(
        required=True,
        allow_none=True,
        description="Imaging plane group of OphysExperiment.",
    )
    indicator = String(required=True, description="String indicator line.")
    experiment_container_id = Int(
        required=True,
        description="ID of ophys container of which this experiment is a "
        "member.",
    )
    ophys_experiment_id = Int(
        required=True, description="ID of the ophys experiment."
    )
    ophys_session_id = Int(
        required=True,
        description="ID of the ophys session this experiment is a member of.",
    )
    ophys_fovs = dict(
        description = "Dictionary of optical fields of view. Each key contains a different imaging plane as a dictionary."
    )
    stimulus_frame_rate = Float(
        required=False,
        allow_none=True,
        description="Stimulus frame rate."
    )
    targeted_imaging_depth = Int(
        required=True,
        description="Average of all experiments in the container.",
    )
    targeted_structure = String(
        required=True, description="String name of the structure targeted."
    )

class VisualCodingInputSchema(VisualCodingInputSchema):
    ophys_experiment_id = Int(
        required=True, description="Id of OphysExperiment to create."
    )

    ophys_container_experiment_ids = List(
        Int,
        required=False,
        cli_as_single_argument=True,
        description="Subset of the experiment ids in the same container to be "
        "released. Experiment Ids are pulled from input metadata "
        "table. Useful for when experiments are excluded from the "
        "release and certain summary values (e.g. "
        "targeted_imaging_depth) must be recalculated from the "
        "released experiments.",
        default=[],
    )

    ophys_experiment_metadata = Nested(
        VisualCodingExperimentMetadataSchema,
        required=True,
        description="Data pertaining to an ophys experiment.",
    )

class OutputSchema(RaisingSchema):
    input_parameters = Nested(VisualCodingInputSchema)
    output_path = OutputFile(
        required=True,
        description="Path of output NWB file.",
    )

class VisualCodingMetadataSchema(BehaviorMetadataSchema, OphysMetadataSchema):
    "This schema is used as a template for the necessary NWB extension."
    neurodata_type = 'VisualCodingMetadata'
    neurodata_type_inc = 'VisualCodingOphysMetadata'
    neurodata_doc = "Metadata for Visual Coding 2p experiments"
    # Fields to skip converting to extension
    # They already exist as attributes for the following pyNWB classes:
    # OpticalChannel, ImagingPlane, NWBFile
    neurodata_skip = {"emission_lambda", "excitation_lambda", "indicator",
                      "targeted_structure", "date_of_acquisition",
                      "ophys_frame_rate"}
