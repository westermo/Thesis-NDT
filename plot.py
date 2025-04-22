import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data from CSV file
df = pd.read_csv('./benchmark_results.csv')

# Print column names to verify what's actually in the CSV
print("Actual columns in CSV:", df.columns.tolist())

# Extract the function columns (excluding metadata columns)
# Correct column names based on what's in the CSV file
function_columns = ['scanning the network', 'Building topology', 'Creating links', 
                    'Connecting to server', 'Transferring files', 'Starting devices', 
                    'Setting configuration', 'Run time', 'Total time']

# Calculate mean and std for each function
means = df[function_columns].mean()
stds = df[function_columns].std()

# Some columns may not have std if there's only one run
# Replace NaN with 0 for those cases
stds = stds.fillna(0)

# Create indices for the bars
indices = np.arange(len(function_columns))

# Create figure and axis with a good size
fig, ax = plt.subplots(figsize=(14, 8))

# Create bar chart with error bars
bars = ax.bar(indices, means, yerr=stds, capsize=10, color='skyblue', edgecolor='black')

# Set labels and title
ax.set_xlabel('Function', fontweight='bold', fontsize=12)
ax.set_ylabel('Time (seconds)', fontweight='bold', fontsize=12)
ax.set_title('Average Time per Function with Standard Deviation', fontweight='bold', fontsize=14)

# Set x-ticks
ax.set_xticks(indices)
ax.set_xticklabels(function_columns, rotation=45, ha='right')

# Add grid for better readability
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Add values on top of bars
for i, bar in enumerate(bars):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + stds[i] + 0.1,
            f'{height:.2f}s', ha='center', va='bottom', fontsize=9)

# Create a second plot to better show the smaller values
fig2, ax2 = plt.subplots(figsize=(14, 8))

# Filter out the larger values for better visualization
# We'll exclude "Starting devices" and "Total time" which are likely the largest
small_indices = [i for i, col in enumerate(function_columns) 
                if col not in ['Starting devices', 'Total time'] 
                or means[i] < 20]  # Adjust threshold as needed

small_means = [means[i] for i in small_indices]
small_stds = [stds[i] for i in small_indices]
small_labels = [function_columns[i] for i in small_indices]

# Create smaller bars chart
small_bars = ax2.bar(range(len(small_means)), small_means, yerr=small_stds, 
                    capsize=10, color='lightgreen', edgecolor='black')

# Set labels and title
ax2.set_xlabel('Function', fontweight='bold', fontsize=12)
ax2.set_ylabel('Time (seconds)', fontweight='bold', fontsize=12)
ax2.set_title('Average Time per Function (Excluding Outliers)', fontweight='bold', fontsize=14)

# Set x-ticks
ax2.set_xticks(range(len(small_means)))
ax2.set_xticklabels(small_labels, rotation=45, ha='right')

# Add grid for better readability
ax2.grid(axis='y', linestyle='--', alpha=0.7)

# Add values on top of bars
for i, bar in enumerate(small_bars):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + small_stds[i] + 0.1,
            f'{height:.2f}s', ha='center', va='bottom', fontsize=9)

# Add success rate information
success_rate = df['success'].mean() * 100
plt.figtext(0.5, 0.01, f"Success Rate: {success_rate:.1f}%", ha='center', 
            fontsize=12, bbox=dict(facecolor='lightgray', alpha=0.5))

# Adjust layouts
plt.tight_layout(rect=[0, 0.03, 1, 0.97])

# Save plots
fig.savefig('benchmark_all_functions.png', dpi=300, bbox_inches='tight')
fig2.savefig('benchmark_small_values.png', dpi=300, bbox_inches='tight')

# Show plots
plt.show()

# Print some statistics
print(f"Number of runs: {len(df)}")
print("\nAverage times with standard deviations:")
for col in function_columns:
    print(f"{col}: {df[col].mean():.2f}s ± {df[col].std():.2f}s")

print("\nFunction with highest variance:")
highest_var_col = df[function_columns].var().idxmax()
print(f"{highest_var_col}: variance = {df[highest_var_col].var():.2f}")

# Calculate percentages of total time
total_time_mean = means['Total time']
print("\nPercentage of total time:")
for col in function_columns:
    if col != 'Total time':
        percentage = (means[col] / total_time_mean) * 100
        print(f"{col}: {percentage:.2f}%")