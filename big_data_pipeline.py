import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import findspark
# This line helps PySpark find the Spark installation automatically if it's not in PATH
# It's good practice for local development.
findspark.init()

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, avg, count, date_format

# --- Configuration ---
NUM_SAMPLES = 5_000_000 # Number of records for the synthetic dataset
DATA_FILENAME = 'large_synthetic_data.csv'
ANALYSIS_REPORT_FILENAME = 'analysis_report.txt'
SPARK_DRIVER_MEMORY = "4g" # Memory allocated to Spark driver for local mode

# --- Function 1: Generate Large Synthetic Data ---
def generate_large_data(num_samples=NUM_SAMPLES, filename=DATA_FILENAME):
    """
    Generates a large synthetic dataset simulating transactional data and saves it to a CSV file.

    Args:
        num_samples (int): The number of transactional records to generate.
        filename (str): The name of the CSV file to save the data to.
    """
    print(f"--- Generating {num_samples:,} Synthetic Large Data Samples ---")
    np.random.seed(42) # for reproducibility

    # Generate Dates over a few years
    start_date = datetime(2020, 1, 1)
    dates = [start_date + timedelta(days=np.random.randint(0, 1095)) for _ in range(num_samples)] # 3 years of data

    # Generate other features
    regions = ['North', 'South', 'East', 'West', 'Central']
    product_categories = ['Electronics', 'Clothing', 'Home Goods', 'Books', 'Food', 'Software', 'Services']
    payment_methods = ['Credit Card', 'Debit Card', 'PayPal', 'Bank Transfer']
    customer_ids = np.random.randint(10000, 99999, num_samples) # Simulate customer IDs

    data = {
        'TransactionID': np.arange(1, num_samples + 1),
        'Date': dates,
        'CustomerID': customer_ids,
        'Region': np.random.choice(regions, num_samples),
        'ProductCategory': np.random.choice(product_categories, num_samples),
        'UnitsSold': np.random.randint(1, 10, num_samples),
        'PricePerUnit': np.random.uniform(5, 1000, num_samples),
        'PaymentMethod': np.random.choice(payment_methods, num_samples),
        'ShippingCost': np.random.uniform(0, 25, num_samples)
    }

    df = pd.DataFrame(data)

    # Calculate TotalAmount and Profit
    df['TotalAmount'] = df['UnitsSold'] * df['PricePerUnit'] + df['ShippingCost']
    df['Profit'] = df['TotalAmount'] * np.random.uniform(0.1, 0.4, num_samples) - np.random.uniform(0, 5, num_samples)
    df['Profit'] = df['Profit'].apply(lambda x: max(0.5, x)) # Ensure profit is positive

    # Format Date column
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d') # Store as YYYY-MM-DD string

    print(f"Saving data to '{filename}'...")
    df.to_csv(filename, index=False)
    print(f"Synthetic data saved to '{filename}' (File size: {os.path.getsize(filename) / (1024*1024):.2f} MB)")
    print("\nDataset head:\n", df.head())
    # For very large dataframes, df.info() and df.describe() can be slow,
    # showing head is usually sufficient for quick check.
    # df.info(verbose=False, show_counts=False)
    # print("\nDataset description:\n", df.describe())

