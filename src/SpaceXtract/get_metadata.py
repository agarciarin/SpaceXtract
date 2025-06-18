import json
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from math import fabs
from collections import OrderedDict
import os
import re
from loguru import logger
from os.path import splitext
import scipy.signal as signal
import sys
import csv
from datetime import datetime

G = 6.67408*10**-11
M = 5.972*10**24
R = 6.373*10**6

g0 = 9.8

BASE_FOLDER = os.path.dirname(__file__)  # Directory where this script is located

def read_list(file):
    data = json.loads(file.readline())

    for x in data:
        data[x] = [data[x]]

    for line in file:
        dict = json.loads(line)

        for x in dict:
            data[x].append(dict[x])

    return data

def find_MECO(acceleration):
    lst = np.where(acceleration < 5)[0]

    if len(lst) == 0:
        return None

    return lst[0]

def final_altitude(velocity, altitude):
    u = G * M
    return -u/(velocity**2/2 - u/(altitude+R)) - R

def acceleration_func(x, Isp, m_dot, m0):
    return g0*Isp*9*m_dot/(m0-9*m_dot*x)

def acceleration_func_s2(x, Isp, m_dot, m0):
    return g0*Isp*m_dot/(m0-m_dot*x)

def fit_data(stage, x_axis, y_axis):
    func = None

    if stage == 1:
        p0 = [288, 300, 5.5 * 10 ** 5]
        param_bounds = ([200, 250, 4.5 * 10 ** 5], [400, 400, 6.5 * 10 ** 5])
        func = acceleration_func
    elif stage == 2:
        p0 = [300, 273, 1.16 * 10 ** 5]
        param_bounds = ([200, 220, 0.5 * 10 ** 5], [400, 400, 2 * 10 ** 5])
        func = acceleration_func_s2

    popt, pcov = curve_fit(func, x_axis, y_axis, p0=p0, bounds=param_bounds)
    return popt

def create_readme(mission_name):
    title = '#{} Information\n\n'.format(mission_name)

    table = ''
    table += '| Data| Value |\n'
    table += '--------------------\n'
    table += '| Stage 1 Apogee| {:.2f} km |\n'.format(stage1_apogee)
    table += '| MECO Time| T+{}:{} |\n'.format(int(meco_time / 60), int(meco_time) % 60)
    table += '| MECO Velocity | {:.2f} m/s |\n'.format(data['velocity'][meco_index])
    table += '| MECO Altitude | {:.2f} km |\n'.format(data['altitude'][meco_index])
    table += '| MECO Velocity Angle | {:.2f} degrees |\n'.format(data['angle'][meco_index])

    print(title + table)

