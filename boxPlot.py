import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the CSV file
df = pd.read_csv('benchmark_results.csv')

# Filter rows where success is True
df_success = df[df['success'] == True]

# Define the columns for each boxplot
columns_group1 = [
    'scanning_physical_network', 'creating_folder_and_unzipping', 'parsing_xml_and_validating',
    'checking_existing_project', 'building_topology', 'creating_links', 'connecting_to_server',
    'transferring_files', 'setting_configuration', 'physical_to_ndt_delay'
]

columns_group2 = [
    'scanning_virtual_network', 'backup_ndt', 'transferring_backup_file', 'extracting_backup_file',
    'parsing_ndt_xml', 'matching_devices', 'applying_config', 'ndt_to_physical_delay'
]

columns_group3 = ['round_trip_time']

# Create boxplot for group 1 in a new window with y-axis increments of 5
plt.figure()
df_success[columns_group1].boxplot()
plt.title('Group 1: Physical Network Operations')
plt.xticks(rotation=90)
plt.yticks(np.arange(0, df_success[columns_group1].max().max() + 5, 5))  # Detailed y-axis with increments of 5
plt.tight_layout()
plt.show()

# Create boxplot for group 2 in a new window with y-axis increments of 5
plt.figure()
df_success[columns_group2].boxplot()
plt.title('Group 2: Virtual Network Operations')
plt.xticks(rotation=90)
plt.yticks(np.arange(0, df_success[columns_group2].max().max() + 5, 5))  # Detailed y-axis with increments of 5
plt.tight_layout()
plt.show()

# Create boxplot for group 3 in a new window with default y-axis
plt.figure()
df_success[columns_group3].boxplot()
plt.title('Group 3: Round Trip Time')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
