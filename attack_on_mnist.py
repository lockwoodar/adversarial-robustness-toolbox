import config
import json

import keras.backend as K
from keras.callbacks import ModelCheckpoint,TensorBoard

import tensorflow as tf

from cleverhans.attacks import fgsm
from cleverhans.utils_tf import model_train, model_eval, batch_eval

from src.classifiers import cnn
from src.utils import load_mnist,make_directory

BATCH_SIZE = 128
NB_EPOCHS = 20
VAL_SPLIT = 0.1
ACT="brelu"
FILEPATH = "./temp/mnist/{}/".format(ACT)

comp_params = {"loss":'categorical_crossentropy',
               "optimizer":'adam',
               "metrics":['accuracy']}


make_directory(FILEPATH)
#MODEL TRAINING
# get MNIST
(X_train, Y_train), (X_test, Y_test) = load_mnist()
# X_train, Y_train, X_test, Y_test = X_train[:1000], Y_train[:1000], X_test[:1000], Y_test[:1000]

im_shape = X_train[0].shape

session = tf.Session()
K.set_session(session)

# learn with bounded relu
model = cnn.cnn_model(im_shape,act=ACT)

# Fit the model
model.compile(**comp_params)

# Save best model weights
# checkpoint = ModelCheckpoint(FILEPATH+"best-weights.{epoch:02d}-{val_acc:.2f}.h5",monitor='val_acc',verbose=1,save_best_only=True,mode='max')
checkpoint = ModelCheckpoint(FILEPATH+"best-weights.h5",monitor='val_acc',verbose=1,save_best_only=True,mode='max')

# remote monitor
monitor = TensorBoard(log_dir=FILEPATH+'/logs',write_graph=False)

callbacks_list = [checkpoint,monitor]

history = model.fit(X_train,Y_train,validation_split=VAL_SPLIT,epochs=NB_EPOCHS,batch_size=BATCH_SIZE,callbacks=callbacks_list)

scores = model.evaluate(X_test,Y_test)

print("\naccuracy: %.2f%%" % (scores[1] * 100))

cnn.save_model(model,FILEPATH,comp_params)

# load model with best weights
model = cnn.load_model(FILEPATH,"best-weights.h5")

# ATTACK
#Define input TF placeholder
x = tf.placeholder(tf.float32, shape=(None,im_shape[0],im_shape[1],im_shape[2]))

predictions = model(x)

adv_results = {"adv_accuracies":[],
               "eps_values": [e/10 for e in range(11)]}

for eps in adv_results["eps_values"]:
    # craft adversarials with Fast Gradient Sign Method (FGSM)
    adv_x = fgsm(x, predictions, eps=eps)

    eval_params = {'batch_size': BATCH_SIZE}
    X_test_adv = batch_eval(session, [x], [adv_x], [X_test], args=eval_params)

    scores = model.evaluate(X_test_adv,Y_test)

    print("\naccuracy on adversarials with %2.1f epsilon: %.2f%%" % (eps,scores[1] * 100))

    adv_results["adv_accuracies"].append(scores[1]*100)

with open(FILEPATH+"adv-acc.json", "w") as json_file:
    json.dump(adv_results,json_file)