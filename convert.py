from tools import utils_image
import numpy as np
from models import YOLO
import config
from tools import utils

from operator import itemgetter


class Yolo4(object):

    def __init__(self, model_path, weights_path, gpu_num=1):
        self.score = config.score
        self.iou = config.iou
        self.weights_path = weights_path
        self.model_path = model_path
        self.gpu_num = gpu_num
        self.colors = utils_image.get_random_colors(len(config.classes_names))
        # self.sess = K.get_session()
        self.yolo4_model = YOLO()()
        # self.yolo4_model.summary()
        self.convertor()

    def convertor(self):

        weights_file = open(self.weights_path, 'rb')

        convs_to_load = []
        bns_to_load = []
        for i in range(len(self.yolo4_model.layers)):
            layer_name = self.yolo4_model.layers[i].name

            layer_name = utils.tf_layer_name_compat(layer_name)

            if layer_name.startswith('conv2d_'):
                convs_to_load.append((int(layer_name[7:]), i))
            if layer_name.startswith('batch_normalization_'):
                bns_to_load.append((int(layer_name[20:]), i))

        convs_sorted = sorted(convs_to_load, key=itemgetter(0))
        bns_sorted = sorted(bns_to_load, key=itemgetter(0))

        bn_index = 0
        for i in range(len(convs_sorted)):
            print('Converting ', i)
            if i == 93 or i == 101 or i == 109:
                # no bn, with bias
                weights_shape = self.yolo4_model.layers[convs_sorted[i][1]].get_weights()[0].shape
                bias_shape = self.yolo4_model.layers[convs_sorted[i][1]].get_weights()[0].shape[3]
                filters = bias_shape
                size = weights_shape[0]
                darknet_w_shape = (filters, weights_shape[2], size, size)
                weights_size = np.product(weights_shape)
                # exit()
                conv_bias = np.ndarray(
                    shape=(filters,),
                    dtype='float32',
                    buffer=weights_file.read(filters * 4))
                conv_weights = np.ndarray(
                    shape=darknet_w_shape,
                    dtype='float32',
                    buffer=weights_file.read(weights_size * 4))
                conv_weights = np.transpose(conv_weights, [2, 3, 1, 0])
                # conv_weights = tf.convert_to_tensor(conv_weights, dtype='float32')
                # conv_bias = tf.convert_to_tensor(conv_bias, dtype='float32')
                self.yolo4_model.layers[convs_sorted[i][1]].set_weights([conv_weights, conv_bias])
            else:
                # with bn, no bias
                weights_shape = self.yolo4_model.layers[convs_sorted[i][1]].get_weights()[0].shape
                size = weights_shape[0]
                bn_shape = self.yolo4_model.layers[bns_sorted[bn_index][1]].get_weights()[0].shape
                filters = bn_shape[0]
                darknet_w_shape = (filters, weights_shape[2], size, size)
                weights_size = np.product(weights_shape)

                conv_bias = np.ndarray(
                    shape=(filters,),
                    dtype='float32',
                    buffer=weights_file.read(filters * 4))
                bn_weights = np.ndarray(
                    shape=(3, filters),
                    dtype='float32',
                    buffer=weights_file.read(filters * 12))


                bn_weight_list = [
                    bn_weights[0],  # scale gamma
                    conv_bias,  # shift beta
                    bn_weights[1],  # running mean
                    bn_weights[2]  # running var
                ]
                # bn_weight_list = tf.convert_to_tensor(bn_weight_list, dtype='float32')
                self.yolo4_model.layers[bns_sorted[bn_index][1]].set_weights(bn_weight_list)

                # print(weights_shape, i, weights_size * 4)
                # exit()
                conv_weights = np.ndarray(
                    shape=darknet_w_shape,
                    dtype='float32',
                    buffer=weights_file.read(weights_size * 4))
                conv_weights = np.transpose(conv_weights, [2, 3, 1, 0])
                self.yolo4_model.layers[convs_sorted[i][1]].set_weights([conv_weights])

                bn_index += 1

        weights_file.close()

        self.yolo4_model.save(self.model_path)

        # if self.gpu_num>=2:
        #     self.yolo4_model = multi_gpu_model(self.yolo4_model, gpus=self.gpu_num)
        # self.sess.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('-w', '--weights', type=str, help='input weights path', default='model_data/train_net_best.weights')
    parser.add_argument('-m', '--model', type=str, help='input h5 model path', default='model_data/train_net_best.h5')

    args = parser.parse_args()
    weights_path = args.weights
    model_path = args.model

    yolo4_model = Yolo4(model_path, weights_path)
    print('Converting finished !')
