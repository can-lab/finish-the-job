from setuptools import setup

def get_version():
    """Get version and version_info from finish_the_job/__meta__.py file."""

    import os
    module_path = os.path.join(os.path.dirname('__file__'), 'finish_the_job',
                               '__meta__.py')

    import importlib.util
    spec = importlib.util.spec_from_file_location('__meta__', module_path)
    meta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(meta)
    return meta.__version__

__version__ = get_version()

setup(
    name = 'Finish the job',
    version = __version__,
    packages = ['finish_the_job'],
    install_requires = ['nipype',
                        'niflow-nipype1-workflows',
                        'nilearn',
                        'nibabel'])
