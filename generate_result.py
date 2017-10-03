# -*- coding: utf-8 -*-
# @Author: lc
# @Date:   2017-09-17 00:22:17
# @Last Modified by:   LC
# @Last Modified time: 2017-09-30 17:01:13

import sys
import time
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
os.environ["CUDA_VISIBLE_DEVICES"] = '1' # decide to use CPU or GPU
from datetime import datetime
import glob
import logging
import re

import json
import tensorflow as tf

import configuration
import inference_wrapper
from inference_utils import caption_generator
from inference_utils import vocabulary


checkpoint_path = '../aichallenge_model_inception/train/'
checkpoint_path = '../aichallenge_model_inception_with_custom_embedding/train/'
vocab_file = '../data/aichallenge/TFRecordFile/word_counts.txt'
test_img_dir = '../data/aichallenge/test1500png/'
#test_img_dir = '../data/aichallenge/testsmall/'
log_file = './logs/model_result_mapping.log'
log_file = './logs/model_result_mapping_custom_embedding.log'
result_json_dir = '../data/aichallenge/result/'
result_json_dir = '../data/aichallenge/result_custom_embedding/'

FLAGS = tf.flags.FLAGS
tf.flags.DEFINE_string("checkpoint_path", checkpoint_path, 
                       "Model checkpoint file or directory containing a model checkpoint file.")
tf.flags.DEFINE_string("vocab_file", vocab_file, "Text file containing the vocabulary.")
tf.flags.DEFINE_string("test_img_dir", test_img_dir, 
                       "directory containing images for test")
tf.flags.DEFINE_string("log_file", log_file, 
                       "log file mapping the reuslt generated by models")
tf.flags.DEFINE_string("result_json_dir", result_json_dir, 
                       "directory containing json file for the result of the test images")

logging.basicConfig(level=logging.DEBUG, filename = log_file, filemode="a+", format="%(asctime)-15s %(levelname)-8s  %(message)s")


def get_evaluated_models(log_file):
    """get evaluated models from log file so as not to evaluate it again
    
    Args:
        log_file (str): 
    
    Returns:
        set(model name)
    """
    evaluated_models = set()
    with open(log_file, 'r') as f:
        for line in f:
            m = re.search('finish(.*)model.ckpt-(\d+)', line)
            if m:
                evaluated_models.add('model.ckpt-'+m.group(2))
    return evaluated_models

    
def main(_):
    # Create the vocabulary.
    vocab = vocabulary.Vocabulary(FLAGS.vocab_file)
    # remove Thumbs.db from files
    filenames = [f for f in os.listdir(FLAGS.test_img_dir) if f.endswith('png')]
    print('There are totally {0} images.....'.format(len(filenames)))
    # get evaluated models from log file
    evaluated_models = get_evaluated_models(FLAGS.log_file)
    
    # validate every checkpoint file in the checkpoint path
    for path in glob.glob(FLAGS.checkpoint_path + '*.meta'):
        checkpoint_file = path.replace('\\', '/').rstrip('.meta')
        if checkpoint_file.split('/')[-1] in evaluated_models:
            print('model {0} has already bee evaluated successfully'.format(checkpoint_file))
            continue
        result_json_file = '{0}result_{1}.json'.format(FLAGS.result_json_dir, checkpoint_file.split('/')[-1])
        logging.info('mapping of model and result file, ({0}, {1})'.format(checkpoint_file.split('/')[-1], result_json_file.split('/')[-1]))
        start_time = time.time()
        g = tf.Graph()
        with g.as_default():
            model = inference_wrapper.InferenceWrapper()
            restore_fn = model.build_graph_from_config(configuration.ModelConfig(), checkpoint_file)
        g.finalize()

        with tf.Session(graph=g) as sess:
            # Load the model from checkpoint.
            restore_fn(sess)

            # Prepare the caption generator. Here we are implicitly using the default
            # beam search parameters. See caption_generator.py for a description of the
            # available beam search parameters.
            count, result = 0, []
            generator = caption_generator.CaptionGenerator(model, vocab)
            for filename in filenames:
                count += 1
                with open(FLAGS.test_img_dir + filename, "rb") as f:
                    image = f.read()
                captions = generator.beam_search(sess, image)
                sentence = [vocab.id_to_word(w) for w in captions[0].sentence[1:-1]]
                sentence = ''.join(sentence)
                image_id = filename.split('.')[0]
                result.append({'caption': sentence, 'image_id':image_id})
                if count % 500 == 0:
                    print('finish generating caption for {0} images'.format(count))
            print('finish totally {0} images'.format(count))
            with open(result_json_file, encoding = 'utf8', mode = 'w') as f:
                json.dump(result, f, ensure_ascii = False)
            logging.info('finish generating {1} from {0}'.format(checkpoint_file.split('/')[-1], result_json_file.split('/')[-1]))
            logging.info('time consuming: {0}\n'.format(time.time() - start_time))
            print('time consuming: {0}s'.format(time.time() - start_time))


if __name__ == "__main__":
    tf.app.run()
    """
    for model in get_evaluated_models(log_file):
        print(model)
    """
