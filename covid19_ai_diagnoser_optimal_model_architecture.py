# -*- coding: utf-8 -*-
"""covid19_ai_diagnoser_optimal_model_architecture.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eHENe0ASeeR4Gi4sdmDfj1my2ajYrsYd
"""

! pip install tensorflow==2.12.*

# General libraries

import os
import numpy as np
import random
import cv2

# Deep learning libraries
import tensorflow as tf
import keras.backend as K
from keras.models import Model,Sequential
from keras.layers import Input,Dense,Flatten,Dropout,BatchNormalization
from keras.layers import Conv2D,SeparableConv2D,MaxPool2D,LeakyReLU,Activation
from keras.optimizers import Adam
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import ModelCheckpoint,ReduceLROnPlateau,EarlyStopping

""" > We can look at X-ray images and how each dataset is distributed """

# Global Utility

# Hyperparameters
img_dims=150
batch_size=32
epochs=10

"""# **Result**

It is good practice to visualize train vs. validation accuracy and loss. This gives you insight on what an adequate number of epochs is while also helping you determine if you are overfitting to the training set.

> *Finally, analyze the metrics of your model so you can decide which metric you would like to optimize for. Recall is a good measure of fit in this case since you would like to catch as many positive cases as posible to prevent spreading the disease (although only certain types of pneumonia are contagious).*
"""

# Util Component 1 : Confusion matrix report/Accuracy measures

from sklearn.metrics import accuracy_score,confusion_matrix

# For graphical confusion matrix
import matplotlib.pyplot as plt
import seaborn as sns

def renderConfusionMetrics(__model,_testData,enableTraining,__train_gen,__test_gen,__batch_size,__epochs,hdf5_testSaveFileName,plotpng):
  preds=__model.predict(_testData)

  acc=accuracy_score(_testLabels,np.round(preds))*100
  cm=confusion_matrix(_testLabels,np.round(preds))
  tn,fp,fn,tp=cm.ravel()
  plt.clf()
  plt.style.use("grayscale")
  group_names=['True Neg','False Pos','False Neg','True Pos']
  group_counts=["{0:0.0f}".format(value) for value in cm.ravel()]
  group_percentages=["{0:.2%}".format(value) for value in cm.ravel()/np.sum(cm)]
  labels=[f"{v1}\n{v2}\n{v3}" for v1,v2,v3 in zip(group_names,group_counts,group_percentages)]
  labels=np.asarray(labels).reshape(2,2)
  sns.heatmap(cm,annot=labels,fmt='',cmp='Blues')
  plt.savefig(plotpng+'.jpg')
  plt.figure()
  print('\nCONFUSION MATRIX FORMAT ------------------\n')
  print("[true positives false positives]")
  print("[false negatives true negatives]\n\n")

  print('CONFUSION MATRIX -----------')
  print(cm)

  print('\nTEST METRICS ------------')
  precision=tp/(tp+fp)*100
  recall=tp/(tp+fn)*100
  specificity=tn/(tn+fp)*100
  print('Accuracy: {}%'.format(acc))
  print('Precision: {}%'.format(precision))
  print('Recall :{}%'.format(recall))
  print('Specificity :{}%'.format(specificity))
  print('F1-score: {}%'.format(2*precision*recall/(precision+recall)))

  if enableTraining:
    checkpoint= ModelCheckpoint(filepath=hdf5_testSaveFileName, save_best_only=True, save_weights_only=True)
    lr_reduce= ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=2, verbose=2, mode='max')
    early_stop= EarlyStopping(monitor='val_loss', min_delta=0.1, patience=1, mode='min')

    hist=__model.fit_generator(
         __train_gen,steps_per_epoch=__test_gen.samples,
         epochs=__epochs,validation_data=__test_gen,
         validation_steps=__test_gen.samples,callbacks=[checkpoint,lr_reduce])
    print('\nTRAIN METRIC ---------------')
    print('Covid19 Train acc:{}'.format(np.round((hist.history['acc'][-1])*100,2)))

"""# **The Model**

> *We can beat everything with depthwise convolution. I learn about separable depthwise convolution and implement it in my model. My results were instantly better when swapping out the convolutional blocks with these types of layers*
"""

# Util Component 2 : Model architecture description

