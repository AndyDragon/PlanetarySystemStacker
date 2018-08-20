import glob
from math import ceil
from time import time

import matplotlib.pyplot as plt
from numpy import arange, amax

from align_frames import AlignFrames
from configuration import Configuration
from exceptions import WrongOrderingError
from frames import Frames
from miscellaneous import local_contrast
from rank_frames import RankFrames


class AlignmentPoints(object):
    def __init__(self, configuration, frames, rank_frames, align_frames):
        self.configuration = configuration
        self.frames = frames
        self.rank_frames = rank_frames
        self.align_frames = align_frames
        self.alignment_boxes = None
        self.alignment_boxes_coordinates = None
        self.alignment_boxes_structure = None
        self.alignment_boxes_max_brightness = None
        self.alignment_boxes_number = None
        self.alignment_points = None
        self.alignment_points_number = None

        self.average_frame_number = max(ceil(frames.number * configuration.average_frame_percent / 100.), 1)
        self.align_frames.average_frame(
            [self.frames.frames_mono[i] for i in self.rank_frames.quality_sorted_indices[:self.average_frame_number]],
            [self.align_frames.frame_shifts[i] for i in
             self.rank_frames.quality_sorted_indices[:self.average_frame_number]])

    def create_alignment_points(self, step_size, box_size):
        mean_frame = self.align_frames.mean_frame
        mean_frame_shape = mean_frame.shape
        box_size_half = int(box_size / 2)
        self.alignment_boxes = []
        self.alignment_boxes_coordinates = []
        self.alignment_boxes_structure = []
        self.alignment_boxes_max_brightness = []

        for y in arange(step_size, mean_frame_shape[0] - step_size, step_size, dtype=int):
            for x in arange(step_size, mean_frame_shape[1] - step_size, step_size, dtype=int):
                box = mean_frame[y - box_size_half:y + box_size_half, x - box_size_half:x + box_size_half]
                self.alignment_boxes.append(box)
                self.alignment_boxes_coordinates.append([y, x])
                stride = 1
                self.alignment_boxes_structure.append(local_contrast(box, stride))
                self.alignment_boxes_max_brightness.append(amax(box))
        self.alignment_boxes_number = len(self.alignment_boxes)
        structure_max = max(self.alignment_boxes_structure)
        self.alignment_boxes_structure = [item / structure_max for item in self.alignment_boxes_structure]

    def select_alignment_points(self, structure_threshold, brightness_threshold):
        if self.alignment_boxes == None:
            raise WrongOrderingError("Attempt to select alignment points before alignment boxes are created")
        self.alignment_points = [item for (index, item) in enumerate(self.alignment_boxes_coordinates) if
                                 self.alignment_boxes_structure[index] > structure_threshold and
                                 self.alignment_boxes_max_brightness[index] > brightness_threshold]
        self.alignment_points_number = len(self.alignment_points)


if __name__ == "__main__":
    names = glob.glob('Images/2012*.tif')
    print(names)
    configuration = Configuration()
    try:
        frames = Frames(names, type='image')
        print("Number of images read: " + str(frames.number))
        print("Image shape: " + str(frames.shape))
    except Exception as e:
        print("Error: " + e.message)
        exit()

    rank_frames = RankFrames(frames, configuration)
    start = time()
    rank_frames.frame_score()
    end = time()
    print('Elapsed time in ranking images: {}'.format(end - start))
    print("Index of maximum: " + str(rank_frames.frame_ranks_max_index))
    print("Frame scores: " + str(rank_frames.frame_ranks))
    print("Frame scores (sorted): " + str([rank_frames.frame_ranks[i] for i in rank_frames.quality_sorted_indices]))
    print("Sorted index list: " + str(rank_frames.quality_sorted_indices))

    align_frames = AlignFrames(frames, rank_frames, configuration)
    start = time()
    (x_low_opt, x_high_opt, y_low_opt, y_high_opt) = align_frames.select_alignment_rect(
        configuration.alignment_rectangle_scale_factor)
    end = time()
    print('Elapsed time in computing optimal alignment rectangle: {}'.format(end - start))
    print("optimal alignment rectangle, x_low: " + str(x_low_opt) + ", x_high: " + str(x_high_opt) + ", y_low: " + str(
        y_low_opt) + ", y_high: " + str(y_high_opt))
    frame = align_frames.frames_mono[align_frames.frame_ranks_max_index].copy()
    frame[y_low_opt, x_low_opt:x_high_opt] = frame[y_high_opt - 1, x_low_opt:x_high_opt] = 255
    frame[y_low_opt:y_high_opt, x_low_opt] = frame[y_low_opt:y_high_opt, x_high_opt - 1] = 255
    plt.imshow(frame, cmap='Greys_r')
    plt.show()

    start = time()
    align_frames.align_frames()
    end = time()
    print('Elapsed time in aligning all frames: {}'.format(end - start))
    print("Frame shifts: " + str(align_frames.frame_shifts))
    print("Intersection: " + str(align_frames.intersection_shape))

    start = time()
    alignment_points = AlignmentPoints(configuration, frames, rank_frames, align_frames)
    end = time()
    print('Elapsed time in computing average frame: {}'.format(end - start))
    print("Average frame computed from the best " + str(alignment_points.average_frame_number) + " frames.")
    plt.imshow(align_frames.mean_frame, cmap='Greys_r')
    plt.show()

    step_size = configuration.alignment_box_step_size
    box_size = configuration.alignment_box_size
    start = time()
    alignment_points.create_alignment_points(step_size, box_size)
    end = time()
    print('Elapsed time in alignment box creation: {}'.format(end - start))
    print("Number of alignment boxes created: " + str(alignment_points.alignment_boxes_number))

    structure_threshold = configuration.alignment_point_structure_threshold
    brightness_threshold = configuration.alignment_point_brightness_threshold
    print("Selection of alignment points, structure threshold: " + str(
        structure_threshold) + ", brightness threshold: " + str(brightness_threshold))
    start = time()
    alignment_points.select_alignment_points(structure_threshold, brightness_threshold)
    end = time()
    print('Elapsed time in alignment point selection: {}'.format(end - start))
    print("Number of alignment points selected: " + str(alignment_points.alignment_points_number))

    start = time()
    frame = align_frames.frames_mono[align_frames.frame_ranks_max_index].copy()
    cross_half_len = 5
    for [y_center, x_center] in alignment_points.alignment_points:
        for y in range(y_center - cross_half_len, y_center + cross_half_len):
            frame[y, x_center] = 255
        for x in range(x_center - cross_half_len, x_center + cross_half_len):
            frame[y_center, x] = 255
    end = time()
    print('Elapsed time in drawing alignment points: {}'.format(end - start))
    plt.imshow(frame, cmap='Greys_r')
    plt.show()
