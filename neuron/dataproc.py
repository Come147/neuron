''' data processing for neuron project '''

# built-in
import sys
import os
import six

# third party
import nibabel as nib
import numpy as np
import scipy.ndimage.interpolation
from tqdm import tqdm # for verbosity for forloops

# import local ndutils
import pynd.ndutils as nd

# from imp import reload # for re-loading modules, since some of the modules are still in development
# reload(nd)


def proc_mgh_vols(inpath, outpath, ext='.mgz',
                  resize_shape=None, interp_order=2, rescale=None, crop=None, offset=None, clip=None):
    ''' process mgh data from mgz format and save to numpy format

        1. load file
        2. normalize intensity
        3. resize
        4. save as python block

        TODO: check header info and such.?
        '''

    # get files in input directory
    files = [f for f in os.listdir(inpath) if f.endswith(ext)]

    # go through each file
    for fileidx in tqdm(range(len(files)), ncols=80):

        # load nifti volume
        volnii = nib.load(os.path.join(inpath, files[fileidx]))

        # get the data out
        vol_data = volnii.get_data().astype(float)

        # process volume
        try:
            vol_data = vol_proc(vol_data, crop=crop, resize_shape=resize_shape,
                            interp_order=interp_order, rescale=rescale, offset=offset, clip=clip)
        except Exception as e:
            print("Skipping %s\nError: %s" % (files[fileidx], str(e)), file=sys.stderr)
            continue

        # save numpy file
        outname = os.path.splitext(os.path.join(outpath, files[fileidx]))[0] + '.npz'
        np.savez_compressed(outname, vol_data=vol_data)



def vol_proc(vol_data,
             crop=None,
             resize_shape=None, # None (to not resize), or vector. If vector, third entry can be None
             interp_order=None,
             rescale=None,
             offset=None,
             clip=None):
    ''' process a volume with a series of intensity rescale, resize and crop rescale'''

    if offset is not None:
        vol_data = vol_data + offset

    # intensity normalize data .* rescale
    if rescale is not None:
        vol_data = np.multiply(vol_data, rescale)

    if clip is not None:
        vol_data = np.clip(vol_data, clip[0], clip[1])

    # resize (downsample) matrices
    if resize_shape is not None and resize_shape != vol_data.shape:
        # allow for the last entry to be None
        if resize_shape[-1] is None:
            resize_ratio = np.divide(resize_shape[0], vol_data.shape[0])
            resize_shape[-1] = np.round(resize_ratio * vol_data.shape[-1]).astype('int')

        resize_ratio = np.divide(resize_shape, vol_data.shape)
        vol_data = scipy.ndimage.interpolation.zoom(vol_data, resize_ratio, order=interp_order)

    # crop data if necessary
    if crop is not None:
        vol_data = nd.volcrop(vol_data, crop=crop)

    return vol_data


def prior_to_weights(prior_filename, nargout=1):
    ''' transform a 4D prior (3D + nb_labels) into a class weight vector '''

    # load prior
    if isinstance(prior_filename, six.string_types):
        prior = np.load(prior_filename)['prior']

    # assumes prior is 4D.
    assert np.ndim(prior) == 4, "prior is the wrong number of dimensions"
    prior = np.reshape(prior, (np.prod(prior.shape[0:3]), prior.shape[-1]))

    # sum total class votes
    class_count = np.sum(prior, 0)
    prior = class_count / np.sum(class_count)

    # compute weights from class frequencies
    weights = 1/prior
    weights = weights / np.sum(weights)
    # weights[0] = 0 # explicitly don't care about bg

    if nargout == 1:
        return weights
    else:
        return (weights, prior)