def derivative(x_axis, y_axis, dx):
    """
    Calculate the derivative of f(x)
    :param x_axis: list of the x axis data
    :param y_axis: list of the y axis data
    :param dx: difference of x axis
    :return: f'(x)
    """
    der = (dx//2+dx%2)*[0]

    for i in range(len(x_axis) - dx):
        der.append((y_axis[i + dx] - y_axis[i]) / (x_axis[i + dx] - x_axis[i]))

    der += dx // 2 * [der[-1]]

    for i in range(dx//2+dx%2):
        der[i] = der[dx//2+dx%2+1]

    return der

def data_between(data, start=0, end=-1):
    new_data = OrderedDict()

    for key in data:
        new_data[key] = data[key][start:end]

    return new_data

def data_before_meco(data, meco_index):
    return data_between(data, end=meco_index)

def get_max_q(data, threshhold=0.5):
    max_q = max(data['q'])
    thresh = threshhold*max_q

    time_0 = -1
    time_f = 0


    for i, q in enumerate(data['q']):
        if q > thresh:
            if time_0 == -1:
                time_0 =i
            time_f = i

    return time_0, time_f

def get_landing_burn(data):
    max_q_landing_index = data['q'].index(max(data['q']))
    post_q_data = data_between(data, start=max_q_landing_index)
    minpoint = signal.argrelmax(np.array(post_q_data['acceleration']))[0][0]
    return minpoint + max_q_landing_index, np.argmax(np.array(data['velocity']) < 5)

def get_boostback(data):
    dv = np.abs(np.subtract(data['velocity'], np.abs(data['velocity_x'])))
    end_index = np.where(dv < 1)[0][0]

    new_data = data_between(data, end=end_index)

    acx = derivative(new_data['time'], new_data['velocity_x'], dx=3)

    start = 0
    end = 0

    for i in range(len(acx)//4):
        if acx[i] >= -5:
            start = i

    for i in range(len(acx)//4, len(acx)):
        if acx[i] > -5:
            end = i
            break

    return start, end

def get_apogee_index(data):
    return data['altitude'].index(max(data['altitude']))

def get_apogee_data(data):
    return data_between(data, start=data['altitude'].index(max(data['altitude'])))

def get_entry(data):
    start_index = data['velocity'].index(max(data['velocity']))
    jerk = derivative(data['time'], data['acceleration'], dx=3)
    end_index = jerk.index(max(jerk))

    return start_index, end_index

def generate_figure(data, td_index, tu_index, bb_start, bb_end, apogee_index, start_entry, end_entry, start_lb, end_lb, output_path):
    plt.plot(data['time'], np.abs(data['velocity']))
    plt.axvline(x=data['time'][td_index], color='k', linestyle='--')
    plt.axvline(x=data['time'][tu_index], color='k', linestyle='--')

    plt.axvline(x=data['time'][bb_start], color='k', linestyle='--')
    plt.axvline(x=data['time'][bb_end], color='k', linestyle='--')

    plt.axvline(x=data['time'][apogee_index], color='k', linestyle='--')

    plt.axvline(x=data['time'][start_entry], color='k', linestyle='--')
    plt.axvline(x=data['time'][end_entry], color='k', linestyle='--')

    plt.axvline(x=data['time'][start_lb], color='k', linestyle='--')
    plt.axvline(x=data['time'][end_lb], color='k', linestyle='--')
    # plt.show()
    
    plt.title('Velocity vs Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')

    # Save figure
    fig_path = os.path.join(output_path, 'Velocity vs Time - Stage 1')
    plt.savefig(f'{fig_path}.png', dpi=300)
    plt.close()
    logger.info(f"Figure saved: {fig_path}.png")

def save_data_in_file(mission_name, date_mission, stage1_apogee, meco_time, data, meco_index, output_path):
     # Extract relevant values
    meco_velocity = round(data['velocity'][meco_index], 2)
    meco_altitude = round(data['altitude'][meco_index], 2)
    meco_angle = round(data['angle'][meco_index], 2)
    
    # Fix: use os.path.join instead of os.join
    filename = mission_name + '_MECO_parameters.csv'
    file_path = os.path.join(output_path, filename)

    # Check if file exists to decide whether to write the header
    write_header = not os.path.exists(file_path)

    # Write data to CSV
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)

        # Write header if file is new
        if write_header:
            writer.writerow([
                "MissionName", "Date", "Stage1_Apogee_(km)", "MECO_Time_(s)",
                "MECO_Alt_(km)", "MECO_Vel_(m/s)", "MECO_Elev_(deg)"
            ])

        # Write the data row
        writer.writerow([
            mission_name,
            date_mission,
            round(stage1_apogee, 2),
            meco_time,
            meco_altitude,
            meco_velocity,
            meco_angle
        ])
        
    logger.info(f"Data saved: {file_path}")
    
def generate_meta_data(input_path, output_path):

    file = open(input_path, 'r')
    data = read_list(file)


    if fabs(data['altitude'][0] - data['altitude'][-1]) < 50:
        final_stage = 1
    else:
        final_stage = 2

    fps = 10

    start_time = 10*fps
    end_time = 10*fps


    time = np.array(data['time'])
    acceleration = np.array(data['acceleration'])

    meco_index = find_MECO(acceleration)
    meco_time = time[meco_index]

    meco_data = data_before_meco(data, meco_index)
    max_q_start, max_q_end = get_max_q(meco_data, threshhold=0.5)

    max_q_data = data_between(meco_data, max_q_start, max_q_end)

    jerk = derivative(max_q_data['time'], max_q_data['acceleration'], 3)

    td_index = max_q_start + jerk.index(min(jerk))
    tu_index = max_q_start + jerk.index(max(jerk))

    post_meco_data = data_between(data, meco_index)
    bb_start, bb_end = meco_index + get_boostback(post_meco_data)

    apogee_index = get_apogee_index(data)
    post_apogee_data = get_apogee_data(data)

    start_entry, end_entry = get_entry(post_apogee_data)

    start_entry += apogee_index
    end_entry += apogee_index

    post_entry_data = data_between(data, start=end_entry)
    start_lb, end_lb = get_landing_burn(post_entry_data)

    start_lb += end_entry
    end_lb += end_entry

    generate_figure(data, td_index, tu_index, bb_start, bb_end, apogee_index, start_entry, end_entry, start_lb, end_lb, output_path)

    if final_stage == 2:
        stage1_apogee = final_altitude(data['velocity_y'][meco_index], 1000*data['altitude'][meco_index])/1000
    elif final_stage == 1:
        stage1_apogee = max(data['altitude'])


    #popt1 = fit_data(1, time[start_time:meco_index-end_time], acceleration[start_time:meco_index-end_time])
    #print('Stage 1: Isp = {:.2f}, m_dot = {:.2f}, mass = {:.2f}'.format(*popt1))

    if final_stage == 2:
        ses_index = meco_index + np.where(acceleration[meco_index:] > 5)[0][0]
        seco_index_start = find_MECO(acceleration[ses_index:])

        if seco_index_start is not None:
            seco_index = meco_index + seco_index_start
            ses_time = time[ses_index]
            seco_time = time[seco_index]

            s2_time = time[ses_index:seco_index]
            s2_time = np.subtract(s2_time, s2_time[0])

        #popt2 = fit_data(2, s2_time, acceleration[ses_index:seco_index])
        #print('Stage 2: Isp = {:.2f}, m_dot = {:.2f}, mass = {:.2f}'.format(*popt2))

    # Save metadata to file
    date_raw, mission_name = os.path.basename(os.path.normpath(output_path)).split('_', 1)
    date_mission = datetime.strptime(date_raw, "%Y%m%d").strftime("%d/%m/%Y")
    save_data_in_file(mission_name, date_mission, stage1_apogee, meco_time, data, meco_index, output_path)

def generate_multiple_meta_data(main_input_folder_path):
    # Regex to match folders starting with date (YYYYMMDD) + underscore + missionname
    folder_pattern = re.compile(r'^\d{8}_.+')

    for entry in os.listdir(main_input_folder_path):
        subfolder_path = os.path.join(main_input_folder_path, entry)

        if os.path.isdir(subfolder_path) and folder_pattern.match(entry):
            # Look for .json files containing 'stage1_analysed' in the filename
            for file in os.listdir(subfolder_path):
                if file.endswith('.json') and 'stage1_analysed' in file:
                    json_path = os.path.join(subfolder_path, file)

            generate_meta_data(input_path=os.path.normpath(json_path), 
                               output_path=os.path.normpath(subfolder_path))
            

def main():
    ### Configuration
    mission_name = '20230728_Starlink-Mission'
    input_path = '../../Output/' + mission_name + '/' + mission_name + '_0_stage1_analysed.json'
    output_path = '../../Output/' + mission_name

    # Multiple missions
    multiple_mission = False
    main_input_folder_path = '../../Output'

    ### Execution
    if multiple_mission:
        generate_multiple_meta_data(os.path.join(BASE_FOLDER, main_input_folder_path))

    else:
        generate_meta_data(os.path.join(BASE_FOLDER, input_path), 
                           os.path.join(BASE_FOLDER, output_path))
    
#
# Main
#
if __name__ == '__main__':
    main()
