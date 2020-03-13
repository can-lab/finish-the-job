"""Finish the job.

Nipype pipeline for common preprocessing steps after fMRIprep:

- Spatial smoothing
- Highpass filtering

Dependencies:

- nipype
- niflow-nipype1-workflows

"""

__author__ = "Florian Krause <f.krause@donders.ru.nl>"
__version__ = "0.1.0"
__date__ = "2020-03-10"


from nipype import Node, MapNode, Workflow
from nipype.interfaces import utility, fsl, io
from niflow.nipype1.workflows.fmri.fsl.preprocess import create_susan_smooth


def create_highpass_filter(cutoff=100, name='highpass'):
    """Create a highpass filter workflow.

    Parameters
    ==========
    cutoff : numeric, optional
        the cutoff value in seconds (default=100)
    name : str, optional
        the name of the workflow (default="highpass")

    Returns
    =======
    highpass : nipype.Workflow object
        the higpahs_filter object

    """

    highpass = Workflow(name=name)
    inputspec = Node(utility.IdentityInterface(fields=['in_files']),
                     name='inputspec')

    # Calculate sigma
    def calculate_sigma(in_file, cutoff):
        import subprocess
        output = subprocess.check_output(
            ['fslinfo', in_file]).decode().split("\n")
        for out in output:
            if out.startswith("pixdim4"):
                sigma = cutoff / (2 * float(out.lstrip("pixdim4")))
                return '-bptf %.10f -1' % sigma

    getsigma = MapNode(utility.Function(function=calculate_sigma,
                                        input_names=['in_file', 'cutoff'],
                                        output_names=['op_string']),
                       iterfield=['in_file'],
                       name='getsigma')
    getsigma.inputs.cutoff = cutoff

    # Save mean
    meanfunc = MapNode(fsl.ImageMaths(op_string='-Tmean', suffix='_mean',
                                      out_data_type='int'),
                       iterfield=["in_file"],
                       name='meanfunc')

    # Filter data
    filter_ = MapNode(fsl.ImageMaths(suffix='_tempfilt', out_data_type='int')
                      iterfield=["in_file", "op_string"], name='filter')

    # Restore mean
    addmean = MapNode(fsl.BinaryMaths(operation='add', output_datatype='int'),
                      iterfield=["in_file", "operand_file"], name='addmean')

    outputspec = Node(utility.IdentityInterface(fields=['filtered_files']),
                      name='outputspec')

    highpass.connect(inputspec, 'in_files', filter_, 'in_file')
    highpass.connect(inputspec, 'in_files', getsigma, 'in_file')
    highpass.connect(getsigma, 'op_string', filter_, 'op_string')
    highpass.connect(inputspec, 'in_files', meanfunc, 'in_file')
    highpass.connect(filter_, 'out_file', addmean, 'in_file')
    highpass.connect(meanfunc, 'out_file', addmean, 'operand_file')
    highpass.connect(addmean, 'out_file', outputspec, 'filtered_files')

    return highpass

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
                        "*_bold.nii.gz")

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

    return [x.replace("preproc_bold", "brain_mask") for x in bold_files]

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
            "highpass_filtering": numeric (cutoff value in seconds)
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
    for step,argument in pipeline.items():
        if step == "spatial_smoothing":
            smooth = create_susan_smooth()
            smooth.inputs.inputnode.fwhm = argument
            preprocessing.connect(state["last"], state["last_output"],
                                smooth, "inputnode.in_files")
            preprocessing.connect(state["last"], (state["last_output"],
                                                  get_masks),
                                smooth, "inputnode.mask_file")
            state["last"] = smooth
            state["last_output"] = "outputnode.smoothed_files"
            state["suffix"] += "{0}mm".format(argument)
        if step == "highpass_filtering":
            highpass = create_highpass_filter(argument)
            preprocessing.connect(state["last"], state["last_output"],
                                highpass, "inputspec.in_files")
            state["last"] = highpass
            state["last_output"] = "outputspec.filtered_files"
            state["suffix"] += "{0}s".format(argument)
        if step == "timecourse_normalization":
            # TODO
            pass

    outputspec = Node(utility.IdentityInterface(fields=["preprocessed_files",
                                                        "suffix"]),
                      name='outputspec')
    outputspec.inputs.suffix = state["suffix"]
    preprocessing.connect(state["last"], state["last_output"],
                outputspec, "preprocessed_files")

    return preprocessing

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
            "highpass_filtering": numeric (cutoff value in seconds)
    work_dir : str, optional
        the working directory (default=None)

    Examples
    ========
    >>> from finish_the_job import finish_the_job
    >>> finish_the_job(fmriprep_dir="/path/to/fmriprep_dir/"
    ...                subjects=[1,2,3],
    ...                pipeline = {"spatial_smoothing": 5,
    ...                            "highpass_filtering": 100})


    """

    if type(subjects) not in (list, tuple):
        subjects = (subjects)

    ftj = Workflow(name="finish_the_job")
    if work_dir is not None:
        ftj.base_dir = work_dir  # set working/output directory

    # Input node
    inputspec = Node(utility.IdentityInterface(fields=['fmriprep_dir',
                                                       'subject']),
                     name='inputspec')
    inputspec.fmriprep_dir = fmriprep_dir
    inputspec.iterables = ("subject", subjects)

    # Get boldfile template
    boldfile_template = Node(utility.Function(input_names=["fmriprep_dir",
                                                           "subject"],
                                              output_names=["template"],
                                              function=get_boldfile_template),
                    name='template')
    boldfile_template.inputs.fmriprep_dir = fmriprep_dir
    boldfile_template.iterables = ("subject", subjects)

    # Get inputs
    dg = Node(io.DataGrabber(), name="data_grabber")
    dg.inputs.sort_filelist = True
    ftj.connect(boldfile_template, "template", dg, "template")

    # Preprocess , suffix files
    preprocessing = create_preprocessing_workflow(pipeline=pipeline)
    ftj.connect(dg, "outfiles", preprocessing, "inputspec.in_files")

    # Get output filenames
    filenames = MapNode(utility.Function(input_names=["bold_filename",
                                                      "suffix"],
                                         output_names=["output_filename"],
                                         function=get_output_filename),
                        iterfield=["bold_filename"],
                    name='filename')
    ftj.connect(preprocessing, "outputspec.suffix", filenames, "suffix")
    ftj.connect(dg, "outfiles", filenames, "bold_filename")

    # Save preprocessed files
    ef = MapNode(io.ExportFile(), iterfield=["in_file", "out_file"],
                 name="export_file")
    ftj.connect(preprocessing, "outputspec.preprocessed_files", ef, "in_file")
    ftj.connect(filenames, "output_filename", ef, "out_file")

    # Run workflow
    if work_dir:
        ftj.write_graph(graph2use="colored",
                       dotfilename="graph_colored.dot")
    ftj.run()
