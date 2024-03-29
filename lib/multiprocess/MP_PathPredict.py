import time
import traceback
from typing import Type
from collections import defaultdict
from multiprocessing import queues

from ..multiprocess import BaseProcess
from .SharedMemory import EQueueType
from lib.predictor import BasePredictor, predictor_factory
from ..postprocess.utils import write_result as wr
from lib.tracker.utils.utils import *


class PathPredictProcess(BaseProcess):
    prefix = 'Argus-SubProcess-PathPredictProcess_'
    dir_name = 'predict'
    log_name = 'Path_Predict_Log'
    save_type = [wr.E_text_result_type.raw]

    def __init__(self,
                 *args,
                 **kwargs
                 ):
        super().__init__(*args, **kwargs)

        self.current_track_result = None
        self.current_predict_result = None
        self.all_predict_result = {}

        self.predictor = predictor_factory[self.opt.predictor_name]()

    def run_action(self) -> None:
        self.logger.info('Start predicting')
        super(PathPredictProcess, self).run_action()
        self.predictor.time_0 = time.perf_counter()
        frame = 0
        subframe = -1
        track_queue = self.shared_container.queue_dict[EQueueType.TrackerResultSend]
        predict_queue = self.shared_container.queue_dict[EQueueType.PredictResultSend]
        while self.shared_container.b_input_loading.value:
            t1 = time.perf_counter()
            try:
                self.current_track_result = track_queue.get(block=False)
                frame += 1
                subframe = 0
                self.current_predict_result = self.predictor.set_new_base(self.current_track_result)
                self.all_predict_result[frame] = {}
            except queues.Empty:
                subframe += 1
                self.current_predict_result = self.predictor.get_predicted_position(time.perf_counter())
                if isinstance(self.current_predict_result, torch.Tensor):
                    self.current_predict_result = self.current_predict_result.numpy()

            predict_queue.put(self.current_predict_result)

            if isinstance(self.current_predict_result, np.ndarray):
                result_each_subframe = {}
                result_class = defaultdict(dict)
                result_id = {}
                valid_position = np.nonzero(self.current_predict_result)
                target_num = len(valid_position[0]) // 4
                for i in range(target_num):
                    cls = valid_position[0][i * 4]
                    target_id = valid_position[1][i * 4]
                    x_position = valid_position[2][(i * 4)]
                    y_position = valid_position[2][(i * 4) + 1]
                    x = self.current_predict_result[cls][target_id][x_position]
                    y = self.current_predict_result[cls][target_id][y_position]
                    result_id[target_id] = ((x, y, 0, 0), 1.0)
                    result_class[cls].update(result_id)

                t2 = time.perf_counter()
                fps = 1 / (t2 - t1)
                result_each_subframe[subframe] = (result_class, fps)
                self.all_predict_result[frame].update(result_each_subframe)

        while predict_queue.qsize() > 0:
            predict_queue.get(block=False)

    def run_end(self) -> None:
        self.all_frame_results = self.all_predict_result
        super().run_end()

        self.logger.info('-'*5 + 'Predict Finished' + '-'*5)
