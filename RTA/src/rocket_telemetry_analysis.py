
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from loguru import logger

# Constants
base_dir = os.path.dirname(__file__)  # Directory where this script is located
EPSILON = 0.1  # Time in seconds to avoid floating point precision issues


def load_json_from_url(url):
  """
  Load JSON data from a given URL.
  
  Args:
      url (str): The URL to fetch the JSON data from.
      
  Returns:
      dict: The parsed JSON data.
  """
  if not url:
    return None
  else:
    response = requests.get(url)
    if response.status_code == 200:
      return response.json()
    else:
      return None
      # raise Exception(f"Failed to load data from {url}, status code: {response.status_code}")

def get_data(df, time):
  data = []

  #Find the index of the row where the time is closest to the given time
  index = df.index[(df['time'] >= (time - EPSILON)) & (df['time'] <= (time + EPSILON))]

  # If the time is not found (row is out of range), return default values
  if not index.empty:
    idx = index[0]
    altitude = df.loc[idx, 'altitude']
    velocity = df.loc[idx, 'velocity']
    
    # If column 'angle' is not present, return default value
    if 'angle' in df.columns:
        angle = df.loc[idx, 'angle']
    else:
        angle = -1
  else:
      altitude = -1
      velocity = -1
      angle = -1

  data.append(altitude)  # Altitude in km
  data.append(velocity)  # Velocity in m/s
  data.append(angle)     # Elevation angle in deg

  return data

def get_apogee(df):

  if 'altitude' in df.columns:
    apogee = df['altitude'].max()
  else:
    apogee = 0

  return apogee

def process_scenarios(path_data, additional_data):
  #Columns for the DataFrame
  columns = [
    "Status", "Company", "Vehicle", "MissionName", "OrbitType", "Date",
    "Stage1_Apogee_(km)",
    "MECO_Time_(s)", "MECO_Alt_(km)", "MECO_Vel_(m/s)", "MECO_Elev_(deg)", 
    "SECO_Time_(s)", "SECO_Alt_(km)", "SECO_Vel_(m/s)", "SECO_Elev_(deg)"
  ]
  
  data_df = pd.DataFrame(columns=columns)

  #Loop through each scenario in the path_data
  for scenario in path_data:
    # print("agrn_Scenario:", scenario['mission_name'])

    # Initialize times and stage-1 apogee
    meco_time = -1
    seco_time = -1
    stage1_apogee = -1

    #Fill Common data
    data_common = [additional_data['Company'], additional_data['Vehicle'], 
                   scenario['mission_name'], additional_data['OrbitType'],
                   additional_data['Date']]

    #Extract the json data for each scenario
    stages_analysed_df = pd.DataFrame(load_json_from_url(scenario['JSON']['analysed']))
    stage1_df = pd.DataFrame(load_json_from_url(scenario['JSON']['stage1']))
    stage2_df = pd.DataFrame(load_json_from_url(scenario['JSON']['stage2']))
    events = load_json_from_url(scenario['JSON']['events'])

    # Get MECO and SECO times from the events
    meco_time = events['meco']
    seco_time = events['seco1']

    # Compute stage-1 parameters
    #TODO
    if stage1_df.empty == False:
      stage1_apogee = get_apogee(stage1_df)

    # Computes MECO data from stages_analysed_df
    if stages_analysed_df.empty == False and meco_time != None:
      data_meco = get_data(stages_analysed_df, meco_time)

    #Computes MECO data from stage1_df
    elif stage1_df.empty == False and meco_time != None:
      data_meco = get_data(stage1_df, meco_time)
    
    # Default
    else:
      data_meco = [-1, -1, -1]

    # Computes SECO data from stages_analysed_df
    if stages_analysed_df.empty == False and seco_time != None:
      data_seco = get_data(stages_analysed_df, seco_time)

    #Computes SECO data from stage2_df
    elif stage2_df.empty == False and seco_time != None:
      data_seco = get_data(stage2_df, seco_time)
    
    # Default
    else:
      data_seco = [-1, -1, -1]

    # Update the MECO and SECO times
    if meco_time is None:
      meco_time = -1
    if seco_time is None:
      seco_time = -1

    # Set status of the scenario
    if (meco_time == -1) and (data_meco == [-1, -1, -1]):
      status = 'False'
    else:
      status = 'True'

    # Save data in the DataFrame
    data_row = [status] + data_common + [stage1_apogee] + [meco_time] + data_meco + [seco_time] + data_seco 
    data_df.loc[len(data_df)] = data_row

  return data_df

def export_data(data_df, output_path, file_name):
  # Create the folder if it doesn't exist
  if not os.path.exists(os.path.join(base_dir, output_path)):
    os.makedirs(os.path.join(base_dir, output_path))

  # Full file path
  full_path = os.path.join(base_dir, output_path, file_name)

  # Export DataFrame to CSV
  data_df.to_csv(full_path, index=False)

