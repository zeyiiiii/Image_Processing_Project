from skimage import io, color, exposure, metrics, filters, util, segmentation, feature
from skimage.transform import resize
import numpy as np
import cv2 as cv
import matplotlib.pyplot as plt
import scipy.fft as sft
import scipy.signal as sps
from PIL import Image

class Helper:
    
    def __init__(self) -> None:
        pass
    
    def get_dft(self,img):
        return sft.fft2(img)
    
    def get_dft_magnitude(self,dft):
        """
        Returns the log10-scaled magnitude of the DFT shifted to have low frequencies at the center
        Param: dft (the complex DFT of an image)
        """   
        dft_mag = np.log10(1 + np.abs(sft.fftshift(dft)))
        return dft_mag
    
    def display_img(self,img):
        """
        Display the image img both as 2D and 3D
        Param: img (a float image with values between 0 and 1)
        """
        I, J = img.shape
        fig = plt.figure(figsize=(8, 4))
        ax1 = fig.add_subplot(1, 3, 1)
        ax1.imshow(img, cmap='viridis')
        ax1.set_title("Original Image")
        ax2 = fig.add_subplot(1, 3, 2, projection='3d')
        j = np.arange(0, J, 1)
        i = np.arange(0, I, 1)
        jj, ii = np.meshgrid(j, i)
        dft = self.get_dft(img)
        dft_mag = self.get_dft_magnitude(dft)
        ax2.plot_surface(jj, ii, dft_mag, rstride=1, cstride=1, cmap='viridis', antialiased=False)
        ax2.set_title("3D Plot")
        ax3 = fig.add_subplot(1, 3, 3)
        inv = np.real(sft.ifft2(dft))
        ax3.imshow(inv, cmap='gray')
        ax3.set_title("Inverse DFT")
    
    def pad_image(self, sticker, image, mode = "constant"):
        """Pad the imaeg

        Args:
            sticker (np.array): sticker
            image (np.array): image
            mode (str, optional): padding mode: constant or reflect. Defaults to "constant".

        Returns:
            box_height, box_width, padded_image
        """
        # Define the size of the search box
        box_height = sticker.shape[0]
        box_width = sticker.shape[1]
        
        # Calculate the required padding
        pad_height = 0 if image.shape[0] % box_height == 0 else box_height - image.shape[0] % box_height
        pad_width = 0 if image.shape[1] % box_width == 0 else box_width - image.shape[1] % box_width
        
        # Apply padding to the image
        if mode == "constant":
            padded_image = np.pad(image, ((0, pad_height), (0, pad_width)), mode='constant', constant_values=1)
        elif mode == "reflect":
            padded_image = np.pad(image, ((0, pad_height), (0, pad_width)), mode='reflect')
        else: 
            print("Invalid Mode")
       
        return box_height, box_width, padded_image
    
    def dft_by_search_box(self,sticker,image): 
        """Get the DFT of each searching box from the image

        Args:
            sticker (np.array): the sticker
            image  (np.array): the original image

        Returns:
            dft_by_box
        """
          
        # Apply padding to the image
        box_height, box_width, padded_image = self.pad_image(sticker, image)
        
        # Initialize an array to store the DFT results
        dft_by_box = []
        
        # Loop over the padded image
        for y in range(0, padded_image.shape[0], box_height):
            for x in range(0, padded_image.shape[1], box_width):
                # Extract the search box from the padded image
                search_box = padded_image[y:y + box_height, x:x + box_width]
                
                # Compute the DFT of each search box
                search_box_dft = self.get_dft(search_box)
                search_box_dft_mag = self.get_dft_magnitude(search_box_dft)
                # Store the DFT result
                dft_by_box.append(search_box_dft_mag)
        
        return dft_by_box
    
    def create_spectrogram(self, sticker, image):
        """ Create a 2D DFT spectrogram of the image
            By combining the DFTs of each searching box

        Args:
            sticker (np.array): the sticker
            image  (np.array): the original image
        
        Returns:
            composite_dft: the complete 2D spectrogram of the image
        """
        # Get dft of each searching box from the image
        dft_by_box = self.dft_by_search_box(sticker, image)
        # Pad the image
        box_height, box_width, padded_image = self.pad_image(sticker,image)
        
        # Create an empty composite array
        composite_dft = np.zeros_like(padded_image)

        total_height = composite_dft.shape[0]
        total_width = composite_dft.shape[1]
        
        num_boxes_vertically = total_height//box_height
        num_boxes_horizontally = total_width//box_width
        
        # Populate the composite array with DFT results
        for i in range(num_boxes_vertically):
            for j in range(num_boxes_horizontally):
                # Calculate the index in the list
                idx = i * num_boxes_horizontally + j
                dft_box = dft_by_box[idx]
          
                # Place the DFT result in the correct position in the composite array
                composite_dft[
                    i * box_height: (i + 1) * box_height,
                    j * box_width: (j + 1) * box_width
                ] = dft_box
        
        return composite_dft
       
            
    def show_spectrogram(self, composite_dft, sticker, grid = False):
        """Display composite_dft as image
        """
        if grid == False:
            plt.figure(figsize=(10, 5))
            plt.imshow(composite_dft, cmap = "gray")
            plt.colorbar()
            plt.title('2-D Spectrogram Representation')
      
        elif grid == True:
           self.show_grid(sticker,composite_dft)
           
    
    def show_grid(self, sticker, image, padding_mode = "constant"):
        """Add grid line to the image based on the sticker size
        
        Args:
            sticker (np.array): the sticker
            image  (np.array): the target image 
        """
        # Pad the image
        box_height, box_width, padded_image = self.pad_image(sticker,image, mode = padding_mode)
        num_boxes_vertically = padded_image.shape[0]//box_height
        num_boxes_horizontally = padded_image.shape[1]//box_width
        
        plt.figure(figsize=(10, 5))
        plt.imshow(padded_image, cmap='gray')
        plt.colorbar()
        plt.title('Padded Image with Grid Lines')
        
        # Calculate the boundaries for the vertical lines (edges of the boxes)
        for i in range(1, num_boxes_horizontally):
            plt.axvline(x=i * box_width, color='orange', linestyle='-', linewidth=2)

        # Calculate the boundaries for the horizontal lines (edges of the boxes)
        for j in range(1, num_boxes_vertically):
            plt.axhline(y=j * box_height, color='orange', linestyle='-', linewidth=2)

        
    def find_location_mse(self, sticker, image):
        """Find the location of the sticker based on mse value

        Args:
            sticker (np.array): the sticker
            image (np.array): the target image

        Returns:
            best_box: Target box number
            min_mse: The minimum value of mse
            sorted_box_idx: Sorted box numbers based on mse values from min to max 
            sorted_mse: Sorted mse values from min to max
        """
        
        sticker_dft = self.get_dft(sticker)
        sticker_dft_mag = self.get_dft_magnitude(sticker_dft)
        mse_results = []
        best_box = -1
        min_mse = np.inf
        
        dft_by_box = self.dft_by_search_box(sticker, image)
        i = 0
        for dft_mag in dft_by_box:
            # Compute the MSE between the two magnitude spectra
            mse = np.mean((dft_mag - sticker_dft_mag) ** 2)
            mse_results.append(mse)
           
            if(mse < min_mse):
                min_mse = mse
                best_box = i+1
            i += 1
        
        sorted_mse_idx = np.argsort(mse_results)
        sorted_box_idx = [i + 1 for i in sorted_mse_idx]
        sorted_mse = np.sort(mse_results)
        
        return best_box, min_mse, sorted_box_idx, sorted_mse
            
    
    def divide_into_four(self, image):
        """Divide an image into 4 equal parts

        Args:
            image (np.array): image

        Returns:
            4 sub-images
        """
        height = image.shape[0]
        width = image.shape[1]
        
        mid_height = height // 2
        mid_width = width // 2
        
        # Extract each part of the image
        top_left = image[:mid_height, :mid_width]
        top_right = image[:mid_height, mid_width:]
        bottom_left = image[mid_height:, :mid_width]
        bottom_right = image[mid_height:, mid_width:]

        return (top_left, (0, 0, mid_height, mid_width)), \
               (top_right, (0, mid_width, mid_height, width)), \
               (bottom_left, (mid_height, 0, height, mid_width)), \
               (bottom_right, (mid_height, mid_width, height, width))
    
    
    def find_location_recursive(self, sticker, image, bounds, min_mse = float('inf')):
        """Recursively divide the image into 4 parts and search for the sticker

        Args:
            sticker (np.array): sticker
            image (np.array): image
            bounds (tuple): top left, top right, bottom left, bottom right of the image
            min_mse (float, optional): Current minimum value of mse 

        Returns:
            image: the target sub-image
            bounds: top left, top right, bottom left, bottom right of the image
        """
        
        if image.shape[0] < sticker.shape[0] and image.shape[1] < sticker.shape[1]:
            return image, bounds
        
        sticker_dft = self.get_dft(sticker)
        sticker_dft = self.get_dft_magnitude(sticker_dft)
        
        # Divide the image into four equal parts
        parts = self.divide_into_four(image)
        selected_part = None
        selected_bounds = None
        
        for part, (top, left, bottom, right) in parts:
        
            # Resize sticker to match the current part's dimensions
            sticker_dft_resized = resize(sticker_dft, (part.shape[0], part.shape[1]))
            part_dft = self.get_dft(part)
            part_dft = self.get_dft_magnitude(part_dft)
            
            mse = np.mean((part_dft - sticker_dft_resized) ** 2)
            
            if mse < min_mse:
                min_mse = mse
                selected_part = part
                selected_bounds = (bounds[0] + top, bounds[1] + left, bounds[0] + bottom, bounds[1] + right)

        if selected_part is not None:
            image, bounds = self.find_location_recursive(sticker, selected_part, selected_bounds, min_mse)
            return selected_part, selected_bounds 
        else:
            return image, bounds
    
    
    def find_location_sliding_window(self, sticker, image, x_step = 20, y_step = 20):
        """Find the best location of the searching window by sliding it over the image
             in the given steps

        Args:
            sticker (np.array): sticker
            image (np.arra): image
            step (int, optional): The number of pixels the window skips each time

        Returns:
            best_position (tuple): the top left coordinate of the best window
            best_match_box (np.array): the best window
        """
        
        sticker_height, sticker_width = sticker.shape
        image_height, image_width = image.shape

        if sticker_height > image_height or sticker_width > image_width:
            return None  # The sticker can't fit in the image

        min_mse = float('inf')
        best_position = None
        best_match_box = None
        sticker_dft = self.get_dft(sticker)
        sticker_dft_mag = self.get_dft_magnitude(sticker_dft)

        # Loop over all possible top-left corners of the search window
        for y in range(0, image_height - sticker_height + 1, y_step):
            for x in range(0, image_width - sticker_width + 1, x_step):
                # Extract the current part of the image that the window covers
                window = image[y:y+sticker_height, x:x+sticker_width]
    
                window_dft = self.get_dft(window)
                window_dft_mag = self.get_dft_magnitude(window_dft)

                # Calculate MSE between the sticker and the window
                mse = np.mean((window_dft_mag - sticker_dft_mag) ** 2)
         
                # Update the best position if a new minimum MSE is found
                if mse < min_mse:
                    min_mse = mse
                    best_position = (y, x)
                    best_match_box = window.copy()

        return best_position, best_match_box
    
    
    def draw_bounding_box(self, sticker, image, top_left):
        """Draw a bounding box based on the shape of the sticker

        Args:
            sticker (np.array): sticker
            image (np.array): image
            top_left (tuple): top left coordinate (y,x) of the box
        """
        # Numpy has coordinate (height, width)
        y,x = top_left
        # Make a copy of the image
        img = image.copy()
        sticker_height = sticker.shape[0]
        sticker_width = sticker.shape[1]
        # OpenCV has coordinate: (width, height)
        image_window=cv.rectangle(img,(x,y),(x+sticker_width, y+sticker_height), (0,255,0), 4)
        io.imshow(image_window)
        
        
    def template_matching(self, image, sticker):
        
        result = feature.match_template(image, sticker)
        ij = np.unravel_index(np.argmax(result), result.shape)
        x, y = ij[::-1]
        
        fig = plt.figure(figsize=(10, 10))
        ax1 = plt.subplot(1, 3, 1)
        ax2 = plt.subplot(1, 3, 2)
        ax3 = plt.subplot(1, 3, 3, sharex=ax2, sharey=ax2)
        
        ax1.imshow(sticker, cmap=plt.cm.gray)
        ax1.set_axis_off()
        ax1.set_title('template')
        
        ax2.imshow(image, cmap=plt.cm.gray)
        ax2.set_axis_off()
        ax2.set_title('image')
        # highlight matched region
        hsticker, wsticker = sticker.shape
        rect = plt.Rectangle((x, y), wsticker, hsticker, edgecolor='r', facecolor='none')
        ax2.add_patch(rect)
        
        ax3.imshow(result)
        ax3.set_axis_off()
        ax3.set_title('`match_template`\nresult')
        # highlight matched region
        ax3.autoscale(False)
        ax3.plot(x, y, 'o', markeredgecolor='r', markerfacecolor='none', markersize=10)
        
        plt.show()
        