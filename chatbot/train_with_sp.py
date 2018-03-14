"""
对SequenceToSequence模型进行基本的参数组合测试
"""

import sys
import random
import pickle

import numpy as np
import tensorflow as tf
from tqdm import tqdm
# from sklearn.utils import shuffle

sys.path.append('..')


def test(bidirectional, cell_type, depth,
         attention_type, use_residual, use_dropout, time_major, hidden_units):
    """测试不同参数在生成的假数据上的运行结果"""

    from sequence_to_sequence import SequenceToSequence
    from data_utils import batch_flow_bucket as batch_flow
    from word_sequence import WordSequence # pylint: disable=unused-variable
    from threadedgenerator import ThreadedGenerator
    from same_person_model import SamePerson

    x_data, y_data, ws = pickle.load(
        open('chatbot.pkl', 'rb'))

    # 训练部分
    n_epoch = 10
    batch_size = 64
    # x_data, y_data = shuffle(x_data, y_data, random_state=0)
    # x_data = x_data[:10000]
    # y_data = y_data[:10000]
    steps = int(len(x_data) / batch_size) + 1

    config = tf.ConfigProto(
        # device_count={'CPU': 1, 'GPU': 0},
        allow_soft_placement=True,
        log_device_placement=False
    )


    with tf.Graph().as_default():
        # test(True, 'lstm', 2, 'Bahdanau', True, True, True, 256)
        model_sp = SamePerson(
            input_vocab_size=len(ws),
            n_target=2,
            batch_size=batch_size,
            learning_rate=0.001,
            bidirectional=True,
            cell_type='lstm',
            depth=2,
            use_residual=True,
            use_dropout=True,
            parallel_iterations=1,
            time_major=True,
            hidden_units=256,
            optimizer='adam'
        )
        init = tf.global_variables_initializer()
        sess_sp = tf.Session(config=config)
        sess_sp.run(init)
        model_sp.load(sess_sp, './s2ss_chatbot_samperson.ckpt')


    save_path = './s2ss_chatbot_sp.ckpt'

    tf.reset_default_graph()
    with tf.Graph().as_default():
        random.seed(0)
        np.random.seed(0)
        tf.set_random_seed(0)

        with tf.Session(config=config) as sess:

            model = SequenceToSequence(
                input_vocab_size=len(ws),
                target_vocab_size=len(ws),
                batch_size=batch_size,
                bidirectional=bidirectional,
                cell_type=cell_type,
                depth=depth,
                attention_type=attention_type,
                use_residual=use_residual,
                use_dropout=use_dropout,
                hidden_units=hidden_units,
                time_major=time_major,
                learning_rate=0.001,
                optimizer='adam',
                share_embedding=True,
                dropout=0.2
            )
            init = tf.global_variables_initializer()
            sess.run(init)

            # print(sess.run(model.input_layer.kernel))
            # exit(1)

            flow = ThreadedGenerator(
                batch_flow([x_data, y_data], ws, batch_size
                           add_end=[False, True]),
                queue_maxsize=30)

            for epoch in range(1, n_epoch + 1):
                costs = []
                bar = tqdm(range(steps), total=steps,
                           desc='epoch {}, loss=0.000000'.format(epoch))
                for _ in bar:
                    x, xl, y, yl = next(flow)

                    rewards = model_sp.predict(sess_sp, x, xl, y, yl)
                    rewards = rewards[:, 1:]

                    x = np.flip(x, axis=1)
                    # print(x, y)
                    cost, lr = model.train(sess, x, xl, y, yl,
                                           return_lr=True, rewards=rewards)
                    costs.append(cost)
                    bar.set_description('epoch {} loss={:.6f} lr={:.6f}'.format(
                        epoch,
                        np.mean(costs),
                        lr
                    ))

                model.save(sess, save_path)

            flow.close()



    # 测试部分
    tf.reset_default_graph()
    model_pred = SequenceToSequence(
        input_vocab_size=len(ws),
        target_vocab_size=len(ws),
        batch_size=1,
        mode='decode',
        beam_width=12,
        bidirectional=bidirectional,
        cell_type=cell_type,
        depth=depth,
        attention_type=attention_type,
        use_residual=use_residual,
        use_dropout=use_dropout,
        hidden_units=hidden_units,
        time_major=time_major,
        parallel_iterations=1,
        learning_rate=0.001,
        optimizer='adam',
        share_embedding=True
    )
    init = tf.global_variables_initializer()

    with tf.Session(config=config) as sess:
        sess.run(init)
        model_pred.load(sess, save_path)

        bar = batch_flow([x_data, y_data], ws, 1, add_end=False)
        t = 0
        for x, xl, y, yl in bar:
            x = np.flip(x, axis=1)
            pred = model_pred.predict(
                sess,
                np.array(x),
                np.array(xl)
            )
            print(ws.inverse_transform(x[0]))
            print(ws.inverse_transform(y[0]))
            print(ws.inverse_transform(pred[0]))
            t += 1
            if t >= 3:
                break

    tf.reset_default_graph()
    model_pred = SequenceToSequence(
        input_vocab_size=len(ws),
        target_vocab_size=len(ws),
        batch_size=1,
        mode='decode',
        beam_width=1,
        bidirectional=bidirectional,
        cell_type=cell_type,
        depth=depth,
        attention_type=attention_type,
        use_residual=use_residual,
        use_dropout=use_dropout,
        hidden_units=hidden_units,
        time_major=time_major,
        parallel_iterations=1,
        learning_rate=0.001,
        optimizer='adam',
        share_embedding=True
    )
    init = tf.global_variables_initializer()

    with tf.Session(config=config) as sess:
        sess.run(init)
        model_pred.load(sess, save_path)

        bar = batch_flow([x_data, y_data], ws, 1, add_end=False)
        t = 0
        for x, xl, y, yl in bar:
            pred = model_pred.predict(
                sess,
                np.array(x),
                np.array(xl)
            )
            print(ws.inverse_transform(x[0]))
            print(ws.inverse_transform(y[0]))
            print(ws.inverse_transform(pred[0]))
            t += 1
            if t >= 3:
                break


def main():
    """入口程序，开始测试不同参数组合"""
    random.seed(0)
    np.random.seed(0)
    tf.set_random_seed(0)
    test(
        bidirectional=True,
        cell_type='lstm',
        depth=2,
        attention_type='Bahdanau',
        use_residual=False,
        use_dropout=False,
        time_major=False,
        hidden_units=512
    )


if __name__ == '__main__':
    main()
