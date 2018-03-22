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

class QuiltLoader:
    def __new__(self, package):
        # set all nodes to have new functions
        quilt.nodes.Node.__len__ = self.get_len
        quilt.nodes.Node.__getitem__ = self.get_node

        # return the loaded object
        return self.ensure_package(self, package)

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

            # this is disgusting and im sorry
            try:
                try:
                    return json.load(open(getattr(attempt, 'load')()))
                except:
                    pass

                try:
                    return tfle.TiffFile(getattr(self, 'load')())
                except:
                    pass

                return getattr(self, 'load')()
            except AttributeError:
                return getattr(self, keys[key + 1])

        # iter by slice
        if isinstance(key, slice):
            # simple fix for slice
            # start and stop + 1 due to nodes having self key
            start = 1 if key.start is None else key.start
            stop = 1 if key.stop is None else key.stop
            step = 1 if key.step is None else key.step

            # return the specified items
            return [self[i] for i in range(start, stop, step)]

        # iter by str
        if isinstance(key, str):
            # detect node type and load proper
            if key == 'image':
                return tfle.TiffFile(getattr(getattr(self, key), 'load')())
            if key == 'info':
                return json.load(open(getattr(getattr(self, key), 'load')()))
            if key == 'load':
                # this is disgusting and im sorry
                try:
                    return json.load(open(getattr(self, key)()))
                except:
                    pass

                try:
                    return tfle.TiffFile(getattr(self, key)())
                except:
                    pass

                return getattr(self, key)()

            # no specific node type requested, must be a group node
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
            print('display_channels(img) requires img to be either type TiffFile or ndarray')
            raise TypeError

        # initialize plots
        fig, axes = plt.subplots(1, len(use_channels), figsize=(15, 10))
        axes = axes.flatten()

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

        converted = False

        # check if TiffFile and convert if necessary
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()
            converted = True

        # if the image object is not in ndarray form now, it was not a valid arg
        if not isinstance(img, np.ndarray):
            print('display_rgb(img) requires img to be either type TiffFile or ndarray')
            raise TypeError

        # get the rgb channel data using the specified numpy function
        if use == 'max':
            r = np.max(img[:, rgb_indices[0], :, :], 0)
            g = np.max(img[:, rgb_indices[1], :, :], 0)
            b = np.max(img[:, rgb_indices[2], :, :], 0)
        elif use == 'mean':
            r = np.mean(img[:, rgb_indices[0], :, :], 0)
            g = np.mean(img[:, rgb_indices[1], :, :], 0)
            b = np.mean(img[:, rgb_indices[2], :, :], 0)
        elif use =='percentile':
            r = np.percentile(img[:, rgb_indices[0], :, :], percentile, 0)
            g = np.percentile(img[:, rgb_indices[1], :, :], percentile, 0)
            b = np.percentile(img[:, rgb_indices[2], :, :], percentile, 0)
        # specified np function doesn't exist or is not supported
        else:
            print('display_stack parameter "use" must be either max (default), mean, or percentile.')
            raise ValueError

        # plot the image
        plt.axis('off')
        plt.title('r: ' + str(rgb_indices[0]) +
                    ' g: ' + str(rgb_indices[1]) +
                    ' b: ' + str(rgb_indices[2]))
        plt.imshow(_channels_to_rgb(r, g, b))

        # return the ndarray of the img if it was converted
        if converted:
            return img

    def display_stack(img, use_indices=[1, 3, 5], use='max', percentile=75.0):
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
            String determing which numpy function to use for displaying image
            Default: 'max'
        percentile: float
            Float to be used if numpy function is specified to be 'percentile'.
        Output
        ----------
        If given TiffFile object, will first retrieve the image data by using TiffFile.asarray(). Uses matplotlib to display the specified channels at the numpy function of the z-stack on top of each other.
        """

        converted = False

        # check if TiffFile and convert if necessary
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()
            converted = True

        # if the image object is not in ndarray form now, it was not a valid arg
        if not isinstance(img, np.ndarray):
            print('display_stack(img) requires img to be either type TiffFile or ndarray')
            raise TypeError

        # initialize empty numpy stack
        size = img.shape
        real_values = np.zeros((size[2], size[3]))
        # append the normalized the numpy stack for each channel added
        for i in use_indices:
            # get the channel data using the specified numpy function
            if use == 'max':
                max_stack = np.max(img[:, i, :, :], 0)
            elif use =='mean':
                max_stack = np.mean(img[:, i, :, :], 0)
            elif use =='percentile':
                max_stack = np.percentile(img[:, i, :, :], percentile, 0)

            # specified np function doesn't exist or is not supported
            else:
                print('display_stack parameter "use" must be either max (default), mean, or percentile.')
                raise ValueError

            normed = _normalize_im(max_stack)
            real_values += normed

        # normalize the whole image
        real_values = _normalize_im(real_values)

        # plot
        plt.axis('off')
        plt.title('channels: ' + str(use_indices))
        plt.imshow(real_values)

        # return the ndarray of the img if it was converted
        if converted:
            return img
