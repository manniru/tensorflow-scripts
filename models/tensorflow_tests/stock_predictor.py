import tensorflow as tf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


outfile = "prediction.png"
outfolder = "output"
#infile = "ETHUSD_OHLC_alltargets.csv"
infile = "TSLA_alltargets.csv"
infolder = "stock"

learning_rate = 0.001
num_epochs = 100
batch_size = 1
train_size = 0.9
truncated_backprop_length = 1
state_size = 12
num_features = 4
num_classes = 4
min_test_size = 100


dataset = pd.read_csv('../data/{}/{}'.format(infolder, infile))
train_length = int(len(dataset.index) * train_size)
test_length = int(len(dataset.index) * (1.0 - train_size))
num_batches = train_length // batch_size // truncated_backprop_length


def prepare_data():
    datasetNorm = (dataset - dataset.min()) / (dataset.max() - dataset.min())
    datasetTrain = datasetNorm[dataset.index < train_length]
    datasetTest = datasetNorm[dataset.index >= train_length]

    try:
        xTrain = datasetTrain[['Open','High','Low','Close']].as_matrix()
        yTrain = datasetTrain[['OpenTarget','HighTarget','LowTarget','CloseTarget']].as_matrix()
        xTest = datasetTest[['Open','High','Low','Close']].as_matrix()
        yTest = datasetTest[['OpenTarget','HighTarget','LowTarget','CloseTarget']].as_matrix()
        test_prices = datasetTest['Close'].as_matrix()
        print("Using OHLC data")
    except:
        xTrain = datasetTrain[['Close','MACD','Stochastics','ATR']].as_matrix()
        yTrain = datasetTrain[['CloseTarget', 'MACDTarget', 'StochasticsTarget', 'ATRTarget']].as_matrix()
        xTest = datasetTest[['Close','MACD','Stochastics','ATR']].as_matrix()
        yTest = datasetTest[['CloseTarget', 'MACDTarget', 'StochasticsTarget', 'ATRTarget']].as_matrix()
        test_prices = datasetTest['Close'].as_matrix()
        print("Using technical indicators data")

    return xTrain, xTest, yTrain, yTest, test_prices


def model():
    batchX_placeholder = tf.placeholder(dtype=tf.float32,
                                        shape=[None, truncated_backprop_length, num_features],
                                        name='data_ph')
    batchY_placeholder = tf.placeholder(dtype=tf.float32,
                                        shape=[None, truncated_backprop_length, num_classes],
                                        name='target_ph')
    W2 = tf.Variable(   initial_value=np.random.rand(state_size, num_classes),
                        dtype=tf.float32)
    b2 = tf.Variable(   initial_value=np.random.rand(1, num_classes),
                        dtype=tf.float32)
    labels_series = tf.unstack(batchY_placeholder, axis=1)
    cell = tf.contrib.rnn.BasicRNNCell(num_units=state_size)
    states_series, current_state = tf.nn.dynamic_rnn(   cell=cell,
                                                        inputs=batchX_placeholder,
                                                        dtype=tf.float32)
    states_series = tf.transpose(states_series, [1,0,2])
    last_state = tf.gather(params=states_series, indices=states_series.get_shape()[0]-1)
    last_label = tf.gather(params=labels_series, indices=len(labels_series)-1)
    weight = tf.Variable(tf.truncated_normal([state_size, num_classes]))
    bias = tf.Variable(tf.constant(0.1, shape=[num_classes]))
    prediction = tf.matmul(last_state, weight) + bias
    loss = tf.reduce_mean(tf.squared_difference(last_label, prediction))
    train_step = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)
    return (loss, train_step, prediction, last_label,
            last_state, batchX_placeholder, batchY_placeholder)


def train_and_test( loss, train_step, prediction, last_label, last_state,
                    batchX_placeholder, batchY_placeholder,
                    xTrain, xTest, yTrain, yTest):
    loss_list = []
    test_days_pred_list = []
    test_day_pred_list = []

    with tf.Session() as sess:
        tf.global_variables_initializer().run()
        print('Train data length: %d' % train_length)
        print('Test data length: %d' % test_length)
        _loss = 0

        # Train
        for epoch_idx in range(num_epochs):
            print('Epoch %d, loss %.6f' % (epoch_idx, _loss))
            for batch_idx in range(num_batches):
                start_idx = batch_idx * truncated_backprop_length
                end_idx = start_idx + truncated_backprop_length * batch_size

                batchX = xTrain[start_idx:end_idx,:].reshape(batch_size,truncated_backprop_length,num_features)
                batchY = yTrain[start_idx:end_idx].reshape(batch_size,truncated_backprop_length,num_classes)

                _loss, _train_step, _pred, _last_label, _prediction = sess.run(
                    fetches = [loss, train_step, prediction, last_label, prediction],
                    feed_dict = {   batchX_placeholder : batchX,
                                    batchY_placeholder : batchY}
                )

                loss_list.append(_loss)

        # Test len(xTest) days
        for test_idx in range(len(xTest) - truncated_backprop_length):
            if test_idx == 0:
                testBatchX = xTest[test_idx:test_idx+truncated_backprop_length,:].reshape((1, truncated_backprop_length, num_features))
                testBatchY = yTest[test_idx:test_idx+truncated_backprop_length].reshape((1, truncated_backprop_length, num_classes))
            else:
                testBatchX = test_pred.reshape([1, truncated_backprop_length, num_features])
                testBatchY = test_pred[0].reshape([1, truncated_backprop_length, num_classes])

            feed = {batchX_placeholder : testBatchX,
                    batchY_placeholder : testBatchY}

            _last_state, _last_label, test_pred = sess.run([last_state, last_label, prediction], feed_dict=feed)
            test_days_pred_list.append(test_pred[-1][0])

        # Test per day
        for test_idx in range(len(xTest) - truncated_backprop_length):
            testBatchX = xTest[test_idx:test_idx+truncated_backprop_length,:].reshape((1, truncated_backprop_length, num_features))
            testBatchY = yTest[test_idx:test_idx+truncated_backprop_length].reshape((1, truncated_backprop_length, num_classes))

            feed = {batchX_placeholder : testBatchX,
                    batchY_placeholder : testBatchY}

            _last_state, _last_label, test_pred = sess.run([last_state, last_label, prediction], feed_dict=feed)
            test_day_pred_list.append(test_pred[-1][0])

    return test_day_pred_list, test_days_pred_list


def plot_prediction(day, days, test_prices):
    fig = plt.figure(num=None, figsize=(22, 10), dpi=80, facecolor="white")
    fig.canvas.set_window_title("Stock prediction {}".format(infile))
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)

    ax1.set_title("Close price prediction per day")
    ax1.plot(test_prices, label='Price', color='blue')
    ax1.plot(day, label='Predicted',color='red')
    ax1.legend(loc='upper left')

    ax2.set_title("Prediction for {} days".format(len(test_prices)))
    ax2.plot(test_prices, label='Price', color='blue')
    ax2.plot(days, label='Predicted', color='red')
    ax2.legend(loc='upper left')

    plt.savefig(os.path.join(outfolder, outfile))
    plt.show()


if __name__ == "__main__":
    outfile = infile.split(".")[0] + "_" + outfile
    trainX, testX, trainY, testY, prices = prepare_data()
    loss, train_step, prediction, last_label, last_state, placeholder_x, placeholder_y = model()
    day, days = train_and_test( loss, train_step, prediction, last_label, last_state,
                                placeholder_x, placeholder_y,
                                trainX, testX, trainY, testY)

    plot_prediction(day, days, prices)
