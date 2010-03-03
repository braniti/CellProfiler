'''<b>Smooth</b> smooths (i.e., blurs) images
<hr>

This module allows you to smooth (blur) images, which can be helpful to 
remove artifacts of a particular size. 
Note that smoothing can be a time-consuming process. 
'''
# CellProfiler is distributed under the GNU General Public License.
# See the accompanying file LICENSE for details.
# 
# Developed by the Broad Institute
# Copyright 2003-2010
# 
# Please see the AUTHORS file for credits.
# 
# Website: http://www.cellprofiler.org

__version__="$Revision$"

import numpy as np
import scipy.ndimage as scind

import cellprofiler.cpmodule as cpm
import cellprofiler.settings as cps
import cellprofiler.cpimage as cpi

from cellprofiler.cpmath.smooth import smooth_with_function_and_mask
from cellprofiler.cpmath.smooth import circular_gaussian_kernel
from cellprofiler.cpmath.smooth import fit_polynomial
from cellprofiler.cpmath.filter import median_filter, bilateral_filter, circular_average_filter

FIT_POLYNOMIAL = 'Fit Polynomial'
MEDIAN_FILTER = 'Median Filter'
GAUSSIAN_FILTER = 'Gaussian Filter'
SMOOTH_KEEPING_EDGES = 'Smooth Keeping Edges'
CIRCULAR_AVERAGE_FILTER = 'Circular Average Filter'

