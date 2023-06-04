# Databricks notebook source
# MAGIC %md
# MAGIC # Databricks and GraphFrames 
# MAGIC An exploration of the two technologies using the [Amazon product co-purchasing network dataset](http://snap.stanford.edu/data/index.html#amazon).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Ingestion
# MAGIC
# MAGIC We each took different approaches to storing and reading the raw .txt files of our data. The first way is by using Azure Blob Storage and using Spark's built-in support for reading Azure Blob Storage files with an account access key. The other way to do it is by uploading data directly to Databricks and storing it in the [Databricks File System](https://learn.microsoft.com/en-us/azure/databricks/dbfs/). We explored both options!
# MAGIC
# MAGIC ### Connecting to data stored in Azure Blob Storage
# MAGIC Our raw data in the form of .txt files was first uploaded to Azure Blob Storage, where the files are securely stored. Azure Blob Storage is Azure's generic storage solution, and has the advantage of high scalability and availability and not being native to Databricks. It is likely that an organization on the cloud may already have files of interest stored in Blob Storage somewhere. Although this was done using Azure Blob Storage, a similar solution would exist for referencing data hosted in other clouds such as on AWS in S3 buckets.
# MAGIC

# COMMAND ----------

# Declare storage account information
storage_account_name = "amazonproductdata"
# TODO: don't store storage key here...
storage_account_access_key = "<Storage Key Here>"

# Set up connection
file_type = "csv"
spark.conf.set(
  "fs.azure.account.key."+storage_account_name+".blob.core.windows.net",
  storage_account_access_key)

# Define file paths
early_march_file_location = "wasbs://raw-data@amazonproductdata.blob.core.windows.net/amazon0302.txt"
late_march_file_location = "wasbs://raw-data@amazonproductdata.blob.core.windows.net/amazon0312.txt"
may_file_location = "wasbs://raw-data@amazonproductdata.blob.core.windows.net/amazon0505.txt"
june_file_location = "wasbs://raw-data@amazonproductdata.blob.core.windows.net/amazon0601.txt"
meta_file_location = "wasbs://raw-data@amazonproductdata.blob.core.windows.net/amazon-meta.txt"

# COMMAND ----------

# MAGIC %md
# MAGIC ### Connecting to data stored in the Databricks File System (DBFS)
# MAGIC Data can also be uploaded within the Databricks workspace UI to DBFS. This is convenient for many users and allows data to be uploaded and managed all in the same system. If flexibility or existing data are not concerns, this is a good option for getting started quickly without worrying about things like authentication to read files.

# COMMAND ----------

# TODO: file path declarations, overwriting azure storage ones

# COMMAND ----------

# MAGIC %md
# MAGIC ### Reading in the data and parsing it
# MAGIC Regardless of how the data was stored, we can simply reference the raw data files and parse them into DataFrames. DataFrames allow us to make the data tabular and manupulate the data with it intuitive APIs. 
# MAGIC
# MAGIC Like with storage, we each came up with slightly different ways to parse the edge data. Both are valid and show the flexibility of the Spark APIs!
# MAGIC
# MAGIC #### Reading edge data (using StructType)

# COMMAND ----------

# Edges
from pyspark.sql.types import StructType, StructField, IntegerType, StringType

# Change to string and rename to src, dst, add time added? 
conn_schema = StructType([
    StructField("FromNodeId", IntegerType(), True),
    StructField("ToNodeId", IntegerType(), True)
])

early_march_df = spark.read.format(file_type) \
    .option("delimiter", "\t") \
    .option("comment", "#") \
    .schema(conn_schema) \
    .load(early_march_file_location)

late_march_df = spark.read.format(file_type) \
    .option("delimiter", "\t") \
    .option("comment", "#") \
    .schema(conn_schema) \
    .load(late_march_file_location)

may_df = spark.read.format(file_type) \
    .option("delimiter", "\t") \
    .option("comment", "#") \
    .schema(conn_schema) \
    .load(may_file_location)

june_df = spark.read.format(file_type) \
    .option("delimiter", "\t") \
    .option("comment", "#") \
    .schema(conn_schema) \
    .load(june_file_location)

display(early_march_df)
display(late_march_df)
display(may_df)
display(june_df)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Reading edge data (using map)

# COMMAND ----------

# TODO: add reading edge data

# COMMAND ----------

# MAGIC %md
# MAGIC #### Reading product detail data (vertices)
# MAGIC Reading in the vertex data was more involved because the Amazon product metadata file did not come in a standard format like JSON or YAML. Luckily for us, the data was at least in a standard format. We first loaded each product into its own row, and then used a complex regular expression to extract the properties we cared about. On the initial read, splitting each product into its own row was important to avoid RAM limitations.

# COMMAND ----------

# Node metadata
from pyspark.sql.functions import col
from pyspark.sql import functions as F

