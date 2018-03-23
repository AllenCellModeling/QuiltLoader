import tifffile as tfle
import numpy as np
import importlib
import codecs
import quilt
import json

import matplotlib.pyplot as plt
from IPython import get_ipython
try:
    get_ipython().run_line_magic('matplotlib', 'inline')
except AttributeError:
    pass

def _normalize_im(img):
    im_min = np.min(img)
    im_max = np.max(img)

    img -= im_min
    img = img / (im_max - im_min)

    img[img<0] = 0
    img[img>1] = 1

    img *= 255

    return img

# channels to rgb function
# takes three xy images and find the normal inverse of them all and returns them in a stack
def _channels_to_rgb(c1, c2, c3):
    r = _normalize_im(c1)
    g = _normalize_im(c2)
    b = _normalize_im(c3)
    return np.stack((r,g,b), -1).astype(int)

def CUSTOM_TRY_EXCEPT(node, key):
    # this is disgusting and im sorry
    try:
        return json.load(open(getattr(node, key)()))
    except:
        pass

    try:
        return tfle.TiffFile(getattr(node, key)())
    except:
        pass

    # setattr(self[key], '_parent_node_', self)
    return getattr(node, key)()

STANDARD_LOADERS = {'image': tfle.TiffFile,
                    'info': json.load,
                    'load': CUSTOM_TRY_EXCEPT}

