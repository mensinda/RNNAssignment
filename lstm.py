#!/usr/bin/env python3

"""
Minimal character-level LSTM model. Written by Ngoc Quan Pham
Code structure borrowed from the Vanilla RNN model from Andreij Karparthy @karparthy.
BSD License
"""
import numpy as np
from random import uniform
import sys


# Since numpy doesn't have a function for sigmoid
# We implement it manually here
def sigmoid(x):
  return 1 / (1 + np.exp(-x))


# The derivative of the sigmoid function
def dsigmoid(y):
    return y * (1 - y)


# The derivative of the tanh function
def dtanh(x):
    return 1 - x*x


# The numerically stable softmax implementation
def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


# data I/O
data = open('data/input.txt', 'r').read() # should be simple plain text file
chars = list(set(data))
data_size, vocab_size = len(data), len(chars)
print('data has %d characters, %d unique.' % (data_size, vocab_size))
char_to_ix = { ch:i for i,ch in enumerate(chars) }
ix_to_char = { i:ch for i,ch in enumerate(chars) }
std = 0.1

option = sys.argv[1]

# hyperparameters
emb_size = 4
hidden_size = 32  # size of hidden layer of neurons
seq_length = 64  # number of steps to unroll the RNN for
learning_rate = 5e-2
max_updates = 500000

concat_size = emb_size + hidden_size

# model parameters
# char embedding parameters
Wex = np.random.randn(emb_size, vocab_size)*std # embedding layer

# LSTM parameters
Wf = np.random.randn(hidden_size, concat_size) * std # forget gate
Wi = np.random.randn(hidden_size, concat_size) * std # input gate
Wo = np.random.randn(hidden_size, concat_size) * std # output gate
Wc = np.random.randn(hidden_size, concat_size) * std # c term

bf = np.zeros((hidden_size, 1)) # forget bias
bi = np.zeros((hidden_size, 1)) # input bias
bo = np.zeros((hidden_size, 1)) # output bias
bc = np.zeros((hidden_size, 1)) # memory bias

# Output layer parameters
Why = np.random.randn(vocab_size, hidden_size)*0.01 # hidden to output
by = np.zeros((vocab_size, 1)) # output bias


def forward(inputs, targets, memory):
    """
    inputs,targets are both list of integers.
    hprev is Hx1 array of initial hidden state
    returns the loss, gradients on model parameters, and last hidden state
    """

    # The LSTM is different than the simple RNN that it has two memory cells
    # so here you need two different hidden layers
    hprev, cprev = memory

    # Here you should allocate some variables to store the activations during forward
    # One of them here is to store the hiddens and the cells
    # xs: characters at timesteps
    # cs: memory at timesteps
    # hs: hidden states at timesteps
    # ys: output layers at timesteps (labels/targets)
    # ps: probability distributions at timesteps
    # wes: word embeddings at timesteps
    # f_gate: forget gate activation at timesteps
    # i_gate: input gate activation at timesteps
    # o_gate: output gate activation at timesteps
    # c_cand: candidate memory at timesteps
    hs, cs, xs, zs, wes, os, ps, ys, f_gate, i_gate, o_gate, c_cand = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}

    hs[-1] = np.copy(hprev)
    cs[-1] = np.copy(cprev)

    loss = 0
    # forward pass
    for t in range(len(inputs)):
        # encode in 1-of-k representation (one hot vector)
        xs[t] = np.zeros((vocab_size,1))
        xs[t][inputs[t]] = 1

        # convert word indices to word embeddings
        wes[t] = np.dot(Wex, xs[t])

        # LSTM cell operation
        # first concatenate the input and h
        # This step is irregular (to save the amount of matrix multiplication we have to do)
        # I will refer to this vector as [h X]
        zs[t] = np.row_stack((hs[t-1], wes[t]))

        # ------ LSTM IMPLEMENTATION START ------

        # compute the forget gate
        # f_gate = sigmoid (W_f \cdot [h X] + b_f)
        f_gate[t] = sigmoid(np.dot(Wf, zs[t]) + bf)

        # compute the input gate
        # i_gate = sigmoid (W_i \cdot [h X] + b_i)
        i_gate[t] = sigmoid(np.dot(Wi, zs[t]) + bi)

        # compute the candidate memory
        # \hat{c} = tanh (W_c \cdot [h X] + b_c])
        c_cand[t] = np.tanh(np.dot(Wc, zs[t]) + bc)

        # new memory: applying forget gate on the previous memory
        # and then adding the input gate on the candidate memory
        # c_new = f_gate * prev_c + i_gate * \hat{c}
        cs[t] = f_gate[t] * cs[t-1] + i_gate[t] * c_cand[t]

        # output gate
        # o_gate = sigmoid (Wo \cdot [h X] + b_o)
        o_gate[t] = sigmoid(np.dot(Wo, zs[t]) + bo)

        # new hidden state for the LSTM
        # h = o_gate * tanh(c_new)
        hs[t] = o_gate[t] * np.tanh(cs[t])

        # ------ LSTM IMPLEMENTATION DONE ------
        # output layer - softmax and cross-entropy loss
        # unnormalized log probabilities for next chars

        # o = Why \cdot h + by
        os[t] = np.dot(Why, hs[t]) + by

        # softmax for probabilities for next chars
        # p = softmax(o)
        ps[t] = softmax(os[t])

        # cross-entropy loss
        # cross entropy loss at time t:
        # create an one hot vector for the label y
        ys[t] = np.zeros((vocab_size, 1))
        ys[t][targets[t]] = 1

        # and then cross-entropy (see the elman-rnn file for the hint)
        loss_t = np.sum(-np.log(ps[t]) * ys[t])
        loss += loss_t

    # define your activations
    memory = (hs[len(inputs)-1], cs[len(inputs)-1])
    activations = (hs, cs, xs, zs, wes, os, ps, ys, f_gate, i_gate, o_gate, c_cand)

    return loss, activations, memory


