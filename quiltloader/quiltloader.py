import tifffile as tfle
import pandas as pd
import numpy as np
import importlib
import codecs
import quilt
import types
import json

import matplotlib.pyplot as plt
from IPython import get_ipython
try:
    get_ipython().run_line_magic('matplotlib', 'inline')
except AttributeError:
    pass

def _normalize_im(img):
    """
    Parameters
    ----------
    img: np.ndarray
        The ndarray that should have all values normalized
    Output
    ----------
    This is a normalize image function, the output of this normalization is in standard 0 - 255 value range.
    """
    im_min = np.min(img)
    im_max = np.max(img)

    img -= im_min
    img = img / (im_max - im_min)

    img[img<0] = 0
    img[img>1] = 1

    img *= 255

    return img

def _channels_to_rgb(r, g, b):
    """
    Parameters
    ----------
    r, g, b: np.ndarray
        ndarray containing which data should be shown as each r, g, b channels of the output image.
    Output
    ----------
    Normalizes all color channels using _normalize_im, then stacks them and ensures integer for future computation.
    """

    r = _normalize_im(r)
    g = _normalize_im(g)
    b = _normalize_im(b)
    return np.stack((r,g,b), -1).astype(np.uint8)

def _custom_try_except(node, key):
    """
    Parameters
    ----------
    node: quilt.nodes.Node
        The current self node.
    key: str
        The target child node.
    Output
    ----------
    Attempts to open the target by try -> except blocks with default loaders. If all loaders fail, it getattrs the target from current as a safety.
    """

    # this is disgusting and im sorry
    try:
        return json.load(open(getattr(node, key)()))
    except:
        pass

    try:
        return tfle.TiffFile(getattr(node, key)())
    except:
        pass

    return getattr(node, key)()

def _join_dicts(additions, defaults):
    """
    Parameters
    ----------
    additions: dict
        A dictionary of custom dictionary additions.
    defaults: dict
        Default set of items all custom dictionaries of this type must have.
    Output
    ----------
    Uses the defaults object to determine if any default items are missing from the additions provided and applies the default items to those that are.
    """

    # ensure loaders exist for each type of obj
    for required, item in defaults.items():
        if required not in additions.keys():
            additions[required] = item

    # return completed loader dict
    return additions

def _find_nodes(head, label, nodes):
    # find and return a list of found quilt nodes
    found = list()
    for node in nodes:
        try:
            found.append(head[label][node])
        except AttributeError:
            pass

    return found

def _get_associates(self):
    meta = self['info']
    associates = dict()
    known_associates = ['plates', 'wells', 'lines', 'fovs', 'cell_segs', 'nuclei_segs', 'structure_segs']

    for known in known_associates:
        try:
            associates[known] = _find_nodes(self.pkg_head,
                                            known,
                                            meta[known])
        except KeyError:
            pass

    return associates

def _get_items(self):
    # get all node keys
    keys = list(self.__dict__.keys())
    iter_k = list(keys)
    # remove any keys that begin with '_'
    for remove_key in iter_k:
        if remove_key.startswith('_'):
            keys.remove(remove_key)

    items = dict()
    for key in keys:
        items[key] = self.__dict__[key]

    return items.items()

def _get_dataframe(self):
    if not isinstance(self, quilt.nodes.GroupNode):
        raise TypeError('"get_dataframe" is required to be called on a base level GroupNode')

    if 'info' in self.__dict__:
        raise TypeError('"get_dataframe" is required to be called on a base level GroupNode')

    objs = list()
    for node_name, node_objects in self.items():
        to_add = dict(node_objects['info'])

        to_add['node'] = node_name
        remove_keys = ['edits', 'channels', 'plates', 'lines', 'wells', 'fovs', 'cell_segs', 'nuclei_segs', 'structure_segs']
        for key in remove_keys:
            try:
                del to_add[key]
            except KeyError:
                pass

        for key, item in to_add.items():
            if isinstance(item, list):
                to_add[key] = str(item)
            # elif isinstance(item, dict):
            #     to_add[key] = json.dumps(item)

        objs.append(to_add)

    return pd.DataFrame(objs)

