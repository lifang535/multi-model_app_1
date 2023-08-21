import time
import torch
from PIL import Image
import multiprocessing

from transformers import ViTForImageClassification, ViTImageProcessor
from logger import logger_model_3, logger_model_3_rate
from request import Request

model_3_lock = multiprocessing.Lock()

class Model_3(multiprocessing.Process):
    def __init__(self, id, person_frames_list, draw_message_list, end_signal, to_monitor_rate):
        super().__init__()
        self.id = id
        self.person_frames_list = person_frames_list
        self.draw_message_list = draw_message_list
        self.end_signal = end_signal
        
        self.device = None
        self.model = None
        self.processor = None
        self.gender_classifier = None

        self.timer_logger_model_3 = time.time()
        self.to_monitor_rate = to_monitor_rate

    def run(self):
        self.device = torch.device("cuda:0")
        self.model = ViTForImageClassification.from_pretrained('nateraw/vit-age-classifier').to(self.device)
        self.processor = ViTImageProcessor.from_pretrained('nateraw/vit-age-classifier')

        self.end_signal.value += 1

        # if self.id == 1:
        #     thread_monitor_rate = threading.Thread(target=self.monitor_rate)
        #     thread_monitor_rate.start()

        print(f"[Model_3_{self.id}] start")
        logger_model_3.info(f"[Model_3_{self.id}] start")
        while True:
            time.sleep(0.01)
            with model_3_lock:
                request = self.person_frames_list.get()
                if request == -1:
                    self.person_frames_list.put(-1) # put the end signal back
                    print(f"[Model_3_{self.id}] end")
                    logger_model_3.info(f"[Model_3_{self.id}] end")
                    self.end_signal.value -= 1
                    # print(f"[Model_3_{self.id}] self.end_signal.value: {self.end_signal.value}")
                    logger_model_3.info(f"[Model_3_{self.id}] self.end_signal.value: {self.end_signal.value}")
                    if self.end_signal.value == 0:
                        self.draw_message_list.put(-1)
                    break
                elif isinstance(request, int):
                    self.draw_message_list.put(request)
                    continue

                if time.time() - self.timer_logger_model_3 > 5:
                    logger_model_3.info(f"[Model_3_{self.id}] frame_filename: {request.ids}, and person_frames_list: {self.person_frames_list.qsize()}")
                    self.timer_logger_model_3 = time.time()
            if isinstance(request, Request):
                self.process_image(request)

    def monitor_rate(self):
        rates = []
        sliding_window_size = 5
        last_person_frame = ""
        last_person_frames_list_len = 0
        while True:
            time.sleep(1e-6)
            with model_3_lock:
                if self.end_signal.value == 0:
                    break
                try:
                    if (len(self.person_frames_list) > 0 and self.person_frames_list[-1][1] != last_person_frame) or len(self.person_frames_list) > last_person_frames_list_len:
                        self.to_monitor_rate.append(time.time())
                        last_person_frame = self.person_frames_list[-1][1]
                    last_person_frames_list_len = len(self.person_frames_list)
                except Exception as e:
                    # logger_model_3.warning(f"[Model_3_{self.id}] {e}, and person_frames_list[-1]: {self.person_frames_list[-1]}, and last_person_frame: {last_person_frame}")
                    ...

                if len(self.to_monitor_rate) > 1:
                    rate = round((len(self.to_monitor_rate) - 1) / (self.to_monitor_rate[-1] - self.to_monitor_rate[0]), 3)
                    rates.append(rate)
                    if len(rates) > sliding_window_size:
                        rates.pop(0)
                    total_weight = sum(range(1, len(rates) + 1))
                    weighted_sum = sum((i + 1) * rate for i, rate in enumerate(rates))
                    moving_average = round(weighted_sum / total_weight, 3)
                    # print(f"[Model_3_{self.id}] rate: {moving_average}")
                    logger_model_3.info(f"[Model_3_{self.id}] rate: {moving_average}")
                    logger_model_3_rate.info(f"{moving_average}")
                    self.to_monitor_rate[:] = self.to_monitor_rate[-1:]
    
    def process_image(self, request):
        image_array, box = request.data, request.box
        image = Image.fromarray(image_array)

        # Validate box coordinates
        box = [int(coord) for coord in box]
        if not (0 <= box[0] < box[2] < image.width and 0 <= box[1] < box[3] < image.height):
            raise ValueError("Invalid box coordinates. Please ensure the box is within the image boundaries.")

        # Crop image based on the box coordinates
        cropped_image = image.crop(box)

        # Age classification
        inputs = self.processor(cropped_image, return_tensors='pt').to(self.device) # TODO: move to GPU
        with torch.no_grad():
            output = self.model(**inputs)

        # Predicted Class probabilities
        proba = output.logits.softmax(1)

        # Predicted Classes
        preds = proba.argmax(1)

        # Extract gender and age information
        age = preds.item()
        age = self.model.config.id2label[age]

        # score = (gender_results[0]['score'] + proba.max().item()) / 2  # Average score
        score = proba.max().item()

        # Return gender, age, and average score as a string
        result_str = f"person in {age}"

        label = f"{result_str}: {100 * score:.0f}%"

        request_copy = request.copy()
        request_copy.label = label

        self.draw_message_list.put(request_copy)

        del image, cropped_image, inputs, output, proba, preds, result_str, score, label

        return
    