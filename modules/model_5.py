import os
import time
import threading
import multiprocessing

import cv2
from logger import logger_model_5, logger_model_5_rate, logger_latency

model_5_lock = multiprocessing.Lock()

class Model_5(multiprocessing.Process):
    def __init__(self, id, frame_files_to_be_processed, end_signal, to_monitor_rate):
        super().__init__()
        self.id = id
        self.frame_files_to_be_processed = frame_files_to_be_processed
        self.end_signal = end_signal

        self.timer_logger_model_5 = time.time()
        self.to_monitor_rate = to_monitor_rate
        self.threading_lock = threading.Lock()

    def run(self):
        self.end_signal.value += 1

        # if self.id == 1:
        #     thread_monitor_rate = threading.Thread(target=self.monitor_rate)
        #     thread_monitor_rate.start()

        print(f"[Model_5_{self.id}] start")
        logger_model_5.info(f"[Model_5_{self.id}] start")
        while True:
            time.sleep(1)
            if time.time() - self.timer_logger_model_5 > 5:
                logger_model_5.info(f"[Model_5_{self.id}] frame_files_to_be_processed: {self.frame_files_to_be_processed}")
                self.timer_logger_model_5 = time.time()
            if len(self.frame_files_to_be_processed) > 0:
                try:
                    if self.frame_files_to_be_processed[0] == -1:
                        print(f"[Model_5_{self.id}] end")
                        logger_model_5.info(f"[Model_5_{self.id}] end")
                        self.end_signal.value -= 1
                        # print(f"[Model_5_{self.id}] self.end_signal.value: {self.end_signal.value}")
                        logger_model_5.info(f"[Model_5_{self.id}] self.end_signal.value: {self.end_signal.value}")
                        break
                    for video_id in self.frame_files_to_be_processed:
                        if video_id != -1 and self.frame_files_to_be_processed.count(video_id) > 1:
                            with self.threading_lock:
                                self.frame_files_to_be_processed.remove(video_id)
                                self.frame_files_to_be_processed.remove(video_id)
                            frame_filename = f"output_frames_video_{video_id}"
                            self.process_video(frame_filename)
                            continue
                    
                except Exception as e:
                    logger_model_5.error(f"[Model_5_{self.id}] {e}")

    def monitor_rate(self):
        rates = []
        sliding_window_size = 1
        last_frame_file = 0
        last_frame_files_len = 0
        while True:
            time.sleep(1e-6)
            with model_5_lock and self.threading_lock:
                if self.end_signal.value == 0:
                    break
                try:
                    if (len(self.frame_files_to_be_processed) > 0 and self.frame_files_to_be_processed[-1] != last_frame_file) or len(self.frame_files_to_be_processed) > last_frame_files_len:
                        self.to_monitor_rate.append(time.time())
                        last_frame_file = self.frame_files_to_be_processed[-1]
                    last_frame_files_len = len(self.frame_files_to_be_processed)
                except Exception as e:
                    logger_model_5.warning(f"[Model_5_{self.id}] {e}, and frame_files_to_be_processed[-1]: {self.frame_files_to_be_processed[-1]}, and last_frame_file: {last_frame_file}")

                if len(self.to_monitor_rate) > 1:
                    rate = round((len(self.to_monitor_rate) - 1) / (self.to_monitor_rate[-1] - self.to_monitor_rate[0]), 3)
                    rates.append(rate)
                    if len(rates) > sliding_window_size:
                        rates.pop(0)
                    total_weight = sum(range(1, len(rates) + 1))
                    weighted_sum = sum((i + 1) * rate for i, rate in enumerate(rates))
                    moving_average = round(weighted_sum / total_weight, 3)
                    # print(f"[Model_5_{self.id}] rate: {moving_average}")
                    logger_model_5.info(f"[Model_5_{self.id}] rate: {moving_average}")
                    logger_model_5_rate.info(f"{moving_average}")
                    self.to_monitor_rate[:] = self.to_monitor_rate[-1:]

    def process_video(self, frame_filename):
        # frame_filename = f"output_{frame_filename}"
        print(f"[Model_5_{self.id}] frame_filename: ", frame_filename)
        logger_model_5.info(f"[Model_5_{self.id}] frame_filename: {frame_filename}")
        video_id = frame_filename.split('_')[-1]
        # Input video file path
        input_video_path = f"../input_videos/video_{video_id}.mp4"
        print(f"[Model_5_{self.id}] input_video_path: ", input_video_path)
        logger_model_5.info(f"[Model_5_{self.id}] input_video_path: {input_video_path}")

        # Output directory for frames
        output_frames_dir = frame_filename
        output_video_dir = "../output_videos"
        os.makedirs(output_video_dir, exist_ok=True)

        # Output video file path
        output_video_path = f"../output_videos/processed_video_{video_id}.mp4"
        print(f"[Model_5_{self.id}] output_video_path: ", output_video_path)
        logger_model_5.info(f"[Model_5_{self.id}] output_video_path: {output_video_path}")
        
        # Open the video file
        cap = cv2.VideoCapture(input_video_path)

        # Get video properties
        frame_width = int(cap.get(3))
        frame_height = int(cap.get(4))
        fps = int(cap.get(5))

        # Define the codec and create a VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Combine the processed frames back into a video
        output_frames = [os.path.join(output_frames_dir, filename) for filename in os.listdir(output_frames_dir)]
        output_frames.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
        output_video = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

        for frame_path in output_frames:
            frame = cv2.imread(frame_path)
            output_video.write(frame)
        
        # Release the output video writer
        output_video.release()

        logger_latency.info(f"video_{video_id} end at {time.time()}")
        
        # Clean up: Delete the processed frames
        for frame_path in output_frames:
            os.remove(frame_path)

        # Clean up: Delete the frames directory
        os.rmdir(output_frames_dir)
        
        print(f"[Model_5_{self.id}] {input_video_path} processed successfully")
        logger_model_5.info(f"[Model_5_{self.id}] {input_video_path} processed successfully")