def check_node_for_image(self, img):
    if not isinstance(self, quilt.nodes.GroupNode):
        raise TypeError('"display_segs" requires a node with at least one of each associated "cell_segs", "nuclei_segs", and "structure_segs" as the "node" parameter')

    if '_mem_img' in self.__dict__:
        img = self._mem_img
    elif img is None:
        associates = self.get_associates()
        if 'fovs' not in associates:
            img = self['image']
        else:
            img = associates['fovs'][0]['image']
    # check if TiffFile and convert if necessary
    if isinstance(img, tfle.tifffile.TiffFile):
        img = img.asarray()

    setattr(self, '_mem_img', img)

    # if the image object is not in ndarray form now, it was not a valid arg
    if not isinstance(img, np.ndarray):
        print('display_channels(img) requires img to be either type TiffFile or ndarray.')
        raise TypeError

    return img

def display_channels(self, img=None, use_channels=[1, 3, 5, 6]):
    """
    Parameters
    ----------
    img: TiffFile/ ndarray
        Either TiffFile or ndarray to display.
        Standard AICS image: [t, z, channel, y, x]
    use_channels: list
        List containing the indices of which channels to use for display.
        Default: [1, 3, 5, 6]
    Output
    ----------
    If given TiffFile object, will first retrieve the image data by using TiffFile.asarray(). Uses matplotlib to display the specified channels at the max of the z-stack.
    """

    img = check_node_for_image(self, img)

    # initialize plots
    fig, axes = plt.subplots(1, len(use_channels), figsize=(15, 10))
    axes = axes.flatten()

    dims = len(img.shape)
    if dims == 5:
        img = np.max(img, 0)
    if dims not in [4, 5]:
        print('image data is not in a standard aics image format.')
        raise TypeError

    if img.shape[1] != 7:
        use_channels = [0, 1, 2, 3]

    # for each channel plot max of stack
    for i, ax in enumerate(axes):
        z_stack = img[:,use_channels[i],:,:]
        max_project = np.max(z_stack, 0)
        ax.imshow(max_project)
        ax.set(xticks=[], yticks=[])
        ax.set_title('channel: ' + str(use_channels[i]))

    # viewing nicety
    plt.tight_layout()

def display_rgb(self, img=None, rgb_indices=[1, 3, 5], use='max', percentile=75.0):
    """
    Parameters
    ----------
    img: TiffFile/ ndarray
        Either TiffFile or ndarray to display.
        Standard AICS image: [t, z, channel, y, x]
    channel_to_rgb_indices: list
        List containing the indices of which channels to use for display.
        Default: [1, 3, 5]
    use: string
        String determing which numpy function to use for displaying image.
        Default: 'max'
    percentile: float
        Float to be used if numpy function is specified to be 'percentile'.
    Output
    ----------
    If given TiffFile object, will first retrieve the image data by using TiffFile.asarray(). Uses matplotlib to display the specified channels at the numpy function of the z-stack as rgb channels.
    """

    img = check_node_for_image(self, img)

    # if the image object is not in ndarray form now, it was not a valid arg
    if not isinstance(img, np.ndarray):
        print('display_rgb(img) requires img to be either type TiffFile or ndarray.')
        raise TypeError

    # initialize use all variables
    if use == 'all':
        styles = ['max', 'mean', 'percentile']
        fig, axes = plt.subplots(1, len(styles), figsize=(15, 10))
        axes = axes.flatten()

        img_collection = list()

    dims = len(img.shape)
    if dims == 5:
        img = img[0,:,:,:,:]
    if dims not in [4, 5]:
        print('image data is not in a standard aics image format.')
        raise TypeError

    if img.shape[1] != 7:
        rgb_indices = [0, 1, 2]

    # get the rgb channel data using the specified numpy function
    if use == 'max' or use == 'all':
        r = np.max(img[:, rgb_indices[0], :, :], 0)
        g = np.max(img[:, rgb_indices[1], :, :], 0)
        b = np.max(img[:, rgb_indices[2], :, :], 0)

        if use == 'all':
            img_collection.append([r, g, b])
    if use == 'mean' or use == 'all':
        r = np.mean(img[:, rgb_indices[0], :, :], 0)
        g = np.mean(img[:, rgb_indices[1], :, :], 0)
        b = np.mean(img[:, rgb_indices[2], :, :], 0)

        if use == 'all':
            img_collection.append([r, g, b])
    if use =='percentile' or use == 'all':
        r = np.percentile(img[:, rgb_indices[0], :, :], percentile, 0)
        g = np.percentile(img[:, rgb_indices[1], :, :], percentile, 0)
        b = np.percentile(img[:, rgb_indices[2], :, :], percentile, 0)

        if use == 'all':
            img_collection.append([r, g, b])

    if use == 'all':
        # for each varient plot rgb
        for i, ax in enumerate(axes):
            ax.set(xticks=[], yticks=[])
            ax.set_title(styles[i] + ' project' +
                        '\nr: ' + str(rgb_indices[0]) +
                        ' g: ' + str(rgb_indices[1]) +
                        ' b: ' + str(rgb_indices[2]))
            ax.imshow(_channels_to_rgb(img_collection[i][0],
                                        img_collection[i][1],
                                        img_collection[i][2]))

    else:
        # plot the image
        plt.axis('off')
        plt.title('r: ' + str(rgb_indices[0]) +
                    ' g: ' + str(rgb_indices[1]) +
                    ' b: ' + str(rgb_indices[2]))
        plt.imshow(_channels_to_rgb(r, g, b))