def defineModelArchitecture(_img_dims):
  # Input layer
  inputs=Input(shape=(_img_dims,_img_dims,3))

  # First conv block
  x=Conv2D(filters=16,kernal_size=(3,3),activation='relu',padding='same')(inputs)
  x=Conv2D(filters=16,kernal_size=(3,3),activation='relu',padding='same')(x)
  x=MaxPool2D(pool_size=(2,2))(x)

  # Second conv block
  x=SeparableConv2D(filters=32,kernel_size=(3,3),activation='relu',padding='same')(x)
  x=SeparableConv2D(filters=32,kernel_size=(3,3),activation='relu',padding='same')(x)
  x=BatchNormalization()(x)
  x=MaxPool2D(pool_size=(2,2))(x)

  # Third conv block

  x = SeparableConv2D(filters=64, kernel_size=(3, 3), activation='relu', padding='same')(x)
  x = SeparableConv2D(filters=64, kernel_size=(3, 3), activation='relu', padding='same')(x)
  x = BatchNormalization()(x)
  x = MaxPool2D(pool_size=(2, 2))(x)

  # Fourth conv block
  x = SeparableConv2D(filters=128, kernel_size=(3, 3), activation='relu', padding='same')(x)
  x = SeparableConv2D(filters=128, kernel_size=(3, 3), activation='relu', padding='same')(x)
  x = BatchNormalization()(x)
  x = MaxPool2D(pool_size=(2, 2))(x)
  x = Dropout(rate=0.2)(x)

  # Fifth conv block

  x = SeparableConv2D(filters=256, kernel_size=(3, 3), activation='relu', padding='same')(x)
  x = SeparableConv2D(filters=256, kernel_size=(3, 3), activation='relu', padding='same')(x)
  x = BatchNormalization()(x)
  x = MaxPool2D(pool_size=(2, 2))(x)
  x = Dropout(rate=0.2)(x)

  # FC layer
  x=Flatten()(x)
  x=Dense(units=512,activation='relu')(x)
  x=Dropout(rate=0.7)(x)
  x=Dense(units=128,activation='relu')(x)
  x=Dropout(rate=0.5)(x)
  x=Dense(units=64,activation='relu')(x)
  x=Dropout(rate=0.3)(x)

  # Output layer
  output=Dense(units=1,activation='sigmoid')(x)

  return inputs,output

"""# **Preparing the data to the model**

> *Using Keras ImageDataGenerator() and .flow_from_directory()  we can feed data from the directory since it is already organized by class while also feeding augmented copies of data. This ensures that we don't run out of memory while training the model.*

# **Image Pre-Processing**

> Before training,you'll first modify your images to be better suited for training a convolutional neural network. For this task, you'll use Keras ImageDataGenerator to perform data preprocessing and data augmentation.


* This class also provides support for basic data augmentation such as random horizontal flipping of images.

* We also use the generator to transform the values in each batch so that their mean is 0 and their standard deviation is 1 (this will faciliate model training by standardizing the input distribution).

* The generator also converts our single channel X-ray images (gray-scale) to a three-channel format by repeating the values in the image across all channels (we will want this because the pre-trained model that we'll use requires three-channel inputs
"""

#Util Component 3 : Data processing

def process_data(__inputPath,img_dims,batch_size):

  # Data generation objects
  train_datagen=ImageDataGenerator(rescale=1./255,zoom_range=0.3,vertical_flip=True)
  test_val_datagen=ImageDataGenerator(rescale=1./255)

  # This is fed to the network in the specified batch sizes and image dimensions

  train_gen=train_datagen.flow_from_directory(
  directory=__inputPath+'test',
  target_size=(img_dims,img_dims),
  batch_size=batch_size,
  class_mode='binary',    
  shuffle=True)

  test_gen=test_val_datagen.flow_from_directory(
  directory=__inputPath + 'test',
  target_size=(img_dims,img_dims),
  batch_size=batch_size,
  class_mode='binary',    
  shuffle=True)

  # I will be making predictions of the test set in one batch size
  # This is useful to be able to get the confusion matrix

  test_data=[]
  test_labels=[]

  for cond in ['/NORMAL/','/PNEUMONIA/']:
    for img in (os.listdir(__inputPath + 'test' + cond)):
      img=cv2.imread(__inputPath + 'test' + cond+img,0)
      img=cv2.resize(img,(img_dims,img_dims))
      img=np.dstack([img,img,img])
      img=img.astype('float32')/255
      if cond=='/NORMAL/':
        label=0
      elif cond=='/PNEUMONIA/':
        label=1
      test_data.append(img)
      test_labels.append(label)  

  test_data=np.array(test_data)
  test_labels=np.array(test_labels)
  return train_gen,test_gen,test_data,test_labels

