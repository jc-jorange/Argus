import numpy as np

from lib.matchor import BaseMatchor, S_Match_point


class BaseMultiCameraMatchor(BaseMatchor):

    @staticmethod
    def get_point_in_camera_coord(k: np.ndarray, p: np.ndarray) -> np.ndarray:
        # p:[x, y]
        k = np.matrix(k)
        p = np.concatenate((p.T, np.array([[1]])))  # concatenate [u,v]T to [u,v,1]T
        return k.I * p

    def convert_predict_to_camera_coord(self, camera_id, predict_result):
        intrinsic_parameters = self.intrinsic_parameters_dict[camera_id]
        predict_result_in_camera_coord = np.zeros(
            (predict_result.shape[0], predict_result.shape[1], predict_result.shape[2] + 2)  # [class,id,[x,y,z,1]]
        )

        classandid_result = np.nonzero(predict_result)

        for i in range(len(classandid_result[0]) // 4):
            class_predict = classandid_result[0][i * 4]
            id_predict = classandid_result[1][i * 4]
            coord_predict = predict_result[class_predict, id_predict]

            coord_b_in_camera_coord = self.get_point_in_camera_coord(intrinsic_parameters, coord_predict)
            predict_result_in_camera_coord[class_predict, id_predict] = coord_b_in_camera_coord.T

        return predict_result_in_camera_coord

    def get_baseline_result(self) -> S_Match_point:
        super().get_baseline_result()
        return self.convert_predict_to_camera_coord(0, self.baseline_result)
