import subprocess
import re
import csv
import os
import time
from datetime import datetime

def extract_timing_data(output_text):
    """Extract timing information from the script output."""
    # Define the patterns to search for timing information
    timing_patterns = [
        r"scanning the network took: (\d+\.\d+) seconds",
        r"Creating unique folder and unzipping: (\d+\.\d+) seconds",
        r"Parsing XML and validating: (\d+\.\d+) seconds",
        r"Checking existing project and deleting if it exists: (\d+\.\d+) seconds",
        r"Building topology took: (\d+\.\d+) seconds",
        r"Creating links took: (\d+\.\d+) seconds", 
        r"Connecting to server took: (\d+\.\d+) seconds",
        r"Transferring files took: (\d+\.\d+) seconds",
        r"Starting devices took: (\d+\.\d+) seconds",
        r"Setting configuration took: (\d+\.\d+) seconds",
        r"Run time was: (\d+\.\d+) seconds",
        r"Total time was: (\d+\.\d+) seconds" 
    ]
    
    # Dictionary to store the timing results
    timing_results = {}
    
    # Extract each timing value
    for pattern in timing_patterns:
        match = re.search(pattern, output_text)
        if match:
            # Extract the step name from the pattern
            if "Total time was" in pattern:
                step_name = "Total time"
            elif "Run time was" in pattern:
                step_name = "Run time"
            else:
                step_match = re.search(r"(.*?) took:", pattern)
                if step_match:
                    step_name = step_match.group(1).strip()
                else:
                    continue  # Skip if we can't extract a step name
                
            # Store the timing value
            timing_results[step_name] = float(match.group(1))
    
    return timing_results

def run_benchmark(iterations=100, output_file="benchmark_results.csv"):
    """Run the main.py script multiple times and collect timing data."""
    
    all_results = []
    
    print(f"Starting benchmark with {iterations} iterations")
    print(f"Results will be saved to {output_file}")
    
    for i in range(iterations):
        # Create a timestamp for this run
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\nRun {i+1}/{iterations} - {timestamp}")
        
        try:
            # Run the main.py script and capture output
            result = subprocess.run(["python", "main.py"], 
                                    capture_output=True, 
                                    text=True)
            
            # Extract timing data from the output
            combined_output = result.stdout + result.stderr
            timing_data = extract_timing_data(combined_output)
            
            # Add run metadata
            timing_data['run_number'] = i+1
            timing_data['timestamp'] = timestamp
            
            if timing_data:
                timing_data['success'] = True
                # Print summary of this run
                total_time = timing_data.get('Total time', 'N/A')
                run_time = timing_data.get('Run time', 'N/A')
                print(f"Run completed - Total time: {total_time} seconds, Run time: {run_time} seconds")
            else:
                # Save output for debugging if no timing data found
                with open(f"run_{i+1}_output.txt", "w") as f:
                    f.write(combined_output)
                
                timing_data['success'] = False
                timing_data['error'] = "No timing data found in output"
                print(f"No timing data found. Output saved to run_{i+1}_output.txt")
                
            all_results.append(timing_data)
            
        except Exception as e:
            print(f"Error during run {i+1}: {e}")
            all_results.append({
                'run_number': i+1,
                'timestamp': timestamp,
                'success': False,
                'error': str(e)
            })
        
        # Add a short delay between runs to prevent resource contention
        time.sleep(1)
    
    # Save results to CSV
    if all_results:
        # Define a fixed order for the CSV columns
        fixed_fieldnames = [
            'run_number', 
            'timestamp', 
            'success', 
            'error',
            'scanning the network',
            'Creating unique folder and unzipping',
            'Parsing XML and validating',
            'Checking existing project and deleting if it exists',
            'Building topology',
            'Creating links',
            'Connecting to server',
            'Transferring files',
            'Starting devices',
            'Setting configuration',
            'Run time',
            'Total time'
        ]
        
        # Get all column names that actually appear in our results
        all_columns = set()
        for result in all_results:
            all_columns.update(result.keys())
        
        # Filter fixed_fieldnames to include only those that actually appear in the results
        fieldnames = [f for f in fixed_fieldnames if f in all_columns]
        
        # Add any additional fields that weren't in our fixed list
        additional_fields = sorted(list(all_columns - set(fieldnames)))
        fieldnames.extend(additional_fields)
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
            
        print(f"\nBenchmark complete. Results saved to {output_file}")
    else:
        print("\nNo results collected. Check for errors.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run main.py benchmark multiple times')
    parser.add_argument('-n', '--iterations', type=int, default=2,
                        help='Number of iterations to run (default: 100)')
    parser.add_argument('-o', '--output', type=str, default="benchmark_results.csv",
                        help='Output CSV file (default: benchmark_results.csv)')
    
    args = parser.parse_args()
    
    run_benchmark(iterations=args.iterations, output_file=args.output)