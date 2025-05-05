import subprocess
import re
import csv
import os
import time
from datetime import datetime

def extract_timing_data(output_text):
    """Extract timing information from the script output."""
    timing_results = {}
    
    # Match pattern: step_name:float
    # Looks for lines containing step_name:float value format
    pattern = r"([a-z_]+):(\d+\.\d+)"
    
    # Find all matches
    for match in re.finditer(pattern, output_text):
        step_name = match.group(1)
        value = float(match.group(2))
        timing_results[step_name] = value
    
    return timing_results

def run_benchmark(output_file="benchmark_results.csv"):
    """Run the main.py script indefinitely and collect timing data."""
    
    # Configuration variables
    TIMEOUT = 600  # 10 minutes static timeout
    SUCCESS_DELAY = 60  # Wait 60 seconds after successful run
    FAILURE_DELAY = 5   # Wait 5 seconds after failed run
    
    print(f"Starting benchmark - running indefinitely until manually stopped")
    print(f"Results will be saved to {output_file}")
    print(f"Configuration: Timeout={TIMEOUT}s, Success delay={SUCCESS_DELAY}s, Failure delay={FAILURE_DELAY}s")
    
    # Define a fixed order for the CSV columns
    fixed_fieldnames = [
        'run_number', 
        'timestamp', 
        'success', 
        'error',
        'scanning_physical_network',
        'creating_folder_and_unzipping',
        'parsing_xml_and_validating',
        'checking_existing_project',
        'building_topology',
        'creating_links',
        'connecting_to_server',
        'transferring_files',
        'starting_devices',
        'setting_configuration',
        'physical_to_ndt_delay',
        'scanning_virtual_network',
        'backup_ndt',
        'transferring_backup_file',
        'extracting_backup_file',
        'parsing_ndt_xml',
        'matching_devices',
        'applying_config',
        'ndt_to_physical_delay',
        'round_trip_time'
    ]
    
    # Initialize run counter
    run_count = 0
    
    # Check if the output file already exists
    file_exists = os.path.isfile(output_file)
    
    # Open the CSV file for writing (or appending if it exists)
    mode = 'a' if file_exists else 'w'
    with open(output_file, mode, newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fixed_fieldnames)
        
        # Write header only if creating a new file
        if not file_exists:
            writer.writeheader()
        
        # If we're appending to an existing file, get the last run number
        if file_exists:
            with open(output_file, 'r') as existing_file:
                reader = csv.reader(existing_file)
                # Count rows (excluding header)
                rows = sum(1 for row in reader) - 1
                run_count = rows
                print(f"Continuing from previous run - {run_count} runs already recorded")
        
        # Run indefinitely until interrupted
        try:
            while True:
                run_count += 1
                
                # Create a timestamp for this run
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"\nRun {run_count} - {timestamp}")
                
                try:
                    # Create temporary file for capturing stderr output
                    stderr_file = f"stderr_run_{run_count}.txt"
                    
                    # Record start time
                    start_time = time.time()
                    
                    # Run the main.py process with stderr redirection only
                    with open(stderr_file, 'w') as f_err:
                        print(f"Starting main.py with timeout of {TIMEOUT} seconds")
                        
                        # Run the process with a timeout
                        try:
                            process = subprocess.Popen(
                                ["python3", "main.py"],
                                stdout=subprocess.DEVNULL,  # Discard stdout
                                stderr=f_err,
                                text=True
                            )
                            
                            # Monitor the process with timeout
                            timed_out = False
                            while process.poll() is None:
                                # Check if timeout exceeded
                                if time.time() - start_time > TIMEOUT:
                                    print(f"Run exceeded timeout of {TIMEOUT} seconds - terminating")
                                    process.terminate()
                                    try:
                                        process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
                                    except subprocess.TimeoutExpired:
                                        process.kill()  # Force kill if it doesn't terminate
                                    timed_out = True
                                    break
                                
                                # Sleep to avoid high CPU usage
                                time.sleep(1)
                        
                        except Exception as e:
                            print(f"Error running process: {e}")
                            timed_out = True
                    
                    # Read the stderr output file
                    with open(stderr_file, 'r') as f:
                        stderr_data = f.read()
                    
                    # Print a brief summary of the output
                    #if stderr_data:
                    #    print(f"STDERR (last 300 chars): {stderr_data[-300:] if len(stderr_data) > 300 else stderr_data}")
                    
                    # Extract timing data from stderr only
                    timing_data = extract_timing_data(stderr_data)
                    
                    # Add run metadata
                    timing_data['run_number'] = run_count
                    timing_data['timestamp'] = timestamp
                    
                    # Check for success (all measurement fields must have values)
                    # Metadata fields that aren't actual measurements
                    metadata_fields = ['run_number', 'timestamp', 'success', 'error']
                    
                    # Get list of measurement fields (all fields except metadata)
                    measurement_fields = [field for field in fixed_fieldnames if field not in metadata_fields]
                    
                    # Check if all measurement fields have values
                    missing_fields = []
                    for field in measurement_fields:
                        if field not in timing_data or timing_data[field] is None:
                            missing_fields.append(field)
                    
                    run_successful = False
                    
                    if timed_out:
                        print(f"Run {run_count} timed out and will be discarded")
                        timing_data['success'] = False
                        timing_data['error'] = f"Exceeded timeout of {TIMEOUT} seconds"
                    elif not missing_fields:
                        # All fields have values - run was successful
                        timing_data['success'] = True
                        run_successful = True
                        
                        # Print simple success message without the problematic format strings
                        print(f"Run completed successfully with all measurement fields populated")
                    else:
                        # Run was unsuccessful - missing some fields
                        print(f"Run {run_count} did not complete properly (missing {len(missing_fields)} measurement fields)")
                        print(f"Missing fields: {', '.join(missing_fields)}")
                        timing_data['success'] = False
                        timing_data['error'] = f"Missing fields: {', '.join(missing_fields)}"
                    
                    # Make sure all fields are present in the data
                    for field in fixed_fieldnames:
                        if field not in timing_data:
                            timing_data[field] = None
                    
                    # Write to CSV
                    writer.writerow(timing_data)
                    csvfile.flush()  # Ensure data is written to disk
                    
                    # Clean up temporary files
                    try:
                        os.remove(stderr_file)
                    except:
                        pass  # Ignore errors in cleanup
                    
                except Exception as e:
                    print(f"Error during run {run_count}: {e}")
                    writer.writerow({
                        'run_number': run_count,
                        'timestamp': timestamp,
                        'success': False,
                        'error': str(e)
                    })
                    csvfile.flush()  # Ensure data is written to disk
                
                # Wait between runs based on success/failure
                if run_successful:
                    print(f"Waiting {SUCCESS_DELAY} seconds before next run (successful run)...")
                    time.sleep(SUCCESS_DELAY)
                else:
                    print(f"Waiting {FAILURE_DELAY} seconds before next run (failed run)...")
                    time.sleep(FAILURE_DELAY)
        
        except KeyboardInterrupt:
            print("\nBenchmark stopped by user")
    
    print(f"\nBenchmark complete. Results saved to {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run main.py benchmark indefinitely')
    parser.add_argument('-o', '--output', type=str, default="benchmark_results.csv",
                        help='Output CSV file (default: benchmark_results.csv)')
    parser.add_argument('-s', '--success-delay', type=int, default=60,
                        help='Seconds to wait after successful run (default: 60)')
    parser.add_argument('-f', '--failure-delay', type=int, default=5,
                        help='Seconds to wait after failed run (default: 5)')
    parser.add_argument('-t', '--timeout', type=int, default=600,
                        help='Timeout in seconds for each run (default: 600)')
    
    args = parser.parse_args()
    
    # Update the global delay variables if provided via command line
    SUCCESS_DELAY = args.success_delay
    FAILURE_DELAY = args.failure_delay
    TIMEOUT = args.timeout
    
    run_benchmark(output_file=args.output)