def backward(activations, clipping=True):

    # backward pass: compute gradients going backwards
    # Here we allocate memory for the gradients
    dWex, dWhy = np.zeros_like(Wex), np.zeros_like(Why)
    dby = np.zeros_like(by)
    dWf, dWi, dWc, dWo = np.zeros_like(Wf), np.zeros_like(Wi),np.zeros_like(Wc), np.zeros_like(Wo)
    dbf, dbi, dbc, dbo = np.zeros_like(bf), np.zeros_like(bi),np.zeros_like(bc), np.zeros_like(bo)

    hs, cs, xs, zs, wes, os, ps, ys, f_gate, i_gate, o_gate, c_cand = activations



    # similar to the hidden states in the vanilla RNN
    # We need to initialize the gradients for these variables
    dhnext = np.zeros_like(hs[0])
    dcnext = np.zeros_like(cs[0])

    # back propagation through time starts here
    for t in reversed(range(len(inputs))):

        # Same as in elman-rnn, we skip directly to
        # the gradients of the unnormalized scores o
        do = ps[t] - ys[t]

        # Same as in elman-rnn
        dWhy += np.dot(do, hs[t].T)
        dby += do

        # h is connected to both o and the next h,
        # sum up gradients
        dh = np.dot(Why.T, do) + dhnext

        # Calculate pre-activation of o_gate within h first
        # h = o_gate * tanh(c_new)
        # o_gate = sigmoid (Wo \cdot [h X] + b_o)
        # ---------
        # In order to gain the pre-activation state of o_gate,
        # the derivative of the sigmoid needs to be used 
        # on the saved value o_gate => dsigmoid(o_gate)
        dh_o = dsigmoid(o_gate[t]) * dh * np.tanh(cs[t])

        # Calculate pre activation c_new within h next
        # h = o_gate * tanh(c_new)
        # c_new = f_gate * prev_c + i_gate * \hat{c}
        # dcnext is added since there is a connection to the next c
        # ---------
        # Note that unlike the sigmoid, cs[t] is not saved in its activated form!
        # This means that first, the value is run through the tanh before the
        # tanh derivative is applied => dtanh(tanh(c_new))
        dh_c = o_gate[t] * dh * dtanh(np.tanh(cs[t])) + dcnext

        # Next, derive c_new = f_gate * prev_c + i_gate * \hat{c}
        # ---------
        # First, the gradient for f_gate
        # f_gate = sigmoid (W_f \cdot [h X] + b_f)
        dc_f = dsigmoid(f_gate[t]) * cs[t-1] * dh_c

        # Second, the gradient for i_gate
        # i_gate = sigmoid (W_i \cdot [h X] + b_i)
        dc_i = dsigmoid(i_gate[t]) * c_cand[t] * dh_c

        # Third, the gradient for \hat{c} = c_cand
        # \hat{c} = tanh (W_c \cdot [h X] + b_c])
        dc_c = dtanh(c_cand[t]) * i_gate[t] * dh_c

        # Update the gate weights
        dWo += np.dot(dh_o, zs[t].T)
        dWf += np.dot(dc_f, zs[t].T)
        dWi += np.dot(dc_i, zs[t].T)
        dWc += np.dot(dc_c, zs[t].T)

        # Update remaining biases
        dbo += dh_o
        dbf += dc_f
        dbi += dc_i
        dbc += dc_c

        # Update dhnext and dcnext
        # ---------
        # First, accumulate gradients of all gates to find gradient of z
        dz_o = np.dot(Wo.T, dh_o) # output gate
        dz_i = np.dot(Wi.T, dc_i) # input gate
        dz_f = np.dot(Wf.T, dc_f) # forget gate
        dz_c = np.dot(Wc.T, dc_c) # candidate memory

        dz = dz_o + dz_i + dz_f + dz_c
        # z = [h X] was saved as zs[t] = np.row_stack((hs[t-1], wes[t])),
        # therefore the first hidden_size elements of dz
        # are the next hidden weights
        dhnext = dz[:hidden_size]

        # dcnext is the gradient of prev_c in 
        # c_new = f_gate * prev_c + i_gate * \hat{c}
        dcnext = f_gate[t] * dh_c

        # Finally, update dWex
        # ---------
        # The word embeddings were the remaining elements of z = [h X]
        # therefore dwes are the remaining elements of dz after dhnext
        dwes = dz[hidden_size:]
        # As a last step, get the gradient dWex 
        # wes[t] = np.dot(Wex, xs[t])
        dWex += np.dot(dwes, xs[t].T) 

    if clipping:
        # clip to mitigate exploding gradients
        for dparam in [dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby]:
            np.clip(dparam, -5, 5, out=dparam)

    gradients = (dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby)

    return gradients