def display_stack(self, img=None, use_indices=[1, 3, 5], use='max', percentile=75.0, force_return=False):
    """
    Parameters
    ----------
    img: TiffFile/ ndarray
        Either TiffFile or ndarray to display.
        Standard AICS image: [t, z, channel, y, x]
    use_indices: list
        List containing the indices of which channels to use for display.
        Default: [1, 3, 5]
    use: string
        String determing which numpy function to use for displaying image.
        Default: 'max'
    percentile: float
        Float to be used if numpy function is specified to be 'percentile'.
    force_return: boolean
        Boolean determining if the generated image data should be returned.
    Output
    ----------
    If given TiffFile object, will first retrieve the image data by using TiffFile.asarray(). Uses matplotlib to display the specified channels at the numpy function of the z-stack on top of each other.
    """

    img = check_node_for_image(self, img)

    # if the image object is not in ndarray form now, it was not a valid arg
    if not isinstance(img, np.ndarray):
        print('display_stack(img) requires img to be either type TiffFile or ndarray.')
        raise TypeError

    size = img.shape
    dims = len(size)
    if dims == 5:
        img = img[0,:,:,:,:]
    if dims not in [4, 5]:
        print('image data is not in a standard aics image format.')
        raise TypeError

    if img.shape[1] != 7:
        use_indices = [0, 1, 2]

    # initialize empty numpy stack
    real_values = np.zeros((size[2], size[3]))
    # append the normalized the numpy stack for each channel added
    for projection, i in enumerate(use_indices):
        # get the channel data using the specified numpy function
        if use == 'max':
            max_stack = _normalize_im(np.max(img[:, i, :, :], 0))
            real_values += max_stack

        if use == 'mean':
            max_stack = _normalize_im(np.mean(img[:, i, :, :], 0))
            real_values += max_stack

        if use == 'percentile':
            max_stack = _normalize_im(np.percentile(
                            img[:, i, :, :], percentile, 0))
            real_values += max_stack

    if force_return:
        return _normalize_im(real_values)

    if use == 'all':
        styles = ['max', 'mean', 'percentile']
        fig, axes = plt.subplots(1, len(styles), figsize=(15, 10))
        axes = axes.flatten()

        img_collection = list()
        for i, style in enumerate(styles):
            img_collection.append(self.display_stack(img,
                                    use_indices=use_indices,
                                    use=styles[i],
                                    percentile=percentile,
                                    force_return=True))

        # for each varient plot rgb
        for i, ax in enumerate(axes):
            # normalize the whole image
            ax.set(xticks=[], yticks=[])
            ax.set_title(styles[i] + ' project' +
                        '\nchannels: ' + str(use_indices))
            ax.imshow(img_collection[i])

    else:
        # normalize the whole image
        real_values = _normalize_im(real_values)
        # plot
        plt.axis('off')
        plt.title('channels: ' + str(use_indices))
        plt.imshow(real_values)