# --- Function 2: Perform Big Data Analysis with PySpark ---
def analyze_big_data(data_filename=DATA_FILENAME, report_filename=ANALYSIS_REPORT_FILENAME):
    """
    Initializes Spark, loads data, performs analysis, and saves insights to a report.
    """
    # --- 2. Initialize Spark Session ---
    print("--- Initializing Spark Session ---")
    spark = SparkSession.builder \
        .appName("BigDataAnalysisPipeline") \
        .config("spark.driver.memory", SPARK_DRIVER_MEMORY) \
        .getOrCreate()
    print("Spark Session initialized successfully.")

    # --- 3. Load Data ---
    print(f"\n--- Loading Data from {data_filename} into Spark DataFrame ---")
    try:
        df_spark = spark.read.csv(data_filename, header=True, inferSchema=True)
        print("Data loaded into Spark DataFrame successfully.")
        print("Spark DataFrame Schema:")
        df_spark.printSchema()
        print("First 5 rows of Spark DataFrame:")
        df_spark.show(5)
        print(f"Total rows in Spark DataFrame: {df_spark.count():,}")
    except Exception as e:
        print(f"Error loading data: {e}")
        print(f"Please ensure '{data_filename}' exists. It should have been generated by this script.")
        spark.stop()
        exit()

    # --- 4. Perform Analysis and Derive Insights ---
    print("\n--- Performing Big Data Analysis ---")

    # Insight 1: Total Sales and Profit by Region
    print("\nInsight 1: Total Sales and Profit by Region")
    sales_by_region = df_spark.groupBy("Region").agg(
        sum("TotalAmount").alias("TotalSales"),
        sum("Profit").alias("TotalProfit")
    ).orderBy(col("TotalSales").desc())
    sales_by_region.show()

    # Insight 2: Top 5 Product Categories by Sales
    print("\nInsight 2: Top 5 Product Categories by Sales")
    top_products = df_spark.groupBy("ProductCategory").agg(
        sum("TotalAmount").alias("TotalSales")
    ).orderBy(col("TotalSales").desc()).limit(5)
    top_products.show()

    # Insight 3: Monthly Sales Trend
    print("\nInsight 3: Monthly Sales Trend")
    monthly_sales = df_spark.withColumn("YearMonth", date_format(col("Date"), "yyyy-MM")) \
        .groupBy("YearMonth").agg(
            sum("TotalAmount").alias("MonthlySales")
        ).orderBy("YearMonth")
    monthly_sales.show(50) # Show more months if available

    # Insight 4: Average Transaction Value by Payment Method
    print("\nInsight 4: Average Transaction Value by Payment Method")
    avg_transaction_value = df_spark.groupBy("PaymentMethod").agg(
        avg("TotalAmount").alias("AverageTransactionValue"),
        count("TransactionID").alias("NumberOfTransactions")
    ).orderBy(col("NumberOfTransactions").desc())
    avg_transaction_value.show()

    # Insight 5: Number of Transactions per Customer (top 10 customers)
    print("\nInsight 5: Top 10 Customers by Number of Transactions")
    top_customers = df_spark.groupBy("CustomerID").agg(
        count("TransactionID").alias("NumberOfTransactions"),
        sum("TotalAmount").alias("TotalSpent")
    ).orderBy(col("NumberOfTransactions").desc()).limit(10)
    top_customers.show()


    # --- 5. Save Insights to a Report File ---
    print(f"\n--- Saving Analysis Report to '{report_filename}' ---")
    with open(report_filename, 'w') as f:
        f.write("--- Big Data Analysis Report ---\n\n")

        f.write("Insight 1: Total Sales and Profit by Region\n")
        # Convert Spark DataFrame to HTML table string for better readability in text file
        # This is a workaround to get a somewhat formatted table in a plain text file.
        # For true HTML output, you'd save to an .html file or use a dedicated reporting tool.
        sales_by_region_html = sales_by_region._repr_html_()
        f.write(sales_by_region_html.replace('<table', '<table border="1"').replace('<th>', '<th style="padding: 5px;">').replace('<td>', '<td style="padding: 5px;">'))
        f.write("\n\n")

        f.write("Insight 2: Top 5 Product Categories by Sales\n")
        top_products_html = top_products._repr_html_()
        f.write(top_products_html.replace('<table', '<table border="1"').replace('<th>', '<th style="padding: 5px;">').replace('<td>', '<td style="padding: 5px;">'))
        f.write("\n\n")

        f.write("Insight 3: Monthly Sales Trend (First 50 Months)\n")
        monthly_sales_html = monthly_sales._repr_html_()
        f.write(monthly_sales_html.replace('<table', '<table border="1"').replace('<th>', '<th style="padding: 5px;">').replace('<td>', '<td style="padding: 5px;">'))
        f.write("\n\n")

        f.write("Insight 4: Average Transaction Value by Payment Method\n")
        avg_transaction_value_html = avg_transaction_value._repr_html_()
        f.write(avg_transaction_value_html.replace('<table', '<table border="1"').replace('<th>', '<th style="padding: 5px;">').replace('<td>', '<td style="padding: 5px;">'))
        f.write("\n\n")

        f.write("Insight 5: Top 10 Customers by Number of Transactions\n")
        top_customers_html = top_customers._repr_html_()
        f.write(top_customers_html.replace('<table', '<table border="1"').replace('<th>', '<th style="padding: 5px;">').replace('<td>', '<td style="padding: 5px;">'))
        f.write("\n\n")

        f.write("\n--- End of Report ---\n")

    print("Analysis report saved successfully.")

    # --- 6. Stop Spark Session ---
    print("\n--- Stopping Spark Session ---")
    spark.stop()
    print("Spark Session stopped.")
    print("\n--- Big Data Analysis Project Complete! ---")

# --- Main execution block ---
if __name__ == "__main__":
    # First, generate the data
    generate_large_data()
    # Then, analyze the generated data
    analyze_big_data()
