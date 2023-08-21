import time
import torch
from PIL import Image
import multiprocessing

from transformers import ViTForImageClassification, ViTImageProcessor
from logger import logger_model_2, logger_model_2_rate
from request import Request

model_2_lock = multiprocessing.Lock()

class Model_2(multiprocessing.Process):
    def __init__(self, id, car_frames_list, draw_message_list, end_signal, to_monitor_rate):
        super().__init__()
        self.id = id
        self.car_frames_list = car_frames_list
        self.draw_message_list = draw_message_list
        self.end_signal = end_signal
        
        self.device = None
        self.model = None
        self.processor = None

        self.timer_logger_model_2 = time.time()
        self.to_monitor_rate = to_monitor_rate

    def run(self):
        self.device = torch.device("cuda:1")
        self.processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
        self.model = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224').to(self.device)

        self.end_signal.value += 1

        # if self.id == 1:
        #     thread_monitor_rate = threading.Thread(target=self.monitor_rate)
        #     thread_monitor_rate.start()

        print(f"[Model_2_{self.id}] start")
        logger_model_2.info(f"[Model_2_{self.id}] start")
        while True:
            time.sleep(0.01)
            # car_frame = None
            with model_2_lock:
                request = self.car_frames_list.get()
                if request == -1:
                    self.car_frames_list.put(-1) # put the end signal back
                    print(f"[Model_2_{self.id}] end")
                    logger_model_2.info(f"[Model_2_{self.id}] end")
                    self.end_signal.value -= 1
                    # print(f"[Model_2_{self.id}] self.end_signal.value: {self.end_signal.value}")
                    logger_model_2.info(f"[Model_2_{self.id}] self.end_signal.value: {self.end_signal.value}")
                    if self.end_signal.value == 0:
                        self.draw_message_list.put(-1)
                    break
                elif isinstance(request, int):
                    self.draw_message_list.put(request)
                    continue
                # frame = self.car_frames_list.pop(0)
                if time.time() - self.timer_logger_model_2 > 5:
                    # print(f"[Model_2_{self.id}] frame_filename: ", frame[1])
                    logger_model_2.info(f"[Model_2_{self.id}] frame_filename: {request.ids}, and car_frames_list: {self.car_frames_list.qsize()}")
                    self.timer_logger_model_2 = time.time()
            if isinstance(request, Request):
                self.process_image(request)

    def monitor_rate(self):
        rates = []
        sliding_window_size = 5
        last_car_frame = ""
        last_car_frames_list_len = 0
        while True:
            time.sleep(1e-6)
            with model_2_lock:
                if self.end_signal.value == 0:
                    break
                try: 
                    if (len(self.car_frames_list) > 0 and self.car_frames_list[-1][1] != last_car_frame) or len(self.car_frames_list) > last_car_frames_list_len:
                        self.to_monitor_rate.append(time.time())
                        last_car_frame = self.car_frames_list[-1][1]
                    last_car_frames_list_len = len(self.car_frames_list)
                except Exception as e:
                    # logger_model_2.warning(f"[Model_2_{self.id}] {e}, and car_frames_list[-1]: {self.car_frames_list[-1]}, and last_car_frame: {last_car_frame}")
                    ...

                if len(self.to_monitor_rate) > 1:
                    rate = round((len(self.to_monitor_rate) - 1) / (self.to_monitor_rate[-1] - self.to_monitor_rate[0]), 3)
                    rates.append(rate)
                    if len(rates) > sliding_window_size:
                        rates.pop(0)
                    total_weight = sum(range(1, len(rates) + 1))
                    weighted_sum = sum((i + 1) * rate for i, rate in enumerate(rates))
                    moving_average = round(weighted_sum / total_weight, 3)
                    # print(f"[Model_2_{self.id}] rate: {moving_average}")
                    logger_model_2.info(f"[Model_2_{self.id}] rate: {moving_average}")
                    logger_model_2_rate.info(f"{moving_average}")
                    self.to_monitor_rate[:] = self.to_monitor_rate[-1:]
    
    def process_image(self, request):
        image_array, box = request.data, request.box
        image = Image.fromarray(image_array)
        box = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        cropped_image = image.crop(box)

        inputs = self.processor(images=cropped_image, return_tensors="pt")
        inputs = {key: val.to(self.device) for key, val in inputs.items()}  # move input data to GPU

        with torch.no_grad():  # execute model inference, make sure we do not compute gradients
            outputs = self.model(**inputs)

        logits = outputs.logits
        predicted_class_idx = logits.argmax(-1).item()
        predicted_class = self.model.config.id2label[predicted_class_idx]

        # Calculate score
        score = torch.softmax(logits, dim=-1)[0][predicted_class_idx].item()        

        # import request
        # self.draw_message_list.append(Request(...))
        label = f"{predicted_class}: {100 * score:.0f}%"
        
        request_copy = request.copy()
        request_copy.label = label

        self.draw_message_list.put(request_copy)

        del image, cropped_image, inputs, outputs, logits, predicted_class_idx, predicted_class, score, label

        return
    