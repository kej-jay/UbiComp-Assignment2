#imports
import json
from io import StringIO

import requests
import scipy.spatial.distance
from collections import deque
import pandas as pd
import os
from sklearn.preprocessing import MaxAbsScaler
import numpy as np
import joblib
import statistics
from time import sleep
from statistics import mode

#constants
max_dispersion = np.deg2rad(1.6)
min_duration = 100
seconds_feature = 5
IP_HOLOLENS = 123
#auxiliary functions
def vector_dispersion(vectors):
    distances = scipy.spatial.distance.pdist(vectors, metric='cosine')
    distances.sort()
    cut_off = np.max([distances.shape[0] // 5, 4])
    return np.arccos(1. - distances[-cut_off:].mean())

def gaze_dispersion(eye_data):
    base_data = eye_data

    vectors = []
    for p in base_data:
        vectors.append((p['gazeDirection_x'], p['gazeDirection_y'], p['gazeDirection_z']))
    vectors = np.array(vectors, dtype=np.float32)

    if len(vectors) < 2:
        return float("inf")
    else:
        return vector_dispersion(vectors)

def get_centroid(eye_data):
    '''Calculates the centroid for each point in a df of points.
    Input: Df of points.
    Output: Vector containg the centroid of all points.'''
    x = [p['gazeDirection_x'] for p in eye_data]
    y = [p['gazeDirection_y'] for p in eye_data]
    z = [p['gazeDirection_z'] for p in eye_data]
    return (sum(x) / len(eye_data), sum(y) / len(eye_data), sum(z) / len(eye_data))

def detect_fixations(gaze_data):
    # Convert Pandas data frame to list of Python dictionaries
    gaze_data = gaze_data.T.to_dict().values()

    candidate = deque()
    future_data = deque(gaze_data)
    while future_data:
        # check if candidate contains enough data
        if len(candidate) < 2 or candidate[-1]['eyeDataTimestamp'] - candidate[0]['eyeDataTimestamp'] < min_duration:
            datum = future_data.popleft()
            candidate.append(datum)
            continue

        # Minimal duration reached, check for fixation
        dispersion = gaze_dispersion(candidate)
        if dispersion > max_dispersion:
            # not a fixation, move forward
            candidate.popleft()
            continue

        # Minimal fixation found. Try to extend!
        while future_data:
            datum = future_data[0]
            candidate.append(datum)

            dispersion = gaze_dispersion(candidate)
            if dispersion > max_dispersion:
                # end of fixation found
                candidate.pop()
                break
            else:
                # still a fixation, continue extending
                future_data.popleft()
        centroid = get_centroid(candidate)
        yield {"start": candidate[0]['eyeDataTimestamp'], "end": candidate[-1]['eyeDataTimestamp'],
               "duration": candidate[-1]['eyeDataTimestamp'] - candidate[0]['eyeDataTimestamp'],
               "centroid": centroid, "dispersion": dispersion}
        candidate.clear()

    #Calculate features
def only_valid_data(data):
        '''Returns only valid gaze points. Those have values in gazeDirection_x etc.'''
        return data[(data.gazeHasValue == True) & (data.isCalibrationValid == True)]

def calculate_blink_features(df, timespan):
        ''' Calculates the blink features for a given df of raw data.
        Input: Dataframe with raw data (incl. invalid points), timespan of data chunk in seconds\
        Output: Dict with the blink features
        '''
        i=0;
        blink_list = []
        blink_duration_list = []
        number_of_blinks = 0
        window_start_time = df["eyeDataTimestamp"][0]
        window_end_time = df["eyeDataTimestamp"][0]
        all_false = 0;
        if (not window_start_time  or not window_end_time):
            return {}

        for i, row in df.iterrows():

            cur_number_of_blinks = 0
            if (not row["gazeHasValue"]):
                cur_number_of_blinks+=1
                all_false += 1
                while (i < len(df["gazeHasValue"])) and (not df["gazeHasValue"][i]) and  window_end_time - window_start_time < 1000:
                    window_end_time = row["eyeDataTimestamp"]
                    i+=1
                    all_false +=1
                blink_list.append(cur_number_of_blinks)
                duration = window_end_time - window_start_time
                blink_duration_list.append(duration)

            number_of_blinks += cur_number_of_blinks;
            if  window_end_time - window_start_time > 1000:
                window_start_time = window_end_time

        blinks_per_second = 0
        if (len(blink_list)  > 0):
            blinks_per_second = number_of_blinks / timespan
        avg_blink_duration = 0
        min_blink_duration = 0
        max_blink_duration = 0
        if (len(blink_duration_list) > 0):
            avg_blink_duration = sum(blink_duration_list) / len(blink_duration_list)
            min_blink_duration = min(blink_duration_list)
            max_blink_duration = max(blink_duration_list)

        # print("all_blinks: ", number_of_blinks, " avg_blink_duration: ", avg_blink_duration,
        #    " min_blink_duration: ", min_blink_duration, " max_blink_duration: ", max_blink_duration,
        #  " blinks_per_second: ", blinks_per_second, " all false: ", all_false)

        return {"number_of_blinks":number_of_blinks, "blinkMean": avg_blink_duration,
                "blinkMin": min_blink_duration, "blinkMax": max_blink_duration,
                "blinkRate": blinks_per_second}


def calculate_fixation_features(df_fixations, timespan):
        '''Calculates the fixation features.
        Input: Dataframe with fixation, timespan of data chunk in seconds.
        Output: Dict containing the fixation features.'''

        min_fix = df_fixations["duration"].min()
        max_fix = df_fixations["duration"].max()
        mean_fix = df_fixations["duration"].mean()
        var_fix = df_fixations["duration"].var()
        std_fix = df_fixations["duration"].std()

        min_dispersion = df_fixations["dispersion"].min()
        max_dispersion = df_fixations["dispersion"].max()
        mean_dispersion = df_fixations["dispersion"].mean()
        var_dispersion = df_fixations["dispersion"].var()
        std_dispersion = df_fixations["dispersion"].std()

        fixation_frequency_second = (len(df_fixations["dispersion"]) / timespan)

    # print("min: ", min_fix, " max: ", max_fix, " mean: ", mean_fix, " var: ", var_fix, "std: ", std_fix)
    # print("min dispersion: ", min_dispersion, " max: ", max_dispersion, " mean: ", mean_dispersion,
    #      " var: ", var_dispersion)
    #print("x dispersion: ", dispersion_x, " y dispersion: ", dispersion_y, " z dispersion: ", dispersion_z)

        return {"meanFix": mean_fix, "minFix": min_fix, "maxFix": max_fix, "varFix": var_fix, "stdFix": std_fix,
            "meanDis": mean_dispersion, "minDis": min_dispersion, "maxDis": max_dispersion,
            "varDis": var_dispersion, "stdDisp": std_dispersion,
            "freqDisPerSec": fixation_frequency_second}


def get_fixation_df(df_valid):
    '''Calls function to calculate Fixations. Converts the list of fixations to a dataframe and numbers the rows as index.
     Input: Dataframe containg valid gaze points.
     Output: Dataframe containing the fixation features.'''
    fixations = list(detect_fixations(df_valid))
    df = pd.DataFrame(fixations)
    df['index'] = range(1, len(df) + 1)
    # df.head()
    return df

def calculate_directions_of_list(points):
    '''Calculates the dominant direction of points.
    Input: Dataframe containing fixation points.
    Output: Dict with dominant direction for x (xDir) and y (yDir).
    '''
    x_values, y_values, z_values = zip(*points['centroid'])
    # Get a list of whether a given value is greater then the previous one in the list
    res_x = [float(val1) < float(val2) for val1, val2 in zip(x_values, x_values[1:])]
    # Sum all that are True
    sum_x = sum(res_x)
    # Divide the sum by the total number of values to get the desired output.
    # dir_x is -1 if there are no fixation (i.e. prevent division by zero)
    dir_x = -1
    if len(res_x) != 0:
        dir_x = sum_x/len(res_x)

    res_y = [float(val1) < float(val2) for val1, val2 in zip(y_values, y_values[1:])]
    sum_y = sum(res_y)
    dir_y = -1
    if len(res_y) != 0:
        dir_y = sum_y /len(res_y)


    return {"xDir": dir_x, "yDir": dir_y}

def calculate_fixation_density(df_all, df_fix):
    '''Calculates the fixation density per area.
    Input: Dataframe with all valid gazepoints, Dataframe with fixations.
    Output: Dict containing the fixation density.'''
    min_x = df_all['gazeDirection_x'].min()
    min_y = df_all['gazeDirection_y'].min()
    max_x = df_all['gazeDirection_x'].max()
    max_y = df_all['gazeDirection_y'].max()

    length = abs(max_x-min_x)
    height = abs(max_x-min_x)
    area = length*height

    number_of_fixations = len(df_fix)

    fix_dens = -1
    if area != 0:
        fix_dens = number_of_fixations/area
    return {"fixDensPerBB": fix_dens}


def get_features_for_n_seconds(df, timespan, label, participant_id):
    ''' Calculates the features for a raw gaze data in chunks of n seconds.
    Input: Dataframe with raw gaze data, timespan to chunk, label (i.e. activity class).
    Output: List of dictionaries, one dictionary contains a chunk of features.
    '''

    list_of_features = []
    i = 0
    while i < len(df)-1:
        newdf = pd.DataFrame(columns=df.columns)
        start_time = df["eyeDataTimestamp"][i]

        while i < len(df)-1 and df["eyeDataTimestamp"][i] < (start_time+timespan*1000):
            entry = df.iloc[[i]]
            newdf = pd.concat([newdf,entry])
            i+=1
        newdf.reset_index(inplace = True)

        if (len(newdf) > timespan*28):
            newdf_valid = only_valid_data(newdf)
            df_fixations = get_fixation_df(newdf_valid)
            features = calculate_fixation_features(df_fixations, timespan)
            blinks = calculate_blink_features(newdf,timespan)

            directions = calculate_directions_of_list(df_fixations)
            density = calculate_fixation_density(newdf_valid, df_fixations)

            features.update(blinks)
            features.update(directions)
            features.update(density)
            features["label"] = label
            # print(f"label: {label}")
            features["duration"] = timespan
            features["participant_id"] = participant_id
            list_of_features.append(features)

    return list_of_features

import csv
def save_as_csv(list_of_dict, participant, folder):
    '''Saves a list of dicts as one csv file.
    Input: List of feature dicts, participant id.
    Output: CSV file, saved in same directory as this file.'''
    header = list_of_dict[0].keys()
    rows =  [x.values() for x in list_of_dict]

    keys = list_of_dict[0].keys()
    file_name = os.path.join(folder, f'feature_list_P{participant}.csv')
    # if the file already exists, append the rows
    if os.path.exists(file_name):
        with open(file_name, 'a', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writerows(list_of_dict)
    # otherwise create a new file
    else:
        with open(file_name, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(list_of_dict)
    # '''
    file_name_all = os.path.join(folder, f'feature_list_all.csv')
    # if the file already exists, append the rows
    if os.path.exists(file_name_all):
        with open(file_name_all, 'a', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writerows(list_of_dict)
    # otherwise create a new file
    else:
        with open(file_name_all, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(list_of_dict)
    # '''
    return file_name

def collect_data_from_csv_files():
    ''' Collects the filenames of all csv-files in a given folder.
    Input: -
    Output: Dict containing the activites per participants.'''
    root_dir = "./Data/RawGazeData3/"

    files_list = os.listdir(root_dir)
    print(files_list)
    # filenames are like this: 00_reading.csv, 01_reading.csv,...
    # where the "00" etc. indicates the participant number
    df_files = {}
    for index, path in enumerate(files_list):
        if ("csv" in path):
            name = path.split("_")
            participant_id = name[0]
            activity = name[1].split(".")[0]
            if df_files.get(participant_id):
                df_files[participant_id][activity] = f"{root_dir}{path}"
            else:
                df_files.update({participant_id: {activity: f"{root_dir}{path}"}})
    return df_files

def calculate_features_and_save_for_list_of_files():
    '''Calculates the features for multiple gaze data files and saves those as CSV files.
    Input: Dict containg the activity class (key) and the paths to the gaze data files (value)
    Output: Feature-files.'''

    paths = collect_data_from_csv_files()
    for participant_id, participant_item in paths.items():
        feature_list = []
        for activity, path in participant_item.items():
            print(f"calculating features for : {path}")
            df = pd.read_csv(path)
            print(f"activity: {activity}")
            feature_list.append(get_features_for_n_seconds(df, seconds_feature, activity, participant_id))

        flat_ls = [item for sublist in feature_list for item in sublist]
        # change the folder here to not overwrite the data we provided!
        save_as_csv(flat_ls, participant_id, './Data/FeatureFiles2')

    print("done.")

def nth_repl_all(s, sub, repl, nth):
    find = s.find(sub)
    # loop util we find no match
    i = 1
    while find != -1:
        # if i  is equal to nth we found nth matches so replace
        if i == nth:
            s = s[:find]+repl+s[find + len(sub):]
            i = 0
        # find + len(sub) + 1 means we start after the last match
        find = s.find(sub, find + len(sub) + 1)
        i += 1
    return s

def get_data_and_write_to_csv():
    print("###getting data here")
    #get data from endpoint
    data = requests.get('http://169.254.155.26:8080/api/lastGazeData')
    message_data = data.json()["message"]
    cleaned = nth_repl_all(message_data,",","\n",60)
    #append headers
    headers = "eyeDataTimestamp,eyeDataRelativeTimestamp,frameTimestamp,isCalibrationValid,gazeHasValue,gazeOrigin_x,gazeOrigin_y,gazeOrigin_z,gazeDirection_x,gazeDirection_y,gazeDirection_z,gazePointHit,gazePoint_x,gazePoint_y,gazePoint_z,gazePoint_target_name,gazePoint_target_x,gazePoint_target_y,gazePoint_target_z,gazePoint_target_pos_x,gazePoint_target_pos_y,gazePoint_target_pos_z,gazePoint_target_rot_x,gazePoint_target_rot_y,gazePoint_target_rot_z,gazePoint_target_scale_x,gazePoint_target_scale_y,gazePoint_target_scale_z,gazePointLeftScreen_x,gazePointLeftScreen_y,gazePointLeftScreen_z,gazePointRightScreen_x,gazePointRightScreen_y,gazePointRightScreen_z,gazePointMonoScreen_x,gazePointMonoScreen_y,gazePointMonoScreen_z,GazePointWebcam_x,GazePointWebcam_y,GazePointWebcam_z,gazePointAOIHit,gazePointAOI_x,gazePointAOI_y,gazePointAOI_z,gazePointAOI_name,gazePointAOI_target_x,gazePointAOI_target_y,gazePointAOI_target_z,gazePointAOI_target_pos_x,gazePointAOI_target_pos_y,gazePointAOI_target_pos_z,gazePointAOI_target_rot_x,gazePointAOI_target_rot_y,gazePointAOI_target_rot_z,gazePointAOI_target_scale_x,gazePointAOI_target_scale_y,gazePointAOI_target_scale_z,GazePointAOIWebcam_x,GazePointAOIWebcam_y,GazePointAOIWebcam_z,info\n"
    raw_data = headers+cleaned
    print(raw_data)
    csv_file = open('test.csv',"w")
    csv_file.write(raw_data)
    csv_file.close()
    df  = pd.read_csv("test.csv")
    df.to_csv("./Data/RawGazeData3/00_unknown.csv")




def post_result_to_endpoint(result):
    print(result)
    match result:
        case "Search":
            url = "http://169.254.155.26:8080/api/soundSearch"
        case "Inspection":
            url = "http://169.254.155.26:8080/api/soundInspection"
        case "Reading":
            url = "http://169.254.155.26:8080/api/soundReading"
    requests.get(url)

def trigger_solid_update(result, probability):
    print(result)
    answ = requests.post("http://localhost:3000/updateActivity?action=" + result + "&probability=" + str(probability))


def compute_probability(predictions):
    nbr_predictions = len(predictions)
    probs = []
    label = ""
    flattened = predictions.flatten().tolist()
    probs.append(flattened.count('Search') / nbr_predictions)
    probs.append(flattened.count('Inspection') / nbr_predictions)
    probs.append(flattened.count('Reading') / nbr_predictions)
    maximum_index = probs.index(max(probs))
    probability = max(probs)
    if maximum_index == 0:
        label ="Search"
    if maximum_index == 1:
        label = "Inspection"
    if maximum_index == 2:
        label = "Reading"
    return (label,probability)


def classify():
    print("classifying")
    recording_location = './'
    all_features_csv = os.path.join(recording_location, './Data/FeatureFiles2/feature_list_all.csv')
    print(all_features_csv)
    df = pd.read_csv(all_features_csv)
    df = df.fillna(0)
    print(len(df))
    features = df.loc[:, df.columns!='label']
    print(features.columns)
    #scale features
    scaler = MaxAbsScaler()
    scaler.fit(features)
    scaled = scaler.transform(features)
    scaled_features = pd.DataFrame(scaled, columns=features.columns)
    #load classifier
    rf = joblib.load('random_forest.joblib')
    return compute_probability(rf.predict(scaled_features))


if __name__ == '__main__':
    while(True):
        sleep(1)
        if os.path.exists("./Data/FeatureFiles2/feature_list_all.csv"):
            os.remove("./Data/FeatureFiles2/feature_list_all.csv")
        get_data_and_write_to_csv()
        calculate_features_and_save_for_list_of_files()
        l = classify()
        trigger_solid_update(l[0], l[1])