def generate_subfigures(df, x_col, y_cols, fig_name, output_path):
  # Create output directory if it doesn't exist
  full_output_path = os.path.join(base_dir, output_path)
  if not os.path.exists(full_output_path):
      os.makedirs(full_output_path)

  # Filter to only rows with status == True
  df = df[df["Status"] == True]

  # Initialize figure
  fig, axs = plt.subplots(2, 2, figsize=(12, 8))
  axs = axs.flatten()  # flatten to index 0–3

  # Plot each subplot
  for i in range(4):
    y_col = y_cols[i]
    ax = axs[i]

    # Filter invalid values for the current column
    valid_data = df[df[y_col] != -1]

    x_vals = valid_data[x_col]
    y_vals = valid_data[y_col]

    # Plot
    ax.plot(x_vals, y_vals, label=y_col, color='tab:blue', marker='o')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True)
    # ax.legend()

    # Compute and show mean
    if not y_vals.empty:
      mean_val = y_vals.mean()
      std_val = y_vals.std()
      max_val = y_vals.max()
      min_val = y_vals.min()
      count_val = len(y_vals)
      
      text_str = (
          f"{y_col}\n"
          f"Nº Sample: {count_val}\n"
          f"Mean {mean_val:.2f}\n"
          f"Std Dev: {std_val:.3f}\n"
          f"Max: {max_val:.2f}\n"
          f"Min: {min_val:.2f}"
          )
    else:
      text_str = (
          f"{y_col}\n"
          f"N/A"
          )

    # Add text box
    ax.text(0.95, 0.95, text_str, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Rotate x-axis labels
    ax.tick_params(axis='x', labelrotation=90)
    
  fig.suptitle(fig_name, fontsize=16)
  fig.tight_layout(rect=[0, 0, 1, 0.96])  # Leave space for title

  # Save the figure
  fig_path = os.path.join(full_output_path, fig_name)
  plt.savefig(f'{fig_path}.png', dpi=300)
  plt.close()

def generate_figure(df, x_col, y_col, fig_name, output_path):
  # Create output directory if it doesn't exist
  full_output_path = os.path.join(base_dir, output_path)
  if not os.path.exists(full_output_path):
      os.makedirs(full_output_path)

  # Filter: Status == True and y_col != -1
  df = df[(df["Status"] == True) & (df[y_col] != -1)]

  x_vals = df[x_col]
  y_vals = df[y_col]

  # Initialize figure
  fig, ax = plt.subplots(figsize=(12, 6))

  # Plot
  ax.plot(x_vals, y_vals, label=y_col, color='tab:blue', marker='o')
  ax.set_xlabel(x_col)
  ax.set_ylabel(y_col)
  ax.grid(True)
  ax.tick_params(axis='x', labelrotation=90)

  # Compute stats
  if not y_vals.empty:
      mean_val = y_vals.mean()
      std_val = y_vals.std()
      max_val = y_vals.max()
      min_val = y_vals.min()
      count_val = len(y_vals)

      text_str = (
          f"{y_col}\n"
          f"Nº Sample: {count_val}\n"
          f"Mean: {mean_val:.2f}\n"
          f"Std Dev: {std_val:.3f}\n"
          f"Max: {max_val:.2f}\n"
          f"Min: {min_val:.2f}"
      )
  else:
      text_str = (
          f"{y_col}\n"
          f"N/A"
      )

  # Add text box
  ax.text(0.95, 0.95, text_str, transform=ax.transAxes,
          fontsize=9, verticalalignment='top', horizontalalignment='right',
          bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

  # Title and layout
  fig.suptitle(fig_name, fontsize=16)
  fig.tight_layout(rect=[0, 0, 1, 0.95])

  # Save figure
  fig_path = os.path.join(full_output_path, fig_name)
  plt.savefig(f'{fig_path}.png', dpi=300)
  plt.close()



def main():
  #########################################################################
  ### Configuration
  #########################################################################
  # Data source
  source_url = "https://raw.githubusercontent.com/shahar603/Telemetry-Data/master/Laucnhes.json"
  
  # Generated .csv file and plots
  output_path = '../Output/RTA-01'
  
  # Import .csv files
  data_to_load_path = "../Output/RTA-01/SpaceX_RTA_01.csv"

  # To be completed manually after generate the .csv file
  additional_data = {
    "Company": "SpaceX",
    "Vehicle": "Falcon 9",
    "OrbitType": "XXX",
    "Date": "XX-XX-XXXX" 
  }

  # Set the mode: 'GEN_PLOT', 'GEN', 'PLOT'
  mode = 'PLOT' 

  #########################################################################
  ### Execution
  #########################################################################
  # Data generation
  if mode == 'GEN_PLOT' or mode == 'GEN':
    # Load the JSON data from the source URL
    logger.info("Loading launch data from source URL...")
    launch_data = load_json_from_url(source_url)

    # Process the scenarios
    if launch_data is not None:
      logger.info("Processing scenarios...")
      data_df = process_scenarios(launch_data, additional_data)
      logger.info("Scenarios processed successfully.")
    else:
      raise Exception("Failed to load launch data from the source URL.")
    
    # Export dataframe to CSV
    export_data(data_df, output_path, file_name='SpaceX_RTA_01.csv')
    logger.info(f"Data exported successfully to {output_path}")

  # Plotting 
  elif mode == 'GEN_PLOT' or mode == 'PLOT':
    # Import data
    logger.info("Loading data from CSV file...")
    data_loaded_df = pd.read_csv(os.path.join(base_dir, data_to_load_path))

    # Plot data
    logger.info("Plotting data...")

    # Plots for MECO
    generate_subfigures(data_loaded_df, 'MissionName', 
        ['MECO_Time_(s)', 'MECO_Alt_(km)', 'MECO_Vel_(m/s)', 'MECO_Elev_(deg)'], 
        'MECO Parameters', output_path)
    
    #Plots for SECO
    generate_subfigures(data_loaded_df, 'MissionName', 
        ['SECO_Time_(s)', 'SECO_Alt_(km)', 'SECO_Vel_(m/s)', 'SECO_Elev_(deg)'], 
        'SECO Parameters', output_path)
    
    # Plots for Stage-1 Apogee
    generate_figure(data_loaded_df, 'MissionName', 'Stage1_Apogee_(km)', 
        'Stage-1 Apogee', output_path)
  

#
# Main
#
if __name__ == '__main__':
    main()