class Smooth(cpm.CPModule):
    
    module_name = 'Smooth'
    category = "Image Processing"
    variable_revision_number = 1
     
    def create_settings(self):
        self.image_name = cps.ImageNameSubscriber('Select the input image','None')
        self.filtered_image_name = cps.ImageNameProvider('Name the output image','FilteredImage')
        self.smoothing_method = cps.Choice('Select smoothing method',
                                           [FIT_POLYNOMIAL,
                                            GAUSSIAN_FILTER,
                                            MEDIAN_FILTER,
                                            SMOOTH_KEEPING_EDGES,
                                            CIRCULAR_AVERAGE_FILTER],doc="""
            This module smooths images using one of several filters. 
            Fitting a polynomial
            is fastest but does not allow a very tight fit compared to the other methods:
            <ul>
            <li><i>Fit Polynomial:</i> This method treats the intensity of the image pixels
            as a polynomial function of the x and y position of
            each pixel. It fits the intensity to the polynomial,
            <i>A x<sup>2</sup> + B y<sup>2</sup> + C x*y + D x + E y + F</i>.
            This will produce a smoothed image with a single peak or trough of intensity 
            that tapers off elsewhere in the image. For many microscopy images (where 
            the illumination of the lamp is brightest in the center of field of view), 
            this method will produce an image with a bright central region and dimmer 
            edges. But, in some cases the peak/trough of the polynomial may actually 
            occur outside of the image itself.</li>
            <li><i>Gaussian Filter:</i> This method convolves the image with a Gaussian whose
            full width at half maximum is the artifact diameter entered.
            Its effect is to blur and obscure features
            smaller than the artifact diameter and spread bright or
            dim features larger than the artifact diameter.</li>
            <li><i>Median Filter:</i> This method finds the median pixel value within the
            artifact diameter you specify. It removes bright or dim features that are much smaller
            than the artifact diameter.</li>
            <li><i>Smooth Keeping Edges:</i> This method uses a bilateral filter which
            limits Gaussian smoothing across an edge while 
            applying smoothing perpendicular to an edge. The effect
            is to respect edges in an image while smoothing other
            features. <i>Smooth Keeping Edges</i> will filter an image with reasonable
            speed for artifact diameters greater than 10 and for
            intensity differences greater than 0.1. The algorithm
            will consume more memory and operate more slowly as
            you lower these numbers.</li>
            <li><i>Circular Average Filter:</i> This method convolves the image with
            a uniform circular averaging filter whose size is the artifact diameter entered. This filter is
            useful for re-creating an out-of-focus blur to an image.</li>
            </ul>""")
        
        self.wants_automatic_object_size = cps.Binary('Calculate artifact diameter automatically?',True,doc="""
            <i>(Used only if Gaussian, Median or Smooth Keeping Edges is selected)</i><br>
            If this box is checked, the module will choose an artifact diameter based on
            the size of the image. The minimum size it will choose is 30 pixels,
            otherwise the size is 1/40 of the size of the image.""")
        
        self.object_size = cps.Float('Typical artifact diameter, in  pixels',16.0,doc="""
            <i>(Used only if choosing the artifact diameter automatically is unchecked)</i><br>
            Enter the approximate diameter of the features to be blurred by
            the smoothing algorithm. This value is used to calculate the size of 
            the spatial filter. To measure distances easily in an open image, 
            use <i>Tools > Show pixel data</i>. Clicking and dragging the 
            mouse will yield a <i>Length</i> measurement in the 
            bottom bar of the figure window.
            For most smoothing methods, selecting a
            diameter over ~50 will take substantial amounts of time to process.""")
        
        self.sigma_range = cps.Float('Edge intensity difference', .1,doc="""
            <i>(Used only if Smooth Keeping Edges is selected)</i><br>
            What are the differences in intensity in the edges that you want to preserve?
            Enter the intensity step that indicates an edge in an image.
            Edges are locations where the intensity changes precipitously, so this
            setting is used to adjust the rough magnitude of these changes. A lower
            number will preserve weaker edges. A higher number will preserve only stronger edges.
            Values should be between zero and one. To view pixel intensities in 
            an open image, use <i>Tools > Show pixel data</i>. When you move 
            your mouse over the image,the pixel intensities will appear in the 
            bottom bar of the figure window.""")

    def settings(self):
        return [self.image_name, self.filtered_image_name, 
                self.smoothing_method, self.wants_automatic_object_size,
                self.object_size, self.sigma_range]

    def visible_settings(self):
        result = [self.image_name, self.filtered_image_name, 
                self.smoothing_method]
        if self.smoothing_method.value != FIT_POLYNOMIAL:
            result.append(self.wants_automatic_object_size)
            if not self.wants_automatic_object_size.value:
                result.append(self.object_size)
            if self.smoothing_method.value == SMOOTH_KEEPING_EDGES:
                result.append(self.sigma_range)
        return result

    def is_interactive(self):
        return False

    def run(self, workspace):
        image = workspace.image_set.get_image(self.image_name.value,
                                              must_be_grayscale=True)
        pixel_data = image.pixel_data
        if self.wants_automatic_object_size.value:
            object_size = min(30,max(1,np.mean(pixel_data.shape)/40))
        else:
            object_size = float(self.object_size.value)
        sigma = object_size / 2.35
        if self.smoothing_method.value == GAUSSIAN_FILTER:
            def fn(image):
                return scind.gaussian_filter(image, sigma, 
                                             mode='constant', cval=0)
            output_pixels = smooth_with_function_and_mask(pixel_data, fn,
                                                          image.mask)
        elif self.smoothing_method.value == MEDIAN_FILTER:
            output_pixels = median_filter(pixel_data, image.mask, 
                                          object_size/2+1)
        elif self.smoothing_method.value == SMOOTH_KEEPING_EDGES:
            sigma_range = float(self.sigma_range.value)
            output_pixels = bilateral_filter(pixel_data, image.mask,
                                             sigma, sigma_range)
        elif self.smoothing_method.value == FIT_POLYNOMIAL:
            output_pixels = fit_polynomial(pixel_data, image.mask)
        elif self.smoothing_method.value == CIRCULAR_AVERAGE_FILTER:
            output_pixels = circular_average_filter(pixel_data, object_size/2+1, image.mask)
        else:
            raise ValueError("Unsupported smoothing method: %s" %
                             self.smoothing_method.value)
        output_image = cpi.Image(output_pixels, parent_image = image)
        workspace.image_set.add(self.filtered_image_name.value,
                                output_image)
        workspace.display_data.pixel_data = pixel_data
        workspace.display_data.output_pixels = output_pixels

    def display(self, workspace):
        figure = workspace.create_or_find_figure(subplots=(1,2))
        figure.subplot_imshow_grayscale(0, 0, 
                                        workspace.display_data.pixel_data,
                                        "Original: %s" % 
                                        self.image_name.value)
        figure.subplot_imshow_grayscale(0, 1,
                                        workspace.display_data.output_pixels,
                                        "Filtered: %s" %
                                        self.filtered_image_name.value)
    
    def upgrade_settings(self, setting_values, variable_revision_number, 
                         module_name, from_matlab):
        if (module_name == 'SmoothKeepingEdges' and from_matlab and
            variable_revision_number == 1):
            image_name, smoothed_image_name, spatial_radius, \
            intensity_radius = setting_values
            setting_values = [image_name,
                              smoothed_image_name,
                              'Smooth Keeping Edges',
                              'Automatic',
                              cps.DO_NOT_USE,
                              cps.NO,
                              spatial_radius,
                              intensity_radius]
            module_name = 'SmoothOrEnhance'
            variable_revision_number = 5
        if (module_name == 'SmoothOrEnhance' and from_matlab and
            variable_revision_number == 4):
            # Added spatial radius
            setting_values = setting_values + ["0.1"]
            variable_revision_number = 5
        if (module_name == 'SmoothOrEnhance' and from_matlab and
            variable_revision_number == 5):
            if setting_values[2] in ('Remove BrightRoundSpeckles',
                                     'Enhance BrightRoundSpeckles (Tophat Filter)'):
                raise ValueError('The Smooth module does not support speckles operations. Please use EnhanceOrSuppressSpeckles instead')
            setting_values = [setting_values[0], # image name
                              setting_values[1], # result name
                              setting_values[2], # smoothing method
                              cps.YES if setting_values[3] == 'Automatic'
                              else cps.NO,       # wants smoothing
                              '16.0' if  setting_values[3] == 'Automatic'
                              else (setting_values[6]
                                    if setting_values[2] == SMOOTH_KEEPING_EDGES
                                    else setting_values[3]),
                              setting_values[7]]
            module_name = 'Smooth'
            from_matlab = False
            variable_revision_number = 1
        return setting_values, variable_revision_number, from_matlab