def display_segs(self, use='max', percentile=75.0, force_return=False):
    if not isinstance(self, quilt.nodes.GroupNode):
        raise TypeError('"display_segs" requires a node with at least one of each associated "cell_segs", "nuclei_segs", and "structure_segs" as the "node" parameter')

    associates = self.get_associates()
    seg_keys = ['cell_segs', 'nuclei_segs', 'structure_segs']
    if not all(key in associates for key in seg_keys):
        raise TypeError('"display_segs" requires a node with at least one of each associated "cell_segs", "nuclei_segs", and "structure_segs" as the "node" parameter')

    imgs = list()
    imgs.append(associates['cell_segs'][0]['image'])
    imgs.append(associates['nuclei_segs'][0]['image'])
    imgs.append(associates['structure_segs'][0]['image'])

    # specified np function doesn't exist or is not supported
    if use not in ['max', 'mean', 'percentile', 'all']:
        print('display_icell parameter "use" must be "max" (default), "mean", "percentile", or "all".')
        raise ValueError

    # create empty np.ndarray
    real_values = np.zeros((624, 924))

    # prep all segs
    for i, img in enumerate(imgs):
        # check if TiffFile and convert if necessary
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()
            imgs[i] = img

        # if the image object is not in ndarray form now, it was not a valid arg
        if not isinstance(img, np.ndarray):
            print('display_icell(img) requires all images in imgs to be either type TiffFile or ndarray.')
            raise TypeError

        # np function all imgs to a 2d
        if use == 'max':
            imgs[i] = _normalize_im(np.max(img, 0))
            real_values += imgs[i]
        if use == 'mean':
            imgs[i] = _normalize_im(np.mean(img, 0))
            real_values += imgs[i]
        if use == 'percentile':
            imgs[i] = _normalize_im(np.percentile(img, percentile, 0).astype(np.uint8))
            real_values += imgs[i]

    if force_return:
        return _normalize_im(real_values)

    if use == 'all':
        styles = ['max', 'mean', 'percentile']
        fig, axes = plt.subplots(1, len(styles), figsize=(15, 10))
        axes = axes.flatten()

        img_collection = list()
        for i, style in enumerate(styles):
            img_collection.append(QuiltLoader.display_segs(imgs,
                                    use=styles[i],
                                    percentile=percentile,
                                    force_return=True))

        # for each varient plot rgb
        for i, ax in enumerate(axes):
            # normalize the whole image
            ax.set(xticks=[], yticks=[])
            ax.set_title(styles[i] + ' project')
            ax.imshow(img_collection[i])

    else:
        # normalize the whole image
        real_values = _normalize_im(real_values)
        # plot
        plt.axis('off')
        plt.imshow(real_values)

def display_all(node, use='max', percentile=75.0):
    return

STANDARD_LOADERS = {'image': tfle.TiffFile,
                    'info': json.load,
                    'load': _custom_try_except}

STANDARD_ATTRIBUTES = {'get_associates': _get_associates,
                       'items': _get_items,
                       'as_dataframe': _get_dataframe,
                       'display_channels': display_channels,
                       'display_stack': display_stack,
                       'display_rgb': display_rgb,
                       'display_segs': display_segs}

