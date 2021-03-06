import os.path
import numpy as np
from tqdm import tqdm

import theano_shim as shim
from sinn.histories import Series, Spiketrain
import sinn.iotools as iotools

from fsGIF import core
logger = core.logger
############################
# Model import
from fsGIF import fsgif_model as gif
#data_dir = "data"
#label_dir = "run_dump"
############################

def get_model(params, Ihist=None):
    # TODO: Use core.get_meso_model

    seed = params.seed
    rndstream = core.get_random_stream(seed)

    if Ihist is None:
        input_filename = core.add_extension(
            core.get_pathname(data_dir=core.data_dir,
                              params=params.input.params,
                              subdir=params.input.dir,
                              suffix=params.input.name,
                              label_dir=core.label_dir,
                              label=''))
        Ihist = iotools.load(input_filename)
        if isinstance(Ihist, np.lib.npyio.NpzFile):
            # Support older data files
            Ihist = Series.from_repr_np(Ihist)

    Ihist_subsampled = core.subsample(Ihist, params.dt,
                                      max_len = int(params.tn / params.dt))

    # Create the activity model
    # We check if different run parameters were specified,
    # otherwise those from Ihist will be taken
    runparams = { name: params[name] for name in params
                  if name in ['t0', 'tn', 'dt'] }

    model_params = core.get_model_params(params.model, 'GIF_mean_field')
        # Needed for now because fsgif_model does not yet use ParameterSet

    Ahist = Series(Ihist_subsampled, name='A', shape=(len(model_params.N),), iterative=True,
                   **runparams)

    # GIF activity model
    mfmodel = gif.GIF_mean_field(model_params, Ahist, Ihist_subsampled,
                                 params.initializer, rndstream)

    return mfmodel

def add_suffix(filename, suffix, sep='_'):
    """Add a suffix before the file extension."""
    base, ext = os.path.splitext(filename)
    if sep != '' and base[-1] != sep and suffix[0] != sep:
        base += sep
    return base + suffix + ext

if __name__ == "__main__":
    core.init_logging_handlers()
    mgr = core.RunMgr(description="Generate activity", calc='activity')
    mgr.load_parameters()
    activity_filename = mgr.get_pathname(label='')

    try:
        mgr.load(activity_filename, cls=Series.from_raw)
    except (core.FileNotFound, core.FileRenamed):
        # Get pathname with run label
        if mgr.args.debug:
            activity_filename = "activity_debug.npr"
            #expected_activity_filename = "activity_debug_nbar.npr"
        else:
            activity_filename = core.add_extension(mgr.get_pathname(label=None))
            #expected_activity_filename = core.add_extension(mgr.get_pathname(label=None, suffix='nbar'))
        # Create mean-field model and generate activity
        mfmodel = get_model(mgr.params)

        # Generate the activity trace
        # We could just call mfmodel.advance('end'), but doing it sequentially allows the progress bar
        # And since we know that variables have to be computed iteratively anyway, there's not much
        # cost to doing this.
        logger.info("Generating new activity data...")
        for i in tqdm(range(mfmodel.t0idx, mfmodel.tnidx),
                      position=mgr.args.threadidx):
            mfmodel.advance(i)

        # Save to file
        iotools.save(activity_filename, mfmodel.A, format='npr')
        iotools.save(add_suffix(activity_filename, 'nbar'), mfmodel.nbar, format='npr')
        iotools.save(add_suffix(activity_filename, 'u'), mfmodel.u, format='npr')
        iotools.save(add_suffix(activity_filename, 'vartheta'), mfmodel.varθ, format='npr')