def sample(memory, seed_ix, n):
    """
    sample a sequence of integers from the model
    h is memory state, seed_ix is seed letter for first time step
    """
    h, c = memory
    x = np.zeros((vocab_size, 1))
    x[seed_ix] = 1
    result = []

    for t in range(n):
        # The following implementation is equivalent to the forward pass,
        # without the storage for the activations

        # convert word indices to word embeddings
        wes = np.dot(Wex, x)

        # LSTM cell operation
        # first concatenate the input and h
        # This step is irregular (to save the amount of matrix multiplication we have to do)
        # I will refer to this vector as [h X]
        zs = np.row_stack((h, wes))

        # compute the forget gate
        # f_gate = sigmoid (W_f \cdot [h X] + b_f)
        f_gate = sigmoid(np.dot(Wf, zs) + bf)

        # compute the input gate
        # i_gate = sigmoid (W_i \cdot [h X] + b_i)
        i_gate = sigmoid(np.dot(Wi, zs) + bi)

        # compute the candidate memory
        # \hat{c} = tanh (W_c \cdot [h X] + b_c])
        c_cand = np.tanh(np.dot(Wc, zs) + bc)

        # new memory: applying forget gate on the previous memory
        # and then adding the input gate on the candidate memory
        # c_new = f_gate * prev_c + i_gate * \hat{c}
        c = f_gate * c + i_gate * c_cand

        # output gate
        # o_gate = sigmoid (Wo \cdot [h X] + b_o)
        o_gate = sigmoid(np.dot(Wo, zs) + bo)

        # new hidden state for the LSTM
        # h = o_gate * tanh(c_new)
        h = o_gate * np.tanh(c)

        # o = Why \cdot h + by
        os = np.dot(Why, h) + by

        # softmax for probabilities for next chars
        # p = softmax(o)
        ps = softmax(os)

        ix = np.random.multinomial(1, ps.ravel())
        for j in range(len(ix)):
            if ix[j] == 1:
                index = j

        # Set the next char
        x = np.zeros((vocab_size, 1))
        x[index] = 1
        result += [index]

    return result

