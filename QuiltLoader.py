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
        quilt.nodes.Node.__len__ = self.get_len
        quilt.nodes.Node.__getitem__ = self.get_node

        return self.ensure_package(self, package)

    # load package by either preload or 'org/pkg'
    def ensure_package(self, package):
        if isinstance(package, quilt.nodes.PackageNode):
            return package
        elif isinstance(package, str):
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
        else:
            print('Must provide either preloaded Quilt package or standard "org/pkg" string.')
            raise ModuleNotFoundError

    # len of group node
    def get_len(self):
        remove_keys = ['_package', '_node', '_DataNode__cached_data']
        keys = list(self.__dict__.keys())
        for remove_key in remove_keys:
            keys.remove(remove_key)

        return len(keys)

    # basic iterables
    def get_node(self, key):
        remove_keys = ['_package', '_node', '_DataNode__cached_data']

        # iter by int
        if isinstance(key, int):
            keys = list(self.__dict__.keys())
            for remove_key in remove_keys:
                keys.remove(remove_key)

            return getattr(self, keys[key])

        # iter by slice
        elif isinstance(key, slice):
            keys = list(self.__dict__.keys())
            for remove_key in remove_keys:
                keys.remove(remove_key)

            start = 0 if key.start is None else key.start
            stop = 0 if key.stop is None else key.stop
            step = 1 if key.step is None else key.step

            return [self[i] for i in range(start, stop, step)]

        # iter by str
        elif isinstance(key, str):
            if key == 'image':
                return tfle.TiffFile(getattr(getattr(self, key), 'load')())
            elif key == 'info':
                return json.load(open(getattr(getattr(self, key), 'load')()))
            else:
                return getattr(self, key)

        # return unsupported type
        else:
            print('unsupported iter-type:', type(key))
            raise TypeError

    def display_channels(img, use_channels=[1, 3, 5, 6]):
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()

        if not isinstance(img, np.ndarray):
            print('display_channels(img) requires img to be either type TiffFile or ndarray')
            raise TypeError

        fig, axes = plt.subplots(1, len(use_channels), figsize=(15, 10))
        axes = axes.flatten()

        for i, ax in enumerate(axes):
            z_stack = img[:,use_channels[i],:,:]
            max_project = np.max(z_stack, 0)
            ax.imshow(max_project)
            ax.set(xticks=[], yticks=[])
            ax.set_title('channel: ' + str(use_channels[i]))

        plt.tight_layout()

        return img

    def display_rgb(img, channel_to_rgb_indices=[1, 3, 5], use='max', percentile=75.0):
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()

        if not isinstance(img, np.ndarray):
            print('display_rgb(img) requires img to be either type TiffFile or ndarray')
            raise TypeError

        if use == 'max':
            c1 = np.max(img[:, channel_to_rgb_indices[0], :, :], 0)
            c2 = np.max(img[:, channel_to_rgb_indices[1], :, :], 0)
            c3 = np.max(img[:, channel_to_rgb_indices[2], :, :], 0)
        elif use == 'mean':
            c1 = np.mean(img[:, channel_to_rgb_indices[0], :, :], 0)
            c2 = np.mean(img[:, channel_to_rgb_indices[1], :, :], 0)
            c3 = np.mean(img[:, channel_to_rgb_indices[2], :, :], 0)
        elif use =='percentile':
            c1 = np.percentile(img[:, channel_to_rgb_indices[0], :, :], percentile, 0)
            c2 = np.percentile(img[:, channel_to_rgb_indices[1], :, :], percentile, 0)
            c3 = np.percentile(img[:, channel_to_rgb_indices[2], :, :], percentile, 0)
        else:
            print('display_stack parameter "use" must be either max (default), mean, or percentile.')
            raise ValueError

        plt.axis('off')
        plt.title('r: ' + str(channel_to_rgb_indices[0]) +
                    ' g: ' + str(channel_to_rgb_indices[1]) +
                    ' b: ' + str(channel_to_rgb_indices[2]))
        plt.imshow(_channels_to_rgb(c1, c2, c3))

        return img

    def display_stack(img, use_indices=[1, 3, 5], use='max', percentile=75.0):
        if isinstance(img, tfle.tifffile.TiffFile):
            img = img.asarray()

        if not isinstance(img, np.ndarray):
            print('display_stack(img) requires img to be either type TiffFile or ndarray')
            raise TypeError

        real_values = np.zeros((624, 924))
        for i in use_indices:
            if use == 'max':
                max_stack = np.max(img[:, i, :, :], 0)
            elif use =='mean':
                max_stack = np.mean(img[:, i, :, :], 0)
            elif use =='percentile':
                max_stack = np.percentile(img[:, i, :, :], percentile, 0)
            else:
                print('display_stack parameter "use" must be either max (default), mean, or percentile.')
                raise ValueError

            normed = _normalize_im(max_stack)
            real_values += normed

        real_values = _normalize_im(real_values)

        plt.axis('off')
        plt.title('channels: ' + str(use_indices))
        plt.imshow(real_values)

        return img
