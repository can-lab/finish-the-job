"""Finish the job.

Nipype pipeline for common preprocessing steps after fMRIprep:

- Spatial smoothing
- Temporal filtering
- Timecourse normalization

Dependencies:

- nipype
- niflow-nipype1-workflows
- nilearn
- nibabel

"""


import os

import nibabel as nib
from nilearn.input_data import NiftiMasker
from nipype import Node, MapNode, Workflow
from nipype.interfaces import utility, fsl, io
from nipype.interfaces.base import BaseInterface, \
        BaseInterfaceInputSpec, traits, File, Str, TraitedSpec
from niflow.nipype1.workflows.fmri.fsl.preprocess import create_susan_smooth


class TimecourseNormalizationInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, desc="functional image")
    mask_file = File(exists=True, desc="mask image")
    method = Str(desc="normalization method ('z' or 'psc')")

class TimecourseNormalizationOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="functional image")

class TimecourseNormalization(BaseInterface):
    input_spec = TimecourseNormalizationInputSpec
    output_spec = TimecourseNormalizationOutputSpec

    def _run_interface(self, runtime):
        orig_units = nib.load(self.inputs.in_file).header.get_xyzt_units()
        masker = NiftiMasker(mask_img=self.inputs.mask_file,
                             standardize=self.inputs.method)
        standard_mat = masker.fit_transform(self.inputs.in_file)
        standard_image = masker.inverse_transform(standard_mat)
        standard_image.header.set_xyzt_units(orig_units[0], orig_units[1])
        nib.save(standard_image, 'normalized.nii.gz')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath('normalized.nii.gz')

        return outputs

def create_timecourse_normalization_workflow(method="Zscore", name="normalization"):
    """Create a timcourse normalization workflow.

    Parameters
    ==========
    method : str, optional
        the normalization method ("Zscore" or "PSC"; default="Zscore")
    name : str, optional
        the name of the workflow (default="normalization")

    Returns
    =======
    normalization : nipype.Workflow object
        the timecourse normalization worklfow object

    """

    normalization = Workflow(name=name)
    inputspec = Node(utility.IdentityInterface(fields=['in_files',
                                                       'mask_files']),
                     name='inputspec')

    tn = MapNode(TimecourseNormalization(),
                                iterfield=['in_file', 'mask_file'],
                                name='normalize')
    tn.inputs.method = method.lower()

    outputspec = Node(utility.IdentityInterface(fields=['normalized_files']),
                      name='outputspec')

    normalization.connect(inputspec, 'in_files', tn, 'in_file')
    normalization.connect(inputspec, 'mask_files', tn, 'mask_file')
    normalization.connect(tn, 'out_file', outputspec, 'normalized_files')

    return normalization

def create_temporal_filter(cutoffs=[100, None], name='tempfilt'):
    """Create a temporal filter workflow.

    Parameters
    ==========
    cutoffs : list, optional
        the high and low cutoff value in seconds (default=[100, None])
    name : str, optional
        the name of the workflow (default="tempfilt")

    Returns
    =======
    tempfilt : nipype.Workflow object
        the temporal filter workflow object

    """

    tempfilt = Workflow(name=name)
    inputspec = Node(utility.IdentityInterface(fields=['in_files']),
                     name='inputspec')

    # Calculate sigmas
    def calculate_sigmas(in_file, cutoffs):
        import subprocess
        output = subprocess.check_output(
            ['fslinfo', in_file]).decode().split("\n")
        for out in output:
            if out.startswith("pixdim4"):
                if cutoffs[0] is None:
                    hisigma = '-1'
                else:
                    hisigma = cutoffs[0] / (2 * float(out.lstrip("pixdim4")))
                    hisigma = '{:.10f}'.format(hisigma)
                if cutoffs[1] is None:
                    losigma = '-1'
                else:
                    losigma = cutoffs[1] / (2 * float(out.lstrip("pixdim4")))
                    losigma = '{:.10f}'.format(losigma)
                return '-bptf {0} {1}'.format(hisigma, losigma)

    getsigmas = MapNode(utility.Function(function=calculate_sigmas,
                                         input_names=['in_file', 'cutoffs'],
                                         output_names=['op_string']),
                        iterfield=['in_file'],
                        name='getsigmas')
    getsigmas.inputs.cutoffs = cutoffs

    # Save mean
    meanfunc = MapNode(fsl.ImageMaths(op_string='-Tmean', suffix='_mean',
                                      out_data_type='int'),
                       iterfield=["in_file"],
                       name='meanfunc')

    # Filter data
    filter_ = MapNode(fsl.ImageMaths(suffix='_tempfilt', out_data_type='int'),
                      iterfield=["in_file", "op_string"], name='filter')

    # Restore mean
    addmean = MapNode(fsl.BinaryMaths(operation='add', output_datatype='int'),
                      iterfield=["in_file", "operand_file"], name='addmean')

    outputspec = Node(utility.IdentityInterface(fields=['filtered_files']),
                      name='outputspec')

    tempfilt.connect(inputspec, 'in_files', filter_, 'in_file')
    tempfilt.connect(inputspec, 'in_files', getsigmas, 'in_file')
    tempfilt.connect(getsigmas, 'op_string', filter_, 'op_string')
    tempfilt.connect(inputspec, 'in_files', meanfunc, 'in_file')
    tempfilt.connect(filter_, 'out_file', addmean, 'in_file')
    tempfilt.connect(meanfunc, 'out_file', addmean, 'operand_file')
    tempfilt.connect(addmean, 'out_file', outputspec, 'filtered_files')

    return tempfilt

