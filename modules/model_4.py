import os
import time
import threading
import multiprocessing
from PIL import Image, ImageDraw, ImageFont

from logger import logger_model_4, logger_model_4_rate

model_4_lock = multiprocessing.Lock()

# Load a font with a larger size
font_size = 16
font = ImageFont.truetype("../fonts/times new roman.ttf", font_size)

class Model_4(multiprocessing.Process):
    def __init__(self, id, draw_message_list, frame_files_to_be_processed, end_signal, to_monitor_rate, table):
        super().__init__()
        self.id = id
        self.draw_message_list = draw_message_list
        self.end_signal = end_signal

        # self.lock = threading.Lock()
        self.frame_files_to_be_processed = frame_files_to_be_processed

        self.timer_logger_model_4 = time.time()
        self.to_monitor_rate = to_monitor_rate

        self.table = {} # dict() {} table
        # self.table = {
        #     "reuqest_id": [request, request...], # until len(vlue) == request.sub_requests[1]
        #     ...
        # }

    def run(self):
        print(f"[Model_4_{self.id}] start")
        logger_model_4.info(f"[Model_4_{self.id}] start")

        self.end_signal.value += 1

        # if self.id == 1:
        #     # thread_monitor_rate = threading.Thread(target=self.monitor_rate)
        #     thread_monitor_table = threading.Thread(target=self.monitor_table)
        #     # thread_monitor_rate.start()
        #     thread_monitor_table.start()

        threads = []

        while True:
            time.sleep(0.01)
            with model_4_lock:
                request = self.draw_message_list.get()
                if request == -1:
                    # if not self.draw_message_list.qsize() == 0:
                    self.draw_message_list.put(-1) # put the end signal back
                    self.end_signal.value -= 1

                    logger_model_4.info(f"[Model_4_{self.id}] self.draw_message_list: {self.draw_message_list.qsize()}")
                    print(f"[Model_4_{self.id}] end")
                    logger_model_4.info(f"[Model_4_{self.id}] end")
                    # print(f"[Model_4_{self.id}] self.end_signal.value: {self.end_signal.value}")
                    logger_model_4.info(f"[Model_4_{self.id}] self.end_signal.value: {self.end_signal.value}")
                    if self.end_signal.value == 0:
                        self.frame_files_to_be_processed.append(-1)
                    break

                elif isinstance(request, int):
                    # continue
                    # print(f"[Model_4_{self.id}] video_{self.draw_message_list[0]} is being processed")
                    # video_id = self.draw_message_list.pop(0)
                    for thread in threads:
                        thread.join()
                    threads = []
                    self.frame_files_to_be_processed.append(request)
                    continue
                
                # [1, 2, 3] -> [1, 2]
                if time.time() - self.timer_logger_model_4 > 5:
                    # print(f"[Model_4_{self.id}] {draw_message[0]} is being processed, and draw_message_list: {len(self.draw_message_list)}")
                    logger_model_4.info(f"[Model_4_{self.id}] {request.ids} is being processed, and draw_message_list: {self.draw_message_list.qsize()}")
                    self.timer_logger_model_4 = time.time()
                
                # self.process_draw_message(draw_message)
                if f"{request.ids[0]}-{request.ids[1]}]" in self.table:
                    self.table[f"{request.ids[0]}-{request.ids[1]}]"].append(request)
                else:
                    self.table[f"{request.ids[0]}-{request.ids[1]}]"] = [request]

                if len(self.table[f"{request.ids[0]}-{request.ids[1]}]"]) >= request.sub_requests[1]:
                    thread = threading.Thread(target=self.process_requests, args=(self.table[f"{request.ids[0]}-{request.ids[1]}]"],))
                    threads.append(thread)
                    thread.start()
                    if len(threads) > 16:
                        threads[0].join()
                        threads.pop(0)
                    self.table.pop(f"{request.ids[0]}-{request.ids[1]}]")

                # if request.ids[1] == request.sub_requests[0] and request.ids[2] == request.sub_requests[1]:
                #     for thread in threads:
                #         thread.join()
                #     threads = []
                #     self.frame_files_to_be_processed.append(request.ids[0])
                #     self.frame_files_to_be_processed.append(request.ids[0])
    
    def process_requests(self, requests):
        for request in requests:
            self.process_draw_message(request)
        
    def monitor_table(self):
        threads = []
        while True:
            time.sleep(0.01)
            if self.end_signal.value == 0:
                    break
            for key, value in self.table.items():
                # print(f"key: {key} and value: {value}")
                if time.time() - value[0] > 1:
                    self.table.pop(key)
                    for draw_message in value[1:]:
                        # print("-----------------------", draw_message)
                        # self.process_draw_message(draw_message)
                        thread = threading.Thread(target=self.process_draw_message, args=(draw_message,))
                        threads.append(thread)
                        thread.start()
                        if len(threads) > 64:
                            threads[0].join()
                            threads.pop(0)
                    break

    # def monitor_rate(self):
    #     rates = []
    #     sliding_window_size = 10
    #     last_draw_message = ""
    #     last_draw_messages_list_len = 0
    #     while True:
    #         time.sleep(1e-6)
    #         with model_4_lock:
    #             if self.end_signal.value == 0:
    #                 break
    #             try:
    #                 if (len(self.draw_message_list) > 0 and self.draw_message_list[-1][0] != last_draw_message) or len(self.draw_message_list) > last_draw_messages_list_len:
    #                     self.to_monitor_rate.append(time.time())
    #                     last_draw_message = self.draw_message_list[-1][0]
    #                 last_draw_messages_list_len = len(self.draw_message_list)
    #             except Exception as e:
    #                 # logger_model_4.warning(f"[Model_4_{self.id}] {e}, and draw_message_list[-1]: {self.draw_message_list[-1]}, and last_draw_message: {last_draw_message}")
    #                 ...

    #             if len(self.to_monitor_rate) > 1:
    #                 rate = round((len(self.to_monitor_rate) - 1) / (self.to_monitor_rate[-1] - self.to_monitor_rate[0]), 3)
    #                 rates.append(rate)
    #                 if len(rates) > sliding_window_size:
    #                     rates.pop(0)
    #                 total_weight = sum(range(1, len(rates) + 1))
    #                 weighted_sum = sum((i + 1) * rate for i, rate in enumerate(rates))
    #                 moving_average = round(weighted_sum / total_weight, 3)
    #                 # print(f"[Model_4_{self.id}] rate: {moving_average}")
    #                 logger_model_4.info(f"[Model_4_{self.id}] rate: {moving_average}")
    #                 logger_model_4_rate.info(f"{moving_average}")
    #                 self.to_monitor_rate[:] = self.to_monitor_rate[-1:]

    def process_draw_message(self, request):
        label, box, image_array = request.label, request.box, request.data # output_frames_video_1/frame_6.jpg
        # print(request.request_id)
        # video_id = request.request_id.split('-')[0].split('_')[1]
        # frame_id = request.request_id.split('-')[-2]
        output_frame_filename = f"output_frames_video_{request.ids[0]}/frame_{request.ids[1]}.jpg"

        # Draw bounding boxes on the image
        try:
            # image = Image.open(frame_filename)
            if os.path.exists(output_frame_filename): # TODO: frame_filename 的命名规则
                image = Image.open(output_frame_filename)
            else:
                image = Image.fromarray(image_array)
                os.makedirs(os.path.dirname(output_frame_filename), exist_ok=True)
                image.save(output_frame_filename)
                
            draw = ImageDraw.Draw(image)

            # label_text = f"{label} {round(score * 100, 1)}%"
            if not "person" in label:
            # if label == "car":
                draw.rectangle(box, outline="green", width=3)
                draw.text((box[0], box[1]), label, fill="red", font=font)
            elif label == "person":
                draw.rectangle(box, outline="blue", width=3)
                draw.text((box[0], box[1]), label, fill="yellow", font=font)
            else:
                draw.rectangle(box, outline="blue", width=3)
                draw.text((box[0], box[1]), label, fill="yellow", font=font)

            # Save the annotated image
            image.save(output_frame_filename)
            
        except Exception as e:
            logger_model_4.error(f"[Model_4_{self.id}] {e}")
        
