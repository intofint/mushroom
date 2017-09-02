import numpy as np
import tensorflow as tf


class Extractor:
    def __init__(self, name=None, folder_name=None, load_path=None,
                 **convnet_pars):
        self._name = name
        self._folder_name = folder_name

        self._session = tf.Session()

        if load_path is not None:
            self._load(load_path)
        else:
            self._build(convnet_pars)

        self._train_writer = tf.summary.FileWriter(
            self._folder_name,
            graph=tf.get_default_graph()
        )

        self._train_saver = tf.train.Saver()

    def __call__(self, x):
        return self._session.run(self._features, feed_dict={self._x: x})

    def predict(self, x):
        return self._session.run(self._prediction, feed_dict={self._x: x})

    def fit(self, x, y):
        summaries, _ = self._session.run(
            [self._merged, self._train_step],
            feed_dict={self._x: x, self._target_prediction: y}
        )
        self._train_writer.add_summary(summaries, self._train_count)

        self._train_count += 1

    def set_weights(self, weights):
        w = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,
                              scope=self._name)
        assert len(w) == len(weights)

        for i in xrange(len(w)):
            self._session.run(tf.assign(w[i], weights[i]))

    def get_weights(self):
        w = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,
                              scope=self._name)

        return self._session.run(w)

    def save(self):
        self._train_saver.save(
            self._session,
            self._folder_name + '/deep_fqi_extractor'
        )

    def _load(self, path):
        restorer = tf.train.import_meta_graph(path + 'deep_fqi_extractor.meta')
        restorer.restore(self._session, path + 'deep_fqi_extractor')
        self._restore_collection()

    def _build(self, convnet_pars):
        with tf.variable_scope(self._name, default_name='deep_fqi_extractor'):
            self._x = tf.placeholder(tf.float32,
                                     shape=[None,
                                            convnet_pars['height'],
                                            convnet_pars['width'],
                                            convnet_pars['history_length']],
                                     name='input')
            hidden_1 = tf.layers.conv2d(
                self._x, 32, 8, 4, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_1'
            )
            hidden_2 = tf.layers.conv2d(
                hidden_1, 64, 4, 2, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_2'
            )
            hidden_3 = tf.layers.conv2d(
                hidden_2, 64, 3, 1, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_3'
            )
            hidden_4 = tf.layers.conv2d(
                hidden_3, 16, 3, 1, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_4'
            )
            self._features = tf.reshape(hidden_4, [-1, 5 * 5 * 16],
                                        name='features')
            self._conv_features = tf.reshape(self._features, [-1, 5, 5, 16],
                                             name='conv_features')
            hidden_5 = tf.layers.conv2d_transpose(
                self._conv_features, 16, 3, 1, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_5'
            )
            hidden_6 = tf.layers.conv2d_transpose(
                hidden_5, 64, 3, 1, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_6'
            )
            hidden_7 = tf.layers.conv2d_transpose(
                hidden_6, 64, 4, 2, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_7'
            )
            hidden_8 = tf.layers.conv2d_transpose(
                hidden_7, 32, 8, 4, activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='hidden_8'
            )
            self._prediction = tf.layers.conv2d_transpose(
                hidden_8, 4, 1, 1, activation=tf.nn.sigmoid,
                kernel_initializer=tf.glorot_uniform_initializer(),
                bias_initializer=tf.glorot_uniform_initializer(),
                name='prediction'
            )

            self._target_prediction = tf.placeholder(
                'float32',
                shape=[None, convnet_pars['height'], convnet_pars['width'],
                       convnet_pars['history_length']],
                name='target_prediction')
            self._action = tf.placeholder('uint8', [None], name='action')

            loss = tf.losses.sigmoid_cross_entropy(self._target_prediction,
                                                   self._prediction)
            tf.summary.scalar('loss', loss)
            self._merged = tf.summary.merge_all()

            optimizer = convnet_pars['optimizer']
            if optimizer['name'] == 'rmspropcentered':
                opt = tf.train.RMSPropOptimizer(learning_rate=optimizer['lr'],
                                                decay=optimizer['decay'],
                                                centered=True)
            elif optimizer['name'] == 'rmsprop':
                opt = tf.train.RMSPropOptimizer(learning_rate=optimizer['lr'],
                                                decay=optimizer['decay'])
            elif optimizer['name'] == 'adam':
                opt = tf.train.AdamOptimizer()
            elif optimizer['name'] == 'adadelta':
                opt = tf.train.AdadeltaOptimizer()
            else:
                raise ValueError('Unavailable optimizer selected.')

            self._train_count = 0
            self._train_step = opt.minimize(loss=loss)

        self._session.run(tf.global_variables_initializer())

        self._add_collection()

    def _add_collection(self):
        tf.add_to_collection('x', self._x)
        tf.add_to_collection('prediction', self._prediction)
        tf.add_to_collection('target_prediction', self._target_prediction)
        tf.add_to_collection('merged', self._merged)
        tf.add_to_collection('train_step', self._train_step)

    def _restore_collection(self):
        self._x = tf.get_collection('x')[0]
        self._prediction = tf.get_collection('prediction')[0]
        self._target_prediction = tf.get_collection('target_prediction')[0]
        self._merged = tf.get_collection('merged')[0]
        self._train_step = tf.get_collection('train_step')[0]