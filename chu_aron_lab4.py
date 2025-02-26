from pyspark.ml import Pipeline
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("DecisionTreeClassification").getOrCreate()

data = spark.read.format("libsvm").load("/FileStore/tables/colon_cancer.txt")

labelIndexer = StringIndexer(inputCol="label", outputCol="indexedLabel").fit(data)

featureIndexer = VectorAssembler(inputCols=["features"], outputCol="indexedFeatures")

(trainingData, testData) = data.randomSplit([0.7, 0.3])

dt = DecisionTreeClassifier(labelCol="indexedLabel", featuresCol="indexedFeatures", maxDepth=5)


pipeline = Pipeline(stages=[labelIndexer, featureIndexer, dt])

model = pipeline.fit(trainingData)

predictions = model.transform(testData)

predictions.select("prediction", "indexedLabel", "features").show(5)

evaluator = MulticlassClassificationEvaluator(
    labelCol="indexedLabel", predictionCol="prediction", metricName="accuracy")
accuracy = evaluator.evaluate(predictions)
print(f"Test Error = {1.0 - accuracy}")

treeModel = model.stages[2]
print(treeModel.toDebugString)