class QuiltLoader:
    """
    Parameters
    ----------
    package: str/ quilt.nodes.PackageNode
        The desired package to initialize with the QuiltLoader functionality.
    load_functions: dict
        The specified loading behavior of DataNodes.
        Default: STANDARD_LOADERS
    attributes: dict
        Additional attributes
    Output
    ----------
    Changes __len__ and __getitem__ functions for all quilt.nodes.Node classes to be the QuiltLoader defined functions of get_len and get_node.
    Adds any navigation functions given by the user
    """

    # TODO:
    # any changes made by the QuiltLoader initialization should be instanced to the loaded packages objects, i believe the current implementation changes Quilt nodes to be whichever the most recent QuiltLoader initializations parameters
    #
    # i should be able to load multiple datasets with different QuiltLoader specifications that are unique from each other

    def __new__(self,
                package,
                load_functions=STANDARD_LOADERS,
                attributes=STANDARD_ATTRIBUTES):

        # set all nodes to have a pointer to the head
        pkg = self.ensure_package(self, package)
        setattr(quilt.nodes.Node, 'pkg_head', pkg)

        # set all nodes to have new functions
        quilt.nodes.Node.__len__ = self.get_len
        quilt.nodes.Node.__getitem__ = self.get_node

        # add provided load functions as an attribute
        load_functions = self.add_load_functions(load_functions)
        setattr(quilt.nodes.Node, 'load_functions', load_functions)

        # add all additional attributes
        attributes = self.add_attributes(attributes)
        for label, attr in attributes.items():
            setattr(quilt.nodes.Node, label, attr)

        # return the loaded object
        return pkg

    def add_load_functions(loaders):
        """
        Parameters
        ----------
        loaders: dict
            A dictionary of custom loading functions with.
            Ex: {'image': custom_img_loader, 'info': custom_json_loader}
        Output
        ----------
        Uses the join_dicts function to add any default loaders that were not provided in the custom loaders object.
        """

        return _join_dicts(loaders, STANDARD_LOADERS)

    def add_attributes(attributes):
        """
        Parameters
        ----------
        attributes: dict
            A dictionary of custom attributes to add to Quilt nodes.
            Ex: {'get_associates': custom_associate_loader}
        Output
        ----------
        Uses the join_dicts function to add any default attributes that were not provided in the custom attributes object.
        """

        return _join_dicts(attributes, STANDARD_ATTRIBUTES)

    def ensure_package(self, package):
        """
        Parameters
        ----------
        package: string/ quilt.nodes.PackageNode
            String representing which package to load or the preloaded Package.
        Output
        ----------
        Attempts to find the package specified by breaking down the org/pkg structure if it exists. If it doesn't, org defaults to 'aics'. Returns the found or provided PackageNode.
        """

        # given preload, simple return
        if isinstance(package, quilt.nodes.PackageNode):
            return package

        # given string, decouple org/ pkg, or use default 'aics'
        if isinstance(package, str):
            # check org/pkg split
            if '/' in package:
                package = package.split('/')
                org = package[0]
                package = package[1]
            else:
                org = 'aics'

            # attempt to find package
            try:
                return importlib.import_module(name='quilt.data.' +
                                                org + '.' + package)
            except ModuleNotFoundError:
                print(org + '/' + pkg + ' has not been installed.')
                raise ModuleNotFoundError

        # no return, raise error
        print('Must provide either preloaded Quilt package or standard "org/pkg" string.')
        raise ModuleNotFoundError

    def get_len(self):
        """
        Output
        ----------
        Returns length of a node by getting all object keys and removing any keys ment to be private, specified by an '_' character at the beginning of the key.
        """

        # get all node keys
        keys = list(self.__dict__.keys())
        iter_k = list(keys)
        # remove any keys that begin with '_'
        for remove_key in iter_k:
            if remove_key.startswith('_'):
                keys.remove(remove_key)

        return len(keys)

    def get_node(self, key):
        """
        Parameters
        ----------
        key: str/ int/ slice
            Key determining which child node should be returned by the current object.
        Output
        ----------
        Provided integer: creates a list of all public keys and returns the object at key of created list.
        Provided slice: sets start, stop, and step, to 1 if None provided, returns the generated list from expanding the slice function.
        Provided string: attempts to getattr the key from the current object.
        Additionally each of these gets attempts to use the custom load_functions to actually open the nodes.
        If key is not a string, int, or slice, raises TypeError as unsupported.
        """
        # TODO:
        # add dev_mode that returns two objects
        # current
        # fov = fov['image']
        # dev_mode
        # fov, filepath = fov['image']

        # iter by int
        if isinstance(key, int):
            # get all node keys
            keys = list(self.__dict__.keys())
            iter_k = list(keys)
            # remove any keys that begin with '_'
            for remove_key in iter_k:
                if remove_key.startswith('_'):
                    keys.remove(remove_key)

            # return the specified iterable
            # key + 1 due to nodes having a self key
            attempt = getattr(self, keys[key])
            try:
                return self.load_functions['load'](attempt, 'load')
            except AttributeError:
                return getattr(self, keys[key])

        # iter by slice
        if isinstance(key, slice):
            # simple fix for slice
            # start and stop + 1 due to nodes having self key
            start = 0 if key.start is None else key.start
            stop = 1 if key.stop is None else key.stop
            step = 1 if key.step is None else key.step

            # return the specified items
            return [self[i] for i in range(start, stop, step)]

        # iter by str
        if isinstance(key, str):
            # detect node type and load proper
            if key == 'image':
                return self.load_functions['image'](getattr(
                                        getattr(self, key), 'load')())
            if key == 'info':
                return self.load_functions['info'](open(
                                        getattr(getattr(self, key), 'load')()))
            # try:
            #     return self.load_functions['load'](self, 'load')
            # except AttributeError:
            return getattr(self, key)

        # return unsupported type
        print('unsupported iter-type:', type(key))
        raise TypeError
