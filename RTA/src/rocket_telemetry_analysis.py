
import requests
import json
import pandas as pd
from loguru import logger


def load_json_from_url(url):
  """
  Load JSON data from a given URL.
  
  Args:
      url (str): The URL to fetch the JSON data from.
      
  Returns:
      dict: The parsed JSON data.
  """
  response = requests.get(url)
  if response.status_code == 200:
    return response.json()
  else:
    return None
    # raise Exception(f"Failed to load data from {url}, status code: {response.status_code}")



def get_data(df, time):
  data = []

  index = df.index[df["time"] == time]

  # If the time is not found, we return default values
  if not index.empty:
    idx = index[0]
    altitude = df.loc[idx, "altitude"]
    velocity = df.loc[idx, "velocity"]
    
    # If angle is not present, we default to 0
    if 'angle' in df.columns:
        angle = df.loc[idx, "angle"]
    else:
        angle = 0
  else:
      altitude = 0
      velocity = 0
      angle = 0

  data.append(time)      # Time in seconds
  data.append(altitude)  # Altitude in km
  data.append(velocity)  # Velocity in m/s
  data.append(angle)     # Elevation angle in deg

  return data


def process_scenarios(path_data, additional_data):
  #Columns for the DataFrame
  columns = [
    "Company", "Vehicle", "MissionName", "OrbitType", "Date",
    "MECO_Time_(s)", "MECO_Alt_(km)", "MECO_Vel_(m/s)", "MECO_Elev_(deg)", 
    "SECO_Time_(s)", "SECO_Alt_(km)", "SECO_Vel_(m/s)", "SECO_Elev_(deg)"
  ]
  
  data_df = pd.DataFrame(columns=columns)

  #Loop through each scenario in the path_data
  for scenario in path_data:
    print("agrn_Scenario:", scenario['mission_name'])

    #Fill Common data
    data_common = [additional_data['Company'], additional_data['Vehicle'], 
                   scenario['mission_name'], additional_data['OrbitType'],
                   additional_data['Date']]

    #Extract the json data for each scenario
    stages_analysed_df = pd.DataFrame(load_json_from_url(scenario['JSON']['analysed']))
    # stage1_df = pd.DataFrame(load_json_from_url(scenario['JSON']['stage1']))
    # stage2_df = pd.DataFrame(load_json_from_url(scenario['JSON']['stage2']))
    events = load_json_from_url(scenario['JSON']['events'])

    # Get MECO and SECO times from the events
    meco_time = events['meco']
    seco_time = events['seco1']

    # Compute stage-1 parameters
    #TODO
    # stage1_apogee = 
    # stage1_range = 

    # Computes MECO data
    if stages_analysed_df.empty or meco_time == None:
      data_meco = [0, 0, 0, 0]  # Default values if no MECO data
    else:
      data_meco = get_data(stages_analysed_df, meco_time)

    # Computes SECO data
    if stages_analysed_df.empty or seco_time == None:
      data_seco = [0, 0, 0, 0]  # Default values if no SECO data
    else:
      data_seco = get_data(stages_analysed_df, seco_time)
    
    # Save data in the DataFrame
    data_row = data_common + data_meco + data_seco 
    data_df.loc[len(data_df)] = data_row

  return data_df



def main():
  #Configuration
  source_url = "https://raw.githubusercontent.com/shahar603/Telemetry-Data/master/Laucnhes.json"

  additional_data = {
    "Company": "SpaceX",
    "Vehicle": "Falcon 9",
    "OrbitType": "XXX",
    "Date": "XX-XX-XXXX" 
  }

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
  

#
# Main
#
if __name__ == '__main__':
    main()
