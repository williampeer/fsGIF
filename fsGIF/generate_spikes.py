import os.path
import numpy as np

import theano_shim as shim
from sinn.histories import Series, Spiketrain
import sinn.iotools as iotools

import core
from core import logger
############################
# Model import
import fsgif_model as gif
############################

"""
Expected parameters format:
{ 'input': {input_params},
  'model': {model_params},
  ['t0', 'tn', 'dt']
}
"""

def generate_spikes(mgr):
    # Temporarily unload Theano since it isn't supported by spike history
    use_theano = shim.config.use_theano
    shim.load(load_theano=False)

    params = mgr.params
    seed = params.seed
    rndstream = core.get_random_stream(seed)

    logger.info("Generating new spike data...")
    #Ihist = Series.from_raw(iotools.loadraw(mgr.get_pathname(params.input)))
    Ihist = mgr.load(mgr.get_pathname(params.input,
                                      subdir=mgr.subdirs['input'],
                                      label=''),
                     calc='input',
                     cls=Series.from_raw,
                     recalculate=False)

    # Create the spiking model
    # We check if different run parameters were specified,
    # otherwise those from Ihist will be taken
    runparams = { name: params[name] for name in params.keys()
                   if name in ['t0', 'tn', 'dt'] }
    # TODO: if dt different from Ihist, subsample Ihist
    shist = Spiketrain(Ihist, name='s', pop_sizes = params.model.N, iterative=True,
                       **runparams)
    model_params = core.get_model_params(params.model)
        # Needed for now because fsgif_model does not yet use ParameterSet
    spiking_model = gif.GIF_spiking(model_params, shist, Ihist,
                                    params.initializer, rndstream)
    w = gif.GIF_spiking.expand_param(np.array(model_params.w), model_params.N) * model_params.Γ
        # w includes both w and Γ from Eq. 20
    shist.set_connectivity(w)

    # Generate the spikes
    shist.set()

    logger.info("Done.")

    # Reload Theano if it was loaded when we entered the function
    shim.load(load_theano=use_theano)

    return spiking_model

if __name__ == "__main__":
    core.init_logging_handlers()
    mgr = core.RunMgr(description="Generate spikes", calc='spikes')
    mgr.load_parameters()
    spike_filename = mgr.get_pathname(label='')
    spike_activity_filename = mgr.get_pathname(label='', suffix='activity')

    generate_data = False
    try:
        # Try to load data to see if it's already been calculated
        shist = mgr.load(spike_filename, cls=Spiketrain.from_raw)
    except core.FileNotFound:
        generate_data = True
    except core.FileRenamed:
        # The --recalculate flag was passed and the original data file renamed
        # Do the same with the associated activity file
        generate_data = True
        activity_path = mgr.find_path(spike_activity_filename)
        if activity_path is not None:
            mgr.rename_to_free_file(activity_path)
                # Warning: If there are missing activity traces, the rename could
                #   suffix the spikes and activity with a different number, as in
                #   both cases the first free suffix is used
                # Warning #2: If the data filename is free, but not the filename
                #   of the derived data (e.g. because only the first was renamed),
                #   the derived data is NOT renamed
    if generate_data:
        # Get new filenames with the run label
        spike_filename = mgr.get_pathname(label=None)
        spike_activity_filename = mgr.get_pathname(suffix='activity', label=None)

        # Generate spikes
        shist = generate_spikes(mgr).s

        # Save to file
        iotools.saveraw(spike_filename, shist)

        # Compute the associated activity trace
        logger.info("Computing activity from spike data")
        Ahist = core.compute_spike_activity(shist)
        iotools.saveraw(spike_activity_filename, Ahist)