regex = r'Id:\s*(\d+)\s*\nASIN:\s+(\w+)\s*\n\s*title:\s*([\w\W]+)\s*\r\n\s*group:\s+(.+)\s*\n\s*salesrank:\s*(-*\d+)\s*\n\s*similar:\s+(\d+)\s*(\d*.*?)\s*\n\s*categories:\s*(\d+)\s*\n\s*([\s\S]*)reviews:\s+total:\s+(\d+)\s+downloaded:\s+(\d+)\s+avg rating:\s+(\d+\.*\d*)\s*\n\s*([\s\S]*)'
df1 = spark.read.text(meta_file_location, lineSep="\r\n\r\n")
metadata_df = df1 \
        .withColumn("id", F.regexp_extract("value", r'(\d+)\s*\nASIN:\s+(\w+)\s*\n', 1)) \
        .withColumn("asin", F.regexp_extract("value", r'(\d+)\s*\nASIN:\s+(\w+)\s*\n', 2)) \
        .withColumn("title", F.regexp_extract("value", regex, 3)) \
        .withColumn("group", F.regexp_extract("value", regex, 4)) \
        .withColumn("salesrank", F.regexp_extract("value", regex, 5)) \
        .withColumn("similar_count", F.regexp_extract("value", regex, 6)) \
        .withColumn("similar", F.regexp_extract("value", regex, 7)) \
        .withColumn("categories_count", F.regexp_extract("value", regex, 8)) \
        .withColumn("categories", F.regexp_extract("value", regex, 9)) \
        .withColumn("reviews_total", F.regexp_extract("value", regex, 10)) \
        .withColumn("reviews_downloaded", F.regexp_extract("value", regex, 11)) \
        .withColumn("reviews_avg_rating", F.regexp_extract("value", regex, 12)) \
        .withColumn("reviews", F.regexp_extract("value", regex, 13)) \
        .withColumn("similar", F.split(F.col("similar"), "\s+").cast("array<string>")) \
        .withColumn("categories", F.split(F.col("categories"), "\r\n").cast("array<string>")) \
        .withColumn("reviews", F.split(F.col("reviews"), "\r\n").cast("array<string>")) \
        .where((F.col("id").isNotNull()) & (F.col("id") != ""))

display(metadata_df)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Saving Product Detail DataFrame to Delta Table
# MAGIC Although we first started with the DataFrame as-is, we found that some algorithms were very slow to run on just this data. Saving the parsed data into a Delta Table and then referencing the Delta Table values was a simple way to get a ~20x performance boosts (and better traceability for any changed values!).

# COMMAND ----------

# Save dataframe as delta table
metadata_df.write.saveAsTable("product_metadata")

# COMMAND ----------

# Reference delta table for dataframe 
node_metadata_df = spark.table("product_metadata")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Answering Query Questions
# MAGIC As part of the assignment, there were 6 questions to be answered from this dataset. The queries below answer the 6 questions.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Q1: What are the percentages of each rating digit for the product with id: 21?
# MAGIC
# MAGIC #### Answer:
# MAGIC | Rating | Count | Percentage |
# MAGIC |--------|-------|------------|
# MAGIC | 5      | 100   | 71.43%     |
# MAGIC | 4      | 30    | 21.43%     |
# MAGIC | 3      | 3     | 2.14%      |
# MAGIC | 2      | 3     | 2.14%      |
# MAGIC | 1      | 4     | 2.86%      |
# MAGIC
# MAGIC

# COMMAND ----------

from pyspark.sql import functions as F

# Filter the DataFrame to only include rows where the id column is equal to 21
product_21_df = node_metadata_df.filter(F.col("id") == "21")

# Explode each review entry into multiple rows and extract rating
product_21_reviews_df = product_21_df.select(F.explode("reviews").alias("review"))
product_21_reviews_df = product_21_reviews_df.withColumn("rating", F.regexp_extract("review", r"rating:\s+(\d+)", 1))

# Count the number of occurrences of each rating
rating_counts_df = product_21_reviews_df.groupBy("rating").count()

# Calculate the percentage of each rating
total_ratings = rating_counts_df.agg(F.sum("count")).collect()[0][0]
rating_percentages_df = rating_counts_df.withColumn("percentage", (F.col("count") / total_ratings) * 100)

# Sort the result by the rating column in descending order
rating_percentages_df = rating_percentages_df.orderBy(F.col("rating").desc())

