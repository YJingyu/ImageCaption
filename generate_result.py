# -*- coding: utf-8 -*-
# @Author: lc
# @Date:   2017-09-17 00:22:17
# @Last Modified by:   lc
# @Last Modified time: 2017-09-17 16:07:09

import sys
import math
import hashlib
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
os.environ["CUDA_VISIBLE_DEVICES"] = '0' # use the second GPU
from shutil import copyfile
from datetime import datetime

import json
import jieba
import tensorflow as tf

import configuration
import inference_wrapper
from inference_utils import caption_generator
from inference_utils import vocabulary


checkpoint_path = '../aichallenge_model_inception/train/'
vocab_file = '../data/aichallenge/TFRecordFile/word_counts.txt'
test_img_dir = '../data/aichallenge/test1500png/'
result_json_file = '../data/aichallenge/result/result{0}.json'.format(datetime.now().strftime("%Y%m%d%H%M%S"))

FLAGS = tf.flags.FLAGS
tf.flags.DEFINE_string("checkpoint_path", checkpoint_path, 
                       "Model checkpoint file or directory containing a model checkpoint file.")
tf.flags.DEFINE_string("vocab_file", vocab_file, "Text file containing the vocabulary.")
tf.flags.DEFINE_string("test_img_dir", test_img_dir, 
                       "directory containing images for test")
tf.flags.DEFINE_string("result_json_file", result_json_file, "Text file containing the captions of test images generated by the model")

tf.logging.set_verbosity(tf.logging.INFO)


def main(_):
    g = tf.Graph()
    with g.as_default():
        model = inference_wrapper.InferenceWrapper()
        restore_fn = model.build_graph_from_config(configuration.ModelConfig(), FLAGS.checkpoint_path)
    g.finalize()

    # Create the vocabulary.
    vocab = vocabulary.Vocabulary(FLAGS.vocab_file)

    with tf.Session(graph=g) as sess:
        # Load the model from checkpoint.
        restore_fn(sess)

        # Prepare the caption generator. Here we are implicitly using the default
        # beam search parameters. See caption_generator.py for a description of the
        # available beam search parameters.
        count, result = 0, []
        generator = caption_generator.CaptionGenerator(model, vocab)
        filenames = os.listdir(FLAGS.test_img_dir)
        for filename in filenames:
            count += 1
            with open(FLAGS.test_img_dir + filename, "rb") as f:
                image = f.read()
            captions = generator.beam_search(sess, image)
            sentence = [vocab.id_to_word(w) for w in captions[0].sentence[1:-1]]
            sentence = ''.join(sentence)
            image_id = int(int(hashlib.sha256(filename.split('.')[0].encode('utf8')).hexdigest(), 16) % sys.maxsize)
            result.append({'caption': sentence, 'image_id':image_id})
            if count % 100 == 0:
                print('finish generating caption for {0} images'.format(count))
        print('finish totally {0} images'.format(count))
        with open(FLAGS.result_json_file, encoding = 'utf8', mode = 'w') as f:
            json.dump(result, f, ensure_ascii=False)


if __name__ == "__main__":
    tf.app.run()