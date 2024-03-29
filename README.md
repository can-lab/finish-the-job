# Finish the job
Running common preprocessing steps after fMRIprep

by [Florian Krause](https://www.floriankrause.org) & [Martin Krentz](mailto:m.krentz@donders.ru.nl)

## Introduction
fMRIprep stops preprocessing after normalization. Often you also need your data to be spatially smoothed and/or temporally highpass-filtered. Finish the job is a convenient way to do this by simply specifying the directory of the preprocessed data from fMRIprep, a list of subjects to run it on, and a pipeline that specifies the details of the additional preprocessing steps to run, as well as their order. All `bold` images of the specified subjects found in the fMRIprep directory will be processed.

Currently available preprocessing steps:
* **"spatial_smoothing"**
  * _spec_: FWHM kernel size in millimeter (numeric)
* **"temporal_filtering"**
  * _spec_: highpass and lowpass filter sizes in seconds (list)
* **"timecourse_normalization"** (**Note:** also performs brain extraction!)
  * _spec_: normalization methods ("Zscore" or "PSC")

Pipelines are simply dictionaries with preprocessing steps as keys and their specs as values.

Example pipeline `{"spatial_smoothing": 5, "temporal_filtering": [100, None], "timecourse_normalization": "Zscore"}`:

<a href="https://github.com/can-lab/finish-the-job/blob/master/graph_colored.png">
  <img src="https://github.com/can-lab/finish-the-job/raw/master/graph_colored.png" width="300">
</a>

Preprocessed images are saved next to the input images, with the `desc` field updated to reflect the preprocessing details (`preproc5mm100sNoneZscore` in the above example).

## Prerequisites
1. Install [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/)
2. Install [graphviz](https://www.graphviz.org/)
3. Install nipype, niflow-manager and niflow-nipype1-workflows with
   ```
   pip3 install nipype niflow-manager niflow-nipype1-workflows
   ```
4. Download [Finish the job](https://github.com/can-lab/finish-the-job/archive/master.zip)
5. Install with
   ```
   pip3 install finish-the-job-X.X.X.zip
   ```
   (replace X.X.X with latest release version)

### Donders cluster
If you are working on the compute cluster of the Donders Institute, please follow the following steps:
1. Load Anaconda3 module by running command: `module load anaconda3`
2. Create new environment in home directory by running command: `cd && python3 -m venv ftj_env`
4. Activate new environment by running command: `source ftj_env/bin/activate`
5. Install Nipype, Nifow-manager into environment by running command: `pip3 install nipype niflow-manager niflow-nipype1-workflows`
6. Download [Finish the job](https://github.com/can-lab/finish-the-job/archive/master.zip)
7. Install with
   ```
   pip3 install finish-the-job-X.X.X.zip
   ```
   (replace X.X.X with latest release version)

## Usage
Example:
```python
from finish_the_job import finish_the_job

finish_the_job(fmriprep_dir="/path/to/fmriprep_dir/",
               subjects=[1,2,3],
               pipeline = {"spatial_smoothing": 5,  # Step 1: spatial smoothing with 5 mm kernel
                           "temporal_filtering": [100, None],  # Step 2: highpass filtering with 100 s filter size
                           "timecourse_normalization": "Z", # Step 3: Z-normalization of voxels timecourses
                           })
```

### Donders cluster
If you are working on the compute cluster of the Donders Institute, please follow the following steps:
1. Start a new interactive job by running command: `qsub -I -l 'procs=8, mem=64gb, walltime=24:00:00'`
2. Load Anaconda3 module by running command: `module load anaconda3`
3. Load graphviz module by running command: `module load graphviz`
4. Activate environment by running command: `source ftj_env/bin/activate`
5. Write script `mystudy_ftj.py` with custom workflow; example:
   ```python
   from finish_the_job import finish_the_job

   finish_the_job(fmriprep_dir="/path/to/fmriprep_dir/",
                  subjects=[1,2,3],
                  pipeline = {"spatial_smoothing": 5,  # Step 1: spatial smoothing with 5 mm kernel
                              "temporal_filtering": [100, None],  # Step 2: highpass filtering with 100 s filter size
                              "timecourse_normalization": "Zscore", # Step 3: Z-normalization of voxels timecourses
                              })
   ```
6. Run script by running command: `python3 mystudy_ftj.py`