# Display the result
display(rating_percentages_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Q2: Which pairs of products have consistently stayed within each other’s “Customers who bought this item also bought” lists through march, may and June of 2003?
# MAGIC
# MAGIC #### Answer:
# MAGIC There are 1,346 products that stayed consistently within each other's “Customers who bought this item also bought” lists.
# MAGIC
# MAGIC See the `consistent_bidirectional_edges` DataFrame for exact customer Id's.

# COMMAND ----------

from pyspark.sql import functions as F

# Create a temporary view for each DataFrame
early_march_df.createOrReplaceTempView("early_march")
late_march_df.createOrReplaceTempView("late_march")
may_df.createOrReplaceTempView("may")
june_df.createOrReplaceTempView("june")

# Find bidirectional edges in each DataFrame
bidirectional_edges_early_march = spark.sql("""
    SELECT DISTINCT e1.FromNodeId, e1.ToNodeId
    FROM early_march e1
    JOIN early_march e2
    ON e1.FromNodeId = e2.ToNodeId AND e1.ToNodeId = e2.FromNodeId
""")

bidirectional_edges_late_march = spark.sql("""
    SELECT DISTINCT l1.FromNodeId, l1.ToNodeId
    FROM late_march l1
    JOIN late_march l2
    ON l1.FromNodeId = l2.ToNodeId AND l1.ToNodeId = l2.FromNodeId
""")

bidirectional_edges_may = spark.sql("""
    SELECT DISTINCT m1.FromNodeId, m1.ToNodeId
    FROM may m1
    JOIN may m2
    ON m1.FromNodeId = m2.ToNodeId AND m1.ToNodeId = m2.FromNodeId
""")

bidirectional_edges_june = spark.sql("""
    SELECT DISTINCT j1.FromNodeId, j1.ToNodeId
    FROM june j1
    JOIN june j2
    ON j1.FromNodeId = j2.ToNodeId AND j1.ToNodeId = j2.FromNodeId
""")

# Find bidirectional edges that are present in all DataFrames
consistent_bidirectional_edges = bidirectional_edges_early_march \
 .intersect(bidirectional_edges_late_march) \
 .intersect(bidirectional_edges_may) \
 .intersect(bidirectional_edges_june)

# Display the result
display(consistent_bidirectional_edges)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Q3: For a product “A” in group “G”, at what level do you find a product of a different group in the June 1st dataset? 
# MAGIC
# MAGIC For any user specified product A (choose 1 random product) belonging to group G, if you consider the “Customers who bought this item also bought” list of June 01 to be level 0 and for each of the items in that list if you consider their “Customers who bought this item also bought” list of June 01 except A as level 1, then for each of those product’s own “Customers who bought this item also bought” list of June 01 except A as level 2 and so on, at what level do you find a product of a different group? Show the chain of products and their groups that were traversed, till you reach a different group. 
# MAGIC
# MAGIC
# MAGIC Levels explained:
# MAGIC ```
# MAGIC Level 0: A : { “Customers who bought this item also bought” list of June 01: [B, C]}
# MAGIC 	Level 1: B: {“Customers who bought this item also bought” list of June 01: [A, D, E]}
# MAGIC 	Level 1: C: {“Customers who bought this item also bought” list of June 01: [A, F, G]}
# MAGIC 		Level 2: D: {“Customers …” list of June 01: [A, H, I]}
# MAGIC 		Level 2: E: {“Customers …” list of June 01: [A, J, K]}
# MAGIC 		Level 2: F: {“Customers …” list of June 01: [A, L, M]}
# MAGIC 		Level 2: G: {“Customers …” list of June 01: [A, N, O]}
# MAGIC 			Level 3: H
# MAGIC 			Level 3: I
# MAGIC 			.
# MAGIC 			.
# MAGIC 			Level 3: O
# MAGIC 		Results expected:
# MAGIC 			Level 0: Product A: Group 1
# MAGIC 			Level 1: Product B: Group 1, Product C: Group 1
# MAGIC 			Level 2: Product D: Group 1, Product E: Group 1 … 
# MAGIC 			.
# MAGIC 			.
# MAGIC 			Level n:		.	.	 Product n: Group 2
# MAGIC ```
# MAGIC
# MAGIC #### Answer:
# MAGIC For two products I explored, both were found to have related items at a different group at level 1.
# MAGIC
# MAGIC ```
# MAGIC "The Casebook of Sherlock Holmes, Volume 2 (Casebook of Sherlock Holmes)" (id: 24, category: Book) =>  "Jonny Quest - Bandit in Adventures Best Friend" (id: 71, category: Video)
# MAGIC ```
# MAGIC And
# MAGIC ```
# MAGIC "Life Application Bible Commentary: 1 and 2 Timothy and Titus" (id: 4, category: Book) => "The NBA's 100 Greatest Plays" (id: 44, category: DVD)
# MAGIC ```

# COMMAND ----------

# Create graph
from graphframes import *

edges = june_df.selectExpr("FromNodeId as src", "ToNodeId as dst")
g = GraphFrame(node_metadata_df, edges)

# COMMAND ----------

# Product 1 search
start_title = "The Casebook of Sherlock Holmes, Volume 2 (Casebook of Sherlock Holmes)"
start_node = g.vertices.filter(f"title = '{start_title}'")
start_node_group = start_node.select("group").collect()[0][0]
start_node_id = start_node.select("id").collect()[0][0]

paths = g.bfs(f"id = {start_node_id}", f"group != '{start_node_group}' AND group != ''", maxPathLength=3).limit(1)
paths.show()

# COMMAND ----------

# Product 2 search
start_title = "Life Application Bible Commentary: 1 and 2 Timothy and Titus"
start_node = g.vertices.filter(f"title = '{start_title}'")
start_node_group = start_node.select("group").collect()[0][0]
start_node_id = start_node.select("id").collect()[0][0]

paths = g.bfs(f"id = {start_node_id}", f"group != '{start_node_group}' AND group != ''", maxPathLength=5).limit(1)
paths.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## GraphFrames Exploration
# MAGIC After answering those questions, we wanted to explore a little bit more. Specifically, we wanted to see what we could do with the GraphFrames APIs.