"""# **✔️ Build a separate generator fo valid and test sets**

> Look back at the generator we wrote for the training data.

* It normalizes each image per batch, meaning thatit uses batch statistics.
* We should not do this with the test and validation data, since in a real life scenario we don't process incoming images a batch at a time (we process one image at a time).
* Knowing the average per batch of test data would effectively give our model an advantage (The model should not have any information about the test data).
"""

#Util Component 4: Report file distributions
#directoryProcessArray eg,=['train','val','test'], in the case that training val and test folders exists in sub dir for processing.

def reportFileDistributions(__inputPath,directoryProcessArray):
  for _set in directoryProcessArray:
    n_normal=len(os.listdir(__inputPath+_set+'/NORMAL/'))
    n_infect=len(os.listdir(__inputPath+_set+'/PNEUMONIA'))
    print('Set:{},normal images :{},illness-positive images:{}'.format(_set,n_normal,n_infect))

#disable warnings
import logging
logging.getLogger('tensorflow').disabled=True

# Setting seeds for reproducibility
seed=232
np.random.seed(seed)
tf.random.set_seed(seed)

"""# 🤖 Model Building

> *One of the challenges while working with medical diagnostic datasets is the large class imbalance present in such datasets.*



## When we have an imbalance data, using a normal loss function will result a model that bias toward the dominating class. One solution is to use a weighted loss function. Using weighted loss function will balance the contribution in the loss function.
"""

#SECTION A: MODEL ARCHITECTURE NON-COVID19 PNEUMONIA DETECTOR

inputs,output=defineModelArchitecture(img_dims)

# Creating model and compiling
model_pneumoniaDetector=Model(inputs=inputs,outputs=output)
model_pneumoniaDetector.compile(optimizer='adam',loss='bibary_crossentropy',metrics=['accuracy'])
model_pneumoniaDetector.load_weights('best_weights_kaggle_user_pneumonia2_0.hdf5')

#Section B : NON-COVID19 PNEUMONIA VS NORMAL LUNG ACCURACY REPORT

print('\n\n#######TRAINED NON-COVID19 PNEUMONIA VS NORMAL LUNG TEST REPORT [LOADED MODEL/WEIGHTS]')

input_path_b='xray_dataset/'

# Report file distributions
reportFileDistributions(input_path_b,['train','val','test'])

# Getting the data

train_gen,test_gen,test_data_b,test_labels_b=process_data(input_path_b,img_dims,batch_size)

# Reporting on accuracies

renderConfusionMetrics ( model_pneumoniaDetector, test_data_b, test_labels_b, False, None, None, None, None, None,'pneumoniaCM')

#SECTION C : MODEL ARCHITECTURE COVID19 DETECTOR

inputs,output = defineModelArchitecture(img_dims)

# Creating model and compiling

model_covid19PneumoniaDetector = Model(inputs=inputs,outputs=output)
model_covid19PneumoniaDetector.compile(optimizer='adam',loss='binary_crossentropy',metrics=['accuracy'])
model_covid19PneumoniaDetector.load_weights('covid19_neural_network_weights_jordan.hdf5')


# SECTION D : COVID19 PNEUMONIA VS NORMAL LUNG ACCURACY REPORT

print('\n\n#######TRAINED COVID19 PNEUMONIA VS NORMAL LUNG TEST REPORT')

# custom_path for covid 19 test data
input_path_d='xray_dataset_covid19/'

# Report file distributions
reportFileDistributions(input_path_d,['train','test'])

# Getting the data

train_gen_d,test_gen_d,test_data_d,test_labels_d=process_data(input_path_d,img_dims,batch_size)

# Reporting on accuracies

renderConfusionMetrics(model_covid19PneumoniaDetector,test_data_d,test_labels_d,False,train_gen_d,test_gen_d,batch_size,11,'covid19_neural_network_weights_jordan_v2.hdf5','covid19PneumoniaCM')