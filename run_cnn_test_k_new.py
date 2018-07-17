from __future__ import print_function
import inbreast
import keras.backend as K
from roc_auc import RocAucScoreOp, PrecisionOp, RecallOp, F1Op
from roc_auc import AUCEpoch, PrecisionEpoch, RecallEpoch, F1Epoch, LossEpoch, ACCEpoch
#from keras.preprocessing.image import ImageDataGenerator
from image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten, BatchNormalization, SpatialDropout2D
from keras.layers import advanced_activations
from keras.layers import Convolution2D, MaxPooling2D
from keras.optimizers import SGD, Adam, RMSprop
from keras.utils import np_utils
import numpy as np
from keras.callbacks import ModelCheckpoint
from keras.regularizers import l1l2
import inbreast
from convnetskeras.convnets import preprocess_image_batch, convnet
import os
from sklearn.metrics import roc_auc_score,roc_curve
np.random.seed(1)
#srng = RandomStreams(1)
fold = 2 # 4
valfold = 4
lr = 5e-5 #1e-3 #5e-5 #5e-5
nb_epoch = 500
batch_size = 80
l2factor = 1e-5
l1factor = 0#2e-7
weighted = False #False #True
noises = 50
data_augmentation = True
modelname = 'alexnet' # miccai16, alexnet, levynet, googlenet
pretrain = True #True #True
savename = modelname+'new_fd'+str(fold)+'_vf'+str(valfold)+'_lr'+str(lr)+'_l2'+str(l2factor)+'_l1'\
+str(l1factor)+'_ep'+str(nb_epoch)+'_bs'+str(batch_size)+'_w'+str(weighted)+'_dr'+str(False)+str(noises)+str(pretrain)
print(savename)
nb_classes = 2
# input image dimensions
img_rows, img_cols = 227, 227
# the CIFAR10 images are RGB
img_channels = 1

# the data, shuffled and split between train and test sets
trX, y_train, teX, y_test, teteX, y_test_test = inbreast.loaddataenhance(fold, 5, valfold=valfold)
trY = y_train.reshape((y_train.shape[0],1))
teY = y_test.reshape((y_test.shape[0],1))
teteY = y_test_test.reshape((y_test_test.shape[0],1))
print('tr, val, te pos num and shape')
print(trY.sum(), teY.sum(), teteY.sum(), trY.shape[0], teY.shape[0], teteY.shape[0])
ratio = trY.sum()*1./trY.shape[0]*1.
print('tr ratio'+str(ratio))
weights = np.array((ratio, 1-ratio))
#trYori = np.concatenate((1-trY, trY), axis=1)
#teY = np.concatenate((1-teY, teY), axis=1)
#teteY = np.concatenate((1-teteY, teteY), axis=1)
X_train = trX.reshape(-1, img_channels, img_rows, img_cols)
X_test = teX.reshape(-1, img_channels, img_rows, img_cols)
X_test_test = teteX.reshape(-1, img_channels, img_rows, img_cols)
print('tr, val, te mean, std')
print(X_train.mean(), X_test.mean(), X_test_test.mean())
# convert class vectors to binary class matrices
Y_train = np.zeros((y_train.shape[0],2))
Y_train[:,0] = 1-y_train
Y_train[:,1] = y_train #np_utils.to_categorical(y_train, nb_classes)
Y_test = np.zeros((y_test.shape[0],2))
Y_test[:,0] = 1-y_test
Y_test[:,1] = y_test #np_utils.to_categorical(y_test, nb_classes)
Y_test_test = np.zeros((y_test_test.shape[0],2)) 
Y_test_test[:,0] = 1-y_test_test
Y_test_test[:,1] = y_test_test #np_utils.to_categorical(y_test_test, nb_classes)
print('X_train shape:', X_train.shape)
print(X_train.shape[0], 'train samples')
print(X_test.shape[0], 'val samples')
print(X_test_test.shape[0], 'test samples')
model = Sequential()
if modelname == 'alexnet':
  X_train_extend = np.zeros((X_train.shape[0],3, 227, 227))
  for i in xrange(X_train.shape[0]):
    rex = np.resize(X_train[i,:,:,:], (227, 227))
    X_train_extend[i,0,:,:] = rex
    X_train_extend[i,1,:,:] = rex
    X_train_extend[i,2,:,:] = rex
    X_train = X_train_extend
  X_test_extend = np.zeros((X_test.shape[0], 3,227, 227))
  for i in xrange(X_test.shape[0]):
    rex = np.resize(X_test[i,:,:,:], (227, 227))
    X_test_extend[i,0,:,:] = rex
    X_test_extend[i,1,:,:] = rex
    X_test_extend[i,2,:,:] = rex
  X_test = X_test_extend
  X_test_test_extend = np.zeros((X_test_test.shape[0], 3, 227, 227))
  for i in xrange(X_test_test.shape[0]):
    rex = np.resize(X_test_test[i,:,:,:], (227,227))
    X_test_test_extend[i,0,:,:] = rex
    X_test_test_extend[i,1,:,:] = rex
    X_test_test_extend[i,2,:,:] = rex
  X_test_test = X_test_test_extend
  alexmodel = convnet('alexnet', weights_path='alexnet_weights.h5', heatmap=False)
  model = convnet('alexnet', outdim=2)
  if pretrain:
    for layer, mylayer in zip(alexmodel.layers, model.layers):
      print(layer.name)
      if layer.name == 'dense_3':
        break
      else:
        weightsval = layer.get_weights()
        print(len(weightsval))
        mylayer.set_weights(weightsval)

X_test_test = X_test_test.astype('float32')
for f in os.listdir('./'):
  metrics = ['loss', 'auc', 'f1', 'acc', 'reca', 'prec']
  for m in metrics:
    if f.endswith('.hdf5') and f.startswith(savename+m):
      print(f)
      weightname = f
      model.load_weights(weightname)
      y_pred = model.predict(X_test_test)
      print(y_pred.shape, Y_test_test.shape)
      score = roc_auc_score(Y_test_test[:,1], y_pred[:,1])
      fpr, tpr, _ = roc_curve(Y_test_test[:,1], y_pred[:,1])
      #np.savetxt('fpr.txt', fpr)
      #np.savetxt('tpr.txt', tpr)
      y_true = np.argmax(Y_test_test, axis=1)
      y_score = np.argmax(y_pred, axis=1)
      TP = np.sum(y_true[y_score==1]==1)*1. / sum(y_true)
      FP = np.sum(y_true[y_score==1]==0)*1. / (y_true.shape[0]-sum(y_true))
      prec = TP / (TP+FP+1e-6)
      TP = np.sum(y_true[y_score==1]==1)*1. / sum(y_true)
      FN = np.sum(y_true[y_score==0]==1)*1. / sum(y_true)
      reca = TP / (TP+FN+1e-6)
      f1 = 2*prec*reca / (prec+reca+1e-6)
      acc = np.mean(y_true == y_score)
      print(acc, score, prec, reca, f1)