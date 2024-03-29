from .. import S_Match_point
from ..MultiCameraMatch import BaseMultiCameraMatchor

import numpy as np


class CenterRayIntersectMatchor(BaseMultiCameraMatchor):
    def __init__(self, *args):
        super().__init__(*args)
        self.ray_dict = {}

    @staticmethod
    def get_intersect_t(p1: np.ndarray, d1: np.ndarray, p2: np.ndarray, d2: np.ndarray) -> (float, float):
        p2_minus_p1 = p2 - p1
        d2_corss_d1 = np.cross(d1, d2)
        ord_squar_2 = np.linalg.norm(d2_corss_d1) ** 2
        t1 = np.dot(np.cross(p2_minus_p1, d1), d2_corss_d1) / ord_squar_2
        t2 = np.dot(np.cross(p2_minus_p1, d2), d2_corss_d1) / ord_squar_2
        return t1, t2

    @staticmethod
    def get_ray_position(p: np.ndarray, d: np.ndarray, t: float) -> np.ndarray:
        return p + (t * d)

    def match_content(self, idx: int, predict_result: S_Match_point) -> S_Match_point:
        predict_result_in_camera_coord = self.convert_predict_to_camera_coord(idx, predict_result)
        classandid_predict_result = np.nonzero(predict_result)
        classandid_baseline = np.nonzero(self.baseline_result)

        camera_position_baseline = self.baseline_camera_position
        camera_position_predict = self.camera_position_dict[idx]

        matched_baseline_classandid = {}
        for i_predict in range(len(classandid_predict_result[0]) // 4):
            class_predict = classandid_predict_result[0][i_predict * 4]
            id_predict = classandid_predict_result[1][i_predict * 4]
            coord_predict = predict_result_in_camera_coord[class_predict, id_predict]

            for i_base in range(len(classandid_baseline[0]) // 4):
                class_base = classandid_baseline[0][i_base * 4]
                id_base = classandid_baseline[1][i_base * 4]

                if class_base in matched_baseline_classandid.keys():
                    if id_base == matched_baseline_classandid[class_base]:
                        continue

                coord_base = self.baseline_result_in_camera[class_base, id_base]

                t1, t2 = self.get_intersect_t(
                    camera_position_baseline, coord_base, camera_position_predict, coord_predict
                )
                p1 = self.get_ray_position(camera_position_baseline, coord_base, t1)
                p2 = self.get_ray_position(camera_position_predict, coord_predict, t2)

                distance = np.linalg.norm(p2 - p1)
                if distance < self.max_distance:
                    if class_predict != class_base or id_predict != id_base:
                        predict_result[class_base, id_base] = predict_result[class_predict, id_predict]
                        predict_result[class_predict, id_predict, :] = 0

                    matched_baseline_classandid.update({class_base: id_base})
                else:
                    if class_predict != class_base or id_predict != id_base:
                        self.baseline_result[class_predict, id_predict] = predict_result[class_predict, id_predict]
                        self.baseline_result_in_camera[class_predict, id_predict] = \
                            predict_result_in_camera_coord[class_predict, id_predict]
                    else:
                        id_loop = id_predict
                        d_i = 1
                        while (id_loop + d_i) in classandid_predict_result[1]:
                            if id_loop + d_i > predict_result.shape[1]:
                                id_loop = 0
                                d_i = 0
                            else:
                                d_i += 1

                        new_id = id_loop + d_i
                        predict_result[class_base, new_id] = predict_result[class_predict, id_predict]
                        self.baseline_result[class_base, new_id] = predict_result[class_predict, id_predict]

                        predict_result[class_predict, id_predict, :] = 0

                        self.baseline_result_in_camera[class_base, new_id] = \
                            predict_result_in_camera_coord[class_predict, id_predict]

        return predict_result