class QuiltLoader:
    def __new__(self, package, load_functions=STANDARD_LOADERS):
        # set all nodes to have new functions
        quilt.nodes.Node.__len__ = self.get_len
        quilt.nodes.Node.__getitem__ = self.get_node

        load_functions = self.compare_load_functions(load_functions)

        setattr(quilt.nodes.Node, 'load_functions', load_functions)

        # return the loaded object
        return self.ensure_package(self, package)

    def compare_load_functions(loaders):
        default_loaders = ['image', 'info', 'load']

        for required in default_loaders:
            if required not in loaders.keys():
                loaders[required] = STANDARD_LOADERS[required]

        return loaders

    # load package by either preload or 'org/pkg'
    def ensure_package(self, package):
        # given preload, simple return
        if isinstance(package, quilt.nodes.PackageNode):
            return package

        # given string, decouple org/ pkg, or use default 'aics'
        if isinstance(package, str):
            if '/' in package:
                package = package.split('/')
                org = package[0]
                package = package[1]
            else:
                org = 'aics'

            try:
                return importlib.import_module(name='quilt.data.' + org + '.' + package)
            except ModuleNotFoundError:
                print(org + '/' + pkg + ' has not been installed.')
                raise ModuleNotFoundError

        # no return, raise error
        print('Must provide either preloaded Quilt package or standard "org/pkg" string.')
        raise ModuleNotFoundError

    # len of group node
    def get_len(self):
        # get all node keys
        keys = list(self.__dict__.keys())
        # remove any keys that begin with '_'
        for remove_key in keys:
            if '_' == remove_key[0]:
                keys.remove(remove_key)

        return len(keys)

    # basic iterables
    def get_node(self, key):
        # iter by int
        if isinstance(key, int):
            # get all node keys
            keys = list(self.__dict__.keys())
            # remove any keys that begin with '_'
            for remove_key in keys:
                if '_' == remove_key[0]:
                    keys.remove(remove_key)

            # return the specified iterable
            # key + 1 due to nodes having a self key
            attempt = getattr(self, keys[key + 1])
            try:
                return self.load_functions['load'](attempt, 'load')
            except AttributeError:
                # setattr(self[key + 1], '_parent_node_', self)
                return getattr(self, keys[key + 1])

        # iter by slice
        if isinstance(key, slice):
            # simple fix for slice
            # start and stop + 1 due to nodes having self key
            start = 1 if key.start is None else key.start
            stop = 1 if key.stop is None else key.stop
            step = 1 if key.step is None else key.step

            # return the specified items
            return [self[i] for i in range(start, stop + 1, step)]

        # iter by str
        if isinstance(key, str):
            # detect node type and load proper
            if key == 'image':
                return self.load_functions['image'](getattr(getattr(self, key), 'load')())
            if key == 'info':
                return self.load_functions['info'](open(getattr(getattr(self, key), 'load')()))
            if key == 'load':
                return self.load_functions['load'](self, key)

            # no specific node type requested, must be a group node
            # setattr(self[key], '_parent_node_', self)
            return getattr(self, key)

        # return unsupported type
        print('unsupported iter-type:', type(key))
        raise TypeError

    def display_channels(img, use_channels=[1, 3, 5, 6]):
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

        converted = False

        # check if TiffFile and convert if necessary
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()
            converted = True

        # if the image object is not in ndarray form now, it was not a valid arg
        if not isinstance(img, np.ndarray):
            print('display_channels(img) requires img to be either type TiffFile or ndarray.')
            raise TypeError

        # initialize plots
        fig, axes = plt.subplots(1, len(use_channels), figsize=(15, 10))
        axes = axes.flatten()

        dims = len(img.shape)
        if dims == 5:
            img = np.max(img, 0)
        if dims not in [4, 5]:
            print('image data is not in a standard aics image format.')
            raise TypeError

        # for each channel plot max of stack
        for i, ax in enumerate(axes):
            z_stack = img[:,use_channels[i],:,:]
            max_project = np.max(z_stack, 0)
            ax.imshow(max_project)
            ax.set(xticks=[], yticks=[])
            ax.set_title('channel: ' + str(use_channels[i]))

        # viewing nicety
        plt.tight_layout()

        # return the ndarray of the img if it was converted
        if converted:
            return img

    def display_rgb(img, rgb_indices=[1, 3, 5], use='max', percentile=75.0):
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

        # specified np function doesn't exist or is not supported
        if use not in ['max', 'mean', 'percentile', 'all']:
            print('display_rgb parameter "use" must be "max" (default), "mean", "percentile", or "all".')
            raise ValueError

        converted = False

        # check if TiffFile and convert if necessary
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()
            converted = True

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
            img = np.max(img, 0)
        if dims not in [4, 5]:
            print('image data is not in a standard aics image format.')
            raise TypeError

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

        # return the ndarray of the img if it was converted
        if converted:
            return img

    def display_stack(img, use_indices=[1, 3, 5], use='max', percentile=75.0, force_return=False):
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

        # specified np function doesn't exist or is not supported
        if use not in ['max', 'mean', 'percentile', 'all']:
            print('display_stack parameter "use" must be "max" (default), "mean", "percentile", or "all".')
            raise ValueError

        converted = False

        # check if TiffFile and convert if necessary
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()
            converted = True

        # if the image object is not in ndarray form now, it was not a valid arg
        if not isinstance(img, np.ndarray):
            print('display_stack(img) requires img to be either type TiffFile or ndarray.')
            raise TypeError

        size = img.shape
        dims = len(size)
        if dims == 5:
            img = np.max(img, 0)
        if dims not in [4, 5]:
            print('image data is not in a standard aics image format.')
            raise TypeError

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
                img_collection.append(QuiltLoader.display_stack(img,
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

        # return the ndarray of the img if it was converted
        if converted:
            return img

    def display_icell(imgs=[], use='max', force_return=False):
        # specified np function doesn't exist or is not supported
        if use not in ['max', 'mean', 'all']:
            print('display_icell parameter "use" must be "max" (default), "mean"s, or "all".')
            raise ValueError

        converted = False

        # create empty np.ndarray
        real_values = np.zeros((624, 924))

        # prep all segs
        for i, img in enumerate(imgs):
            # check if TiffFile and convert if necessary
            if isinstance(img, tfle.tifffile.TiffFile):
                img = img.asarray()
                imgs[i] = img
                converted = True

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

        if force_return:
            return _normalize_im(real_values)

        if use == 'all':
            styles = ['max', 'mean']
            fig, axes = plt.subplots(1, len(styles), figsize=(15, 10))
            axes = axes.flatten()

            img_collection = list()
            for i, style in enumerate(styles):
                img_collection.append(QuiltLoader.display_icell(imgs,
                                        use=styles[i],
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

        # return the ndarray of the img if it was converted
        if converted:
            return img