if option == 'train':

    n, p = 0, 0
    n_updates = 0

    # momentum variables for Adagrad
    mWex, mWhy = np.zeros_like(Wex), np.zeros_like(Why)
    mby = np.zeros_like(by)

    mWf, mWi, mWo, mWc = np.zeros_like(Wf), np.zeros_like(Wi), np.zeros_like(Wo), np.zeros_like(Wc)
    mbf, mbi, mbo, mbc = np.zeros_like(bf), np.zeros_like(bi), np.zeros_like(bo), np.zeros_like(bc)

    smooth_loss = -np.log(1.0/vocab_size)*seq_length # loss at iteration 0

    while True:
        # prepare inputs (we're sweeping from left to right in steps seq_length long)
        if p+seq_length+1 >= len(data) or n == 0:
            hprev = np.zeros((hidden_size,1)) # reset RNN memory
            cprev = np.zeros((hidden_size,1))
            p = 0 # go from start of data
        inputs = [char_to_ix[ch] for ch in data[p:p+seq_length]]
        targets = [char_to_ix[ch] for ch in data[p+1:p+seq_length+1]]

        # sample from the model now and then
        if n % 100 == 0:
            sample_ix = sample((hprev, cprev), inputs[0], 200)
            txt = ''.join(ix_to_char[ix] for ix in sample_ix)
            print ('----\n %s \n----' % (txt, ))

        # forward seq_length characters through the net and fetch gradient
        loss, activations, memory = forward(inputs, targets, (hprev, cprev))
        gradients = backward(activations)

        hprev, cprev = memory
        dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby = gradients
        smooth_loss = smooth_loss * 0.999 + loss * 0.001
        if n % 100 == 0: print ('iter %d, loss: %f' % (n, smooth_loss)) # print progress

        # perform parameter update with Adagrad
        for param, dparam, mem in zip([Wf, Wi, Wo, Wc, bf, bi, bo, bc, Wex, Why, by],
                                    [dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWex, dWhy, dby],
                                    [mWf, mWi, mWo, mWc, mbf, mbi, mbo, mbc, mWex, mWhy, mby]):
            mem += dparam * dparam
            param += -learning_rate * dparam / np.sqrt(mem + 1e-8) # adagrad update

        p += seq_length # move data pointer
        n += 1 # iteration counter
        n_updates += 1
        if n_updates >= max_updates:
            break

elif option == 'gradcheck':

    p = 0
    inputs = [char_to_ix[ch] for ch in data[p:p+seq_length]]
    targets = [char_to_ix[ch] for ch in data[p+1:p+seq_length+1]]

    delta = 0.001

    hprev = np.zeros((hidden_size, 1))
    cprev = np.zeros((hidden_size, 1))

    memory = (hprev, cprev)

    loss, activations, _ = forward(inputs, targets, memory)
    gradients = backward(activations, clipping=False)
    dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby = gradients

    for weight, grad, name in zip([Wf, Wi, Wo, Wc, bf, bi, bo, bc, Wex, Why, by],
                                   [dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWex    , dWhy, dby],
                                   ['Wf', 'Wi', 'Wo', 'Wc', 'bf', 'bi', 'bo', 'bc', 'Wex', 'Why', 'by']):

        str_ = ("Dimensions dont match between weight and gradient %s and %s." % (weight.shape, grad.shape))
        assert(weight.shape == grad.shape), str_

        print(name)
        for i in range(weight.size):

            # evaluate cost at [x + delta] and [x - delta]
            w = weight.flat[i]
            weight.flat[i] = w + delta
            loss_positive, _, _ = forward(inputs, targets, memory)
            weight.flat[i] = w - delta
            loss_negative, _, _ = forward(inputs, targets, memory)
            weight.flat[i] = w  # reset old value for this parameter

            grad_analytic = grad.flat[i]
            grad_numerical = (loss_positive - loss_negative) / ( 2 * delta )

            # compare the relative error between analytical and numerical gradients
            rel_error = abs(grad_analytic - grad_numerical) / abs(grad_numerical + grad_analytic)

            if rel_error > 0.01:
                print ('WARNING %f, %f => %e ' % (grad_numerical, grad_analytic, rel_error))
