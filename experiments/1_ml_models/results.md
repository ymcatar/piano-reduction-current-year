# Experiment: ML models (25 Sep 2017)

We try multiple models on the existing feature set defined by Cherry. All models
are taken from scikit-learn.

The training data is from Beethoven Op. 18 No. 1-4. The testing data is from
**Spring Sonata I**.

## Control: 1-layer neural network

![](output/nn-1.png)

[Download XML](output/nn.xml)

## Support vector machine

![](output/svm-1.png)

[Download XML](output/svm.xml)

One reason this did not work well is that I did not normalize (whiten) the input
data. More experimentation needed.

## Logistic regression (= 0-layer neural network)

![](output/logistic-1.png)

[Download XML](output/logistic.xml)

Compared to the 1-layer neural network, this probably has less overfitting.

## Decision tree (depth=7)

![](output/dtree-1.png)

[Download XML](output/dtree.xml)

Depth = 7 is where the model starts to overfit. Depth values around this number
yield similarly bad results.

## Random forest (ensemble size=10)

![](output/rforest-1.png)

[Download XML](output/rforest.xml)

Unsurprisingly, random forest is a very good out-of-the-box classifier.

## Concluding remarks

These experiments show that we will be in need of much more data for training as
we increase the number of features and the complexity of the models. Otherwise,
the models will easily overfit.