def get_boldfile_template(fmriprep_dir, subject):
    """Return boldfile template string for given directory and subject.

    Paramters
    =========
    bids_dir : str
        the path to the fMRIprep directory
    subject : str or int
        the subject identifier

    Returns
    =======
    template : str
        the boldfile template string

    """

    import os

    if type(subject) == int:
        subject = "sub-{0:03d}".format(subject)
    return os.path.join(fmriprep_dir, subject, "ses-*", "func",
                        "*_desc-preproc_bold.nii.gz")

def get_masks(bold_files):
    """Get mask files for given bold files.

    Parameters
    ==========
    bold_files = list
        the list of bold files

    Returns
    =======
    mask_files : list
        the list of mask files

    """

    import os
    import re

    masks = [x.replace("preproc_bold", "brain_mask") for x in bold_files]
    return  [re.sub("echo-[0-9]_", "", x) if not os.path.isfile(x) \
             else x for x in masks]  # new since fmriprep 21.0.0

def get_output_filename(bold_filename, suffix):
    """Get output filename for given bold filename and suffix.

    Parameters
    ==========
    bold_filename : str
        the bold filename
    suffix : str
        the `desc` suffix

    Returns
    =======
    output_filename = str
        the output filename

    """

    import os

    path, filename = os.path.split(bold_filename)
    split_name = filename.split("_")
    d = {x.split("-")[0]: x.split("-")[1] for x in split_name[:-1]}
    extension = split_name[-1]
    d["desc"] += suffix
    new = "_".join([f"{x}-{y}" for x,y in d.items()]) + "_" + extension
    return os.path.join(path, new)

def create_preprocessing_workflow(pipeline, name="preprocessing"):
    """Create a preprocessing workflow.

    Parameters
    ==========
    pipeline : dict
        the preprocessing pipeline (ordered!); possible options are:
            "spatial_smoothing": numeric (FWHM Gaussian kernel in millimeters)
            "temporal_filtering": list (high and low cutoff values in seconds)
            "timecourse_normalization": str (method; one of "Zscore" or "PSC")
    name : str, optional
        the name of the workflow (default="preprocessing")

    Returns
    =======
    preprocessing : nipype.Workflow object
        the preprocessing workflow

    """

    preprocessing = Workflow(name=name)

    inputspec = Node(utility.IdentityInterface(fields=['in_files']),
                     name='inputspec')

    state = {"last": inputspec, "last_output": "in_files", "suffix": ""}

    # Run each step in pipeline
    for step,spec in pipeline.items():
        if step == "spatial_smoothing":
            smooth = create_susan_smooth(name="spatial_smoothing")
            smooth.inputs.inputnode.fwhm = spec
            preprocessing.connect(state["last"], state["last_output"],
                                  smooth, "inputnode.in_files")
            preprocessing.connect(inputspec, ("in_files", get_masks),
                                  smooth, "inputnode.mask_file")
            state["last"] = smooth
            state["last_output"] = "outputnode.smoothed_files"
            state["suffix"] += "{0}mm".format(spec)
        if step == "temporal_filtering":
            tempfilt = create_temporal_filter(spec, name="temporal_filtering")
            preprocessing.connect(state["last"], state["last_output"],
                                  tempfilt, "inputspec.in_files")
            state["last"] = tempfilt
            state["last_output"] = "outputspec.filtered_files"
            state["suffix"] += "".join(
                    [str(x) if x is None else "{0}s".format(x) for x in spec])
        if step == "timecourse_normalization":
            normalize = create_timecourse_normalization_workflow(
                name="timecourse_normalization")
            preprocessing.connect(state["last"], state["last_output"],
                                  normalize, "inputspec.in_files")
            preprocessing.connect(inputspec, ("in_files", get_masks),
                                  normalize, "inputspec.mask_files")
            state["last"] = normalize
            state["last_output"] = "outputspec.normalized_files"
            state["suffix"] += "{0}".format(spec)

    outputspec = Node(utility.IdentityInterface(fields=["preprocessed_files",
                                                        "suffix"]),
                      name='outputspec')
    outputspec.inputs.suffix = state["suffix"]
    preprocessing.connect(state["last"], state["last_output"],
                outputspec, "preprocessed_files")

    return preprocessing

def str2list(x):
    if type(x) is str:
        return [x]
    else:
        return x

def finish_the_job(fmriprep_dir, subjects, pipeline, work_dir=None):
    """Run common preprocessing steps after fMRIprep.

    Parameters
    ==========
    fmriprep_dir : str
        the root directory of the fMRIprep data
    subjects : list
        the subjects to preprocess
    pipeline : dict
        the preprocessing pipeline (ordered!); possible options are:
            "spatial_smoothing": numeric (FWHM Gaussian kernel in millimeters)
            "temporal_filtering": list (high and cutoff values in seconds)
            "timecourse_normalization": str (method; one of "Zscore" or "PSC")
    work_dir : str, optional
        the working directory (default=None)

    Examples
    ========
    >>> from finish_the_job import finish_the_job
    >>> finish_the_job(fmriprep_dir="/path/to/fmriprep_dir/"
    ...                subjects=[1,2,3],
    ...                pipeline = {"spatial_smoothing": 5,
    ...                            "temporal_filtering": [100, None],
                                   "timecourse_normalization": "Zscore"})


    """

    if type(subjects) not in (list, tuple):
        subjects = (subjects)

    ftj = Workflow(name="finish_the_job")
    if work_dir is not None:
        ftj.base_dir = work_dir  # set working/output directory

    # Get boldfile template
    boldfile_template = Node(utility.Function(input_names=["fmriprep_dir",
                                                           "subject"],
                                              output_names=["template"],
                                              function=get_boldfile_template),
                    name='locate_bold_files')
    boldfile_template.inputs.fmriprep_dir = fmriprep_dir
    boldfile_template.iterables = ("subject", subjects)


    # Get inputs
    dg = Node(io.DataGrabber(), name="get_data")
    dg.inputs.sort_filelist = True
    ftj.connect(boldfile_template, "template", dg, "template")

    # Ensure inputs are list
    ensure_list = Node(utility.Function(input_names=["in_files"],
                                        output_names=["out_files"],
                                        function=str2list),
                    name='ensure_data_is_list')
    ftj.connect(dg, "outfiles", ensure_list, "in_files")

    # Preprocess files
    preprocessing = create_preprocessing_workflow(pipeline=pipeline)
    ftj.connect(ensure_list, "out_files", preprocessing, "inputspec.in_files")

    # Get output filenames
    filenames = MapNode(utility.Function(input_names=["bold_filename",
                                                      "suffix"],
                                         output_names=["output_filename"],
                                         function=get_output_filename),
                        iterfield=["bold_filename"],
                    name='create_output_filenames')
    ftj.connect(preprocessing, "outputspec.suffix", filenames, "suffix")
    ftj.connect(ensure_list, "out_files", filenames, "bold_filename")

    # Save preprocessed files
    ef = MapNode(io.ExportFile(), iterfield=["in_file", "out_file"],
                 name="save_data")
    ftj.connect(preprocessing, "outputspec.preprocessed_files", ef, "in_file")
    ftj.connect(filenames, "output_filename", ef, "out_file")

    # Run workflow
    if work_dir:
        ftj.write_graph(graph2use="colored",
                       dotfilename="graph_colored.dot")
    ftj.run()

