# Finish the job
Nipype pipeline for common preprocessing steps after fMRIprep

## Introduction
fMRIprep stops preprocessing after normalization. Often you also need your data to be spatially smoothed and/or temporally highpass-filtered. Finish the job is a convenient way to do this by simply specifying the directory of the preprocessed data from fMRIprep, a list of subjects to run it on, and a pipeline that specifies the details of the additional preprocessing steps to run, as well as their order. All `bold` images of the specified subjects found in the fMRIprep directory will be processed.

Example pipeline `{"spatial_smoothing": 5, "highpass_filtering": 100}`:

<a href="https://github.com/can-lab/finish-the-job/blob/master/graph_colored.png">
  <img src="https://github.com/can-lab/finish-the-job/raw/master/graph_colored.png" width="300">
</a>

Preprocessed images are saved next to the input images, with the `desc` field updated to reflect the preprocessing details (`preproc5mm100s` in the above example).

## Prerequisites
1. Install [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/)
2. Install [graphviz](https://www.graphviz.org/)
3. Install nipype, niflow-manager and niflow-nipype1-workflows with
   ```
   pip3 install nipype niflow-manager niflow-nipype1-workflows
   ```
4. Download [Finish the job](https://github.com/can-lab/finish-the-job/releases/latest)
5. Install wth
   ```
   pip3 install finish-the-job-X.X.X.zip
   ```
   (replace X.X.X with latest release version)

### Donders cluster
If you are working on the compute cluster of the Donders Institute, please follow the following steps:
1. Load fMRIprep module by running command: `module load fmriprep`
2. Install virtualenv by running command: `pip3 install virtualenv --user`
3. Create new environment in home directory by running command: `cd && python3 -m virtualenv ftj_env`
4. Activate new environment by running command: `source ~/ftj_env/bin/activate`
5. Update pip in environment by running command: `pip3 install -U pip`
6. Install Nipype, Nifow-manager into environment by running command: `pip3 install nipype niflow-manager niflow-nipype1-workflows`
4. Download [Finish the job](https://github.com/can-lab/finish-the-job/releases/latest)
5. Install with
   ```
   pip3 install finish-the-job-X.X.X.zip
   ```
   (replace X.X.X with latest release version)

## Usage
```python
from finish_the_job import finish_the_job

finish_the_job(fmriprep_dir="/path/to/fmriprep_dir/"
               subjects=[1,2,3],
               pipeline = {"spatial_smoothing": 5,
                           "highpass_filtering": 100,
                           "timecourse_normalization": "Z"})
```

### Donders cluster
If you are working on the compute cluster of the Donders Institute, please follow the following steps:
1. Start a new interactive job by running command: `qsub -I -l 'procs=8, mem=64gb, walltime=24:00:00'`
2. Load fMRIprep module by running command: `module load fmriprep`
3. Load graphviz module by running command: `module load graphviz`
4. Activate environment by running command: `source ~/ftj_env/bin/activate`
5. Write script `mystudy_ftj.py` with custom workflow:
   ```python
   from finish_the_job import finish_the_job

   finish_the_job(fmriprep_dir="/path/to/fmriprep_dir/"
                  subjects=[1,2,3],
                  pipeline = {"spatial_smoothing": 5,
                              "highpass_filtering": 100,
                              "timecourse_normalization": "Z"})
   ```
6. Run script by running command: `python3 mystudy_ftj.py`
