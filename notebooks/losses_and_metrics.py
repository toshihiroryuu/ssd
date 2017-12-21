from functools import partial, update_wrapper
import tensorflow as tf
from keras.metrics import sparse_categorical_accuracy, categorical_accuracy


def compute_one_by_N(N):
    zero = tf.constant(0.0)
    zero_mask = tf.cast(tf.equal(N, zero), tf.float32)
    non_zero_mask = tf.cast(tf.not_equal(N, zero), tf.float32)
    N = N + zero_mask
    one_by_N = tf.reciprocal(N)
    
    return one_by_N*non_zero_mask


def wrapped_partial(func, *args, **kwargs):
    partial_func = partial(func, *args, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func


def loss_with_negative_mining(y_true, y_pred, k, num_aspect_ratios, num_classes):
#     zero = tf.constant(0.0)
#     print "Start loss"
#     print y_true, y_pred
    zero = tf.constant(0, dtype=tf.int32)
    
    # remove the zero padding from the input to get sparse labels
    y_true = tf.slice(y_true, begin=[0, 0, 0, 0], size=[-1, -1, -1, num_aspect_ratios])
    y_pred_shape = tf.shape(y_pred)
    y_pred = tf.reshape(y_pred, shape = [y_pred_shape[0], y_pred_shape[1], y_pred_shape[2],
                                         num_aspect_ratios, num_classes])
    y_true = tf.cast(y_true, tf.int32)
    
    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y_true, logits=y_pred)
#     print "y_true", y_true, "y_pred", y_pred, "loss", loss
    
    # computing loss for all boxes where the label is not background
    pos_samples = tf.not_equal(y_true, zero)
    pos_loss = tf.multiply(loss, tf.cast(pos_samples, tf.float32))
    pos_loss = tf.reduce_sum(pos_loss, [1, 2, 3])
    
    # computing loss for all boxes where the label is background, will only keep the top k terms
    neg_samples = tf.equal(y_true, zero)
    neg_loss = tf.multiply(loss, tf.cast(neg_samples, tf.float32))
    
#     print "pos_samples", pos_samples, "neg_samples", neg_samples, "pos_loss", pos_loss, "neg_loss", neg_loss
    
    neg_loss_flattened = tf.reshape(neg_loss, [tf.shape(y_true)[0], -1])
    top_k_neg_loss, _ = tf.nn.top_k(neg_loss_flattened, k=k, sorted=False)
    top_k_neg_loss = tf.reduce_sum(top_k_neg_loss, axis=1)
    N = tf.cast(tf.reduce_sum(y_true, [1, 2, 3]), tf.float32)# + tf.ones(whatever)
#     one_by_N = tf.reciprocal(N)
    total_loss = (pos_loss + top_k_neg_loss)*compute_one_by_N(N)
    
#     print "neg_loss_flattened", neg_loss_flattened, "top_k_neg_loss", top_k_neg_loss, "N", N, 
#     "total_loss before sum", total_loss
    
#     print "End loss"
    
    return tf.reduce_mean(total_loss)


def accuracy(y_true, y_pred, num_aspect_ratios, num_classes):
#     sparse_categorical_accuracy that works for matrices with rank greater than 2
    print "y_true", y_true, "y_pred", y_pred
    y_true = tf.slice(y_true, begin=[0, 0, 0, 0], size=[-1, -1, -1, num_aspect_ratios])
    
    y_pred_shape = tf.shape(y_pred)
    y_pred = tf.reshape(y_pred, shape = [y_pred_shape[0], y_pred_shape[1], y_pred_shape[2],
                                         num_aspect_ratios, num_classes])
    print "After reshape and slicing: y_true", y_true, "y_pred", y_pred
    y_pred = tf.reshape(y_pred, shape = [-1, num_classes])
    y_true = tf.reshape(y_true, shape=[ -1])
    
    y_true = tf.cast(y_true, tf.int32)
    y_true_one_hot = tf.one_hot(y_true, depth=num_classes)
#     y_pred_dense = tf.argmax(y_pred, axis=1)
    print "Final: y_true", y_true_one_hot, "y_pred", y_pred
    return categorical_accuracy(y_true_one_hot, y_pred)

def recall(y_true, y_pred, num_aspect_ratios, num_classes):
    # Out of all the default boxes that are not background, how many does the model get right
    
    zero = tf.constant(0, dtype=tf.int32)
#     print "y_true", y_true, "y_pred", y_pred
    # remove extra zero padding
    y_true = tf.slice(y_true, begin=[0, 0, 0, 0], size=[-1, -1, -1, num_aspect_ratios])
    
    y_pred_shape = tf.shape(y_pred)
    y_pred = tf.reshape(y_pred, shape = [y_pred_shape[0], y_pred_shape[1], y_pred_shape[2],
                                         num_aspect_ratios, num_classes])
#     print "After reshape and slicing: y_true", y_true, "y_pred", y_pred
    y_pred = tf.reshape(y_pred, shape = [-1, num_classes])
    y_true = tf.reshape(y_true, shape=[ -1])
    
    y_true = tf.cast(y_true, tf.int32)
    
    pos_indices = tf.squeeze(tf.where(tf.not_equal(y_true, zero)))
    print (pos_indices)
    y_true_pos = tf.gather(y_true, pos_indices)
    y_pred_pos = tf.gather(y_pred, pos_indices) #y_pred[pos_indices]
    
    y_true_pos_one_hot = tf.one_hot(y_true_pos, depth=num_classes)

    return categorical_accuracy(y_true_pos_one_hot, y_pred_